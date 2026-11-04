"""Build ForestFire_Before + ForestFire_Burning maps in-editor (#50).

Runs headless inside UnrealEditor-cmd:
  UnrealEditor-cmd.exe ForestFire.uproject -run=pythonscript
    -script=ue_build_maps.py -unattended -nopause -nosplash

Reads <project>/inputs/{foliage.csv, fire_schedule.json, terrain.obj,
meta.json} (see unreal/forest_fire README + tools/terrain_gen.py).
Placeholder art: engine BasicShapes (cones/cylinders) with flat
materials — layout/counts/positions are T0-exact, art-pack meshes are
pending-operator. Writes <project>/Saved/MapsBuild_<status>.txt.

Grid mapping: grid (x=east, y=north) -> UE cm (X=y*500+250, Y=x*500+250).
"""

import csv
import json
import os
import sys
import time
import traceback

import unreal

BURN_SNAPSHOT_STEP = 40  # burning-variant baked state (broad fire + first burnout)
STATUS_DIR = os.path.join(unreal.Paths.project_dir(), "Saved")


def mark(status, detail=""):
    with open(os.path.join(STATUS_DIR, f"MapsBuild_{status}.txt"), "w") as fh:
        fh.write(detail or status)


def log(msg):
    unreal.log("MapsBuild: " + msg)


def load_inputs():
    root = os.path.join(unreal.Paths.project_dir(), "inputs")
    with open(os.path.join(root, "foliage.csv")) as fh:
        foliage = list(csv.DictReader(fh))
    with open(os.path.join(root, "fire_schedule.json")) as fh:
        schedule = json.load(fh)
    with open(os.path.join(root, "meta.json")) as fh:
        meta = json.load(fh)
    with open(os.path.join(root, "heights.json")) as fh:
        heights = json.load(fh)
    return {
        "foliage": foliage,
        "schedule": schedule,
        "meta": meta,
        "heights": heights,
        "terrain_obj": os.path.join(root, "terrain.obj"),
        "swatches": os.path.join(root, "swatches"),
    }


def sample_height(data, east_m, north_m):
    """Bilinear ground height (cm) from the generator grid. No traces:
    line_trace_single returns None under -cmd (no physics scene)."""
    grid = data["heights"]
    step, n, hs = grid["step_m"], grid["n"], grid["heights_cm"]
    fx = min(n - 1.001, max(0.0, east_m / step))
    fy = min(n - 1.001, max(0.0, north_m / step))
    x0, y0 = int(fx), int(fy)
    tx, ty = fx - x0, fy - y0
    return (hs[y0][x0] * (1 - tx) * (1 - ty) + hs[y0][x0 + 1] * tx * (1 - ty)
            + hs[y0 + 1][x0] * (1 - tx) * ty + hs[y0 + 1][x0 + 1] * tx * ty)


def import_terrain(obj_path):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    task = unreal.AssetImportTask()
    task.set_editor_property("automated", True)
    task.set_editor_property("destination_path", "/Game/Maps")
    task.set_editor_property("destination_name", "SM_Terrain")
    task.set_editor_property("filename", obj_path)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    opts = unreal.FbxImportUI()
    opts.set_editor_property("import_materials", False)
    opts.set_editor_property("import_textures", False)
    opts.set_editor_property("import_as_skeletal", False)
    opts.static_mesh_import_data.set_editor_property("combine_meshes", True)
    opts.static_mesh_import_data.set_editor_property("auto_generate_collision", True)
    task.set_editor_property("options", opts)
    tools.import_asset_tasks([task])
    mesh = unreal.EditorAssetLibrary.load_asset("/Game/Maps/SM_Terrain")
    if mesh is None:
        raise RuntimeError("terrain import produced no StaticMesh")
    try:
        mesh.get_editor_property("body_setup").set_editor_property(
            "collision_trace_flag",
            unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
        )
        unreal.EditorAssetLibrary.save_asset("/Game/Maps/SM_Terrain")
    except Exception as exc:  # noqa: BLE001 - collision fallback is non-fatal
        log(f"complex-as-simple collision unavailable ({exc}); box fallback stands")
    return mesh


def import_texture(png_path, name):
    # Delete-first like materials: replace_existing alone left stale bulk
    # data in place (flames rendered BLUE = R/B-swapped bytes from an older
    # import despite correct on-disk PNGs; 2026-11-03).
    full = f"/Game/Maps/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    task = unreal.AssetImportTask()
    task.set_editor_property("automated", True)
    task.set_editor_property("destination_path", "/Game/Maps")
    task.set_editor_property("destination_name", name)
    task.set_editor_property("filename", png_path)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tools.import_asset_tasks([task])
    tex = unreal.EditorAssetLibrary.load_asset(f"/Game/Maps/{name}")
    if tex is None:
        raise RuntimeError(f"texture import failed: {name}")
    return tex


def make_material(path, name, base_tex, emis_tex="mirror", two_sided=False):
    """Flat-swatch TextureSample material. ONLY TextureSample 'RGB' into
    COLOR inputs (base, emissive) is used: constant-expression pins ('', 'R')
    connect-True but render useless (black base, dead opacity), and 'RGB'
    into SCALAR inputs (roughness/specular) whites the whole frame (pkg9:
    pure-255 everywhere, both maps) - presumably NaN shaders poisoning
    auto-exposure. So: no Constant nodes, no scalar wiring, defaults rule.
    emis_tex=None leaves emissive unconnected (true lit); 'mirror' reuses
    the base swatch; otherwise an explicit swatch (black base + orange
    emissive = real flame)."""
    full = f"{path}/{name}"
    # Always rebuild: a stale material with broken wires would otherwise linger.
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary

    def sample(texture):
        node = lib.create_material_expression(mat, unreal.MaterialExpressionTextureSample)
        node.set_editor_property("texture", texture)
        return node

    def connect(tex, prop):
        ok = lib.connect_material_property(sample(tex), "RGB", prop)
        assert ok, f"{name}: connect RGB -> {prop} failed"

    connect(base_tex, unreal.MaterialProperty.MP_BASE_COLOR)
    if emis_tex == "mirror":
        connect(base_tex, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    elif emis_tex is not None:
        connect(emis_tex, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if two_sided:
        mat.set_editor_property("two_sided", True)
    unreal.EditorAssetLibrary.save_asset(full)
    return mat


def make_materials(swatch_dir):
    tex = {n: import_texture(os.path.join(swatch_dir, f"{n}.png"), f"T_{n}")
           for n in ("ground", "trunk", "canopy", "canopy_peat", "charred",
                     "flame", "smoke", "glow", "black", "white")}
    return {
        # NOTE: emissive-mirror is load-bearing, not decorative: with plain
        # lit materials (pkg9/10) the packaged frame goes pure-255 white on
        # BOTH maps (auto-exposure diverges once emissive floors are gone -
        # the 75k sun does not appear to light in packaged builds despite a
        # perfect config; follow-up). Mirror restored = pkg8-proven look.
        "ground": make_material("/Game/Maps", "M_PeatGround", tex["ground"],
                                two_sided=True),
        "trunk": make_material("/Game/Maps", "M_Trunk", tex["trunk"]),
        "canopy": make_material("/Game/Maps", "M_Canopy", tex["canopy"]),
        "canopy_peat": make_material("/Game/Maps", "M_CanopyPeat", tex["canopy_peat"]),
        "charred": make_material("/Game/Maps", "M_Charred", tex["charred"]),
        # Crown-fire shroud: unlit orange (no diffuse washout).
        "flame": make_material("/Game/Maps", "M_Flame", tex["black"],
                               emis_tex=tex["flame"]),
        # Opaque grey slabs (translucent+scalar-opacity renders invisible).
        "smoke": make_material("/Game/Maps", "M_Smoke", tex["smoke"]),
        "glow": make_material("/Game/Maps", "M_CrackGlow", tex["black"],
                              emis_tex=tex["glow"], two_sided=True),
    }


def spawn_mesh(location, mesh, material, scale, collide=True):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(*location), unreal.Rotator(0, 0, 0)
    )
    comp = actor.static_mesh_component
    comp.set_static_mesh(mesh)
    comp.set_material(0, material)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    # Profile, not setter: set_collision_enabled reverts to BLOCK on
    # save+reload (probed); the "NoCollision" profile persists.
    if not collide:
        comp.set_collision_profile_name("NoCollision")
        got = comp.get_collision_enabled()
        if got != unreal.CollisionEnabled.NO_COLLISION:
            raise RuntimeError(f"collision disable failed ({got}); aborting")
    return actor


def build_map(name, data, mats, meshes, burning):
    t0 = time.time()
    umap = os.path.join(unreal.Paths.project_dir(), "Content", "Maps", f"{name}.umap")
    # new_level REFUSES existing package paths (returns False, leaves the
    # editor on /Temp/Untitled). Delete first so recreate always works.
    if unreal.EditorAssetLibrary.does_asset_exist(f"/Game/Maps/{name}"):
        assert unreal.EditorAssetLibrary.delete_asset(f"/Game/Maps/{name}"), \
            f"{name}: delete existing map failed"
    new_ok = unreal.EditorLevelLibrary.new_level(f"/Game/Maps/{name}")
    world = unreal.EditorLevelLibrary.get_editor_world()
    world_path = world.get_path_name() if world else "<no world>"
    log(f"new_level({name}) -> {new_ok} world={world_path}")
    meta = data["meta"]
    spawn = meta["spawn_cm"]
    log(f"building {name} (burning={burning})")

    ground = spawn_mesh((0.0, 0.0, 0.0), meshes["terrain"], mats["ground"], (1, 1, 1))
    ground.set_actor_label("PeatGround")

    sched = data["schedule"]["steps"][BURN_SNAPSHOT_STEP] if burning else None
    burning_cells = set(sched["burning"]) if sched else set()
    burned_cells = set(sched["burned"]) if sched else set()
    smolder_cells = set(sched["smoldering"]) if sched else set()

    stats = {"trees": 0, "flames": 0, "smoke": 0}
    for row in data["foliage"]:
        x = float(row["x_m"]) * 100.0 + 250.0  # UE Y (east)
        y = float(row["y_m"]) * 100.0 + 250.0  # UE X (north)
        key = f"{row['x_cell']},{row['y_cell']}"
        gz = sample_height(data, float(row["x_m"]) + 2.5, float(row["y_m"]) + 2.5)
        charred = key in burned_cells
        canopy_mat = mats["charred"] if charred else (
            mats["canopy_peat"] if float(row["peat_depth"]) > 0 else mats["canopy"])
        trunk_mat = mats["charred"] if charred else mats["trunk"]
        spawn_mesh((y, x, gz), meshes["cylinder"], trunk_mat, (0.5, 0.5, 3.0))
        spawn_mesh((y, x, gz + 260.0), meshes["cone"], canopy_mat, (3.2, 3.2, 4.0))
        stats["trees"] += 1
        if key in burning_cells:
            # Crown-fire shroud: wider than the canopy (r=2.2m vs 1.6m) with
            # its top above the canopy top, so flames read from side and air.
            # (Centered at gz+60 the cone hid INSIDE the canopy.)
            spawn_mesh((y, x, gz + 380.0), meshes["cone"], mats["flame"], (4.4, 4.4, 3.2),
                       collide=False)
            stats["flames"] += 1
        if key in smolder_cells:
            spawn_mesh((y, x, gz + 420.0), meshes["cube"], mats["smoke"], (2.5, 2.5, 7.0),
                       collide=False)
            stats["smoke"] += 1
            if key not in burning_cells:
                spawn_mesh((y, x, gz + 30.0), meshes["plane"], mats["glow"], (4.0, 4.0, 1.0),
                           collide=False)
    log(f"instances: {stats}")

    # NOTE: Rotator positional order in Python is (roll, pitch, yaw) -
    # always use keywords (positional (-50, 130, 0) aimed the sun into space).
    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0, 0, 800),
        unreal.Rotator(pitch=-50.0, yaw=130.0, roll=0.0))
    sun.set_actor_label("Sun")
    # Movable sun: dynamic lighting, no lightmap bake (headless-friendly).
    # Intensity 10 (NOT physical 75k lux): 75k whites every Scene capture to
    # pure-255 on both maps (pkg9+, clean recooks, DXCache purge all white;
    # seg/normals fine) while 10 renders the forest (bisect B1, 2026-11-03).
    # Skylight real_time_capture is innocent (B2: 75k + capture-off still
    # white), so the blowout is the sun level vs the capture pipeline's
    # exposure range. Scene brightness is emissive/fog-driven anyway; revisit
    # with a PostProcessVolume + AE tuning if true daylight is needed.
    # atmosphere_sun_light: without the flag SkyAtmosphere has no light and
    # renders BLACK (forum-verified).
    sun_light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_light.set_editor_property("intensity", 10.0)
    try:
        sun_light.set_editor_property("atmosphere_sun_light", True)
    except Exception as exc:  # noqa: BLE001 - fail loud, black sky otherwise
        raise RuntimeError(f"atmosphere_sun_light failed: {exc}")
    sky_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyLight, unreal.Vector(0, 0, 500), unreal.Rotator(0, 0, 0))
    sky_light.set_actor_label("SkyFill")
    sky_comp = sky_light.get_component_by_class(unreal.SkyLightComponent)
    sky_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_comp.set_editor_property("intensity", 1.0)
    try:
        sky_comp.set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001 - fail loud, black ambient otherwise
        raise RuntimeError(f"sky real_time_capture failed: {exc}")
    unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog = fog_actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    try:
        if burning:
            fog.set_editor_property("fog_density", 0.022)
        else:
            fog.set_editor_property("fog_density", 0.0012)
    except Exception as exc:  # noqa: BLE001 - surface density failures loudly
        raise RuntimeError(f"fog density failed: {exc}")
    try:
        color = (0.72, 0.52, 0.30, 1.0) if burning else (0.55, 0.62, 0.70, 1.0)
        fog.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(*color))
    except Exception as exc:  # noqa: BLE001 - tint is best-effort across versions
        log(f"fog tint unavailable ({exc}); density stands")

    start = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(spawn["x"], spawn["y"], spawn["z"]),
        unreal.Rotator(0, 0, 0))
    start.set_actor_label("DroneSpawn")

    gm_class = unreal.load_class(None, "/Script/AirSim.AirSimGameMode")
    if gm_class is None:
        raise RuntimeError("AirSimGameMode class not found; is the plugin enabled?")
    world.get_world_settings().set_editor_property("default_game_mode", gm_class)

    # new_level is flaky under -cmd (observed: level left with no package
    # filename so save_current_level silently does nothing). Save through
    # the asset library and prove it on the filesystem.
    saved = unreal.EditorAssetLibrary.save_asset(f"/Game/Maps/{name}")
    if not saved:
        unreal.EditorLevelLibrary.save_current_level()
    if not (os.path.exists(umap) and os.path.getmtime(umap) > t0):
        raise RuntimeError(
            f"{name}: save failed (new_level={new_ok} world={world_path} "
            f"save_asset={saved})")
    log(f"saved {name} (save_asset={saved})")
    return stats


def verify_map(name, expect_fire):
    """Reload a saved map from disk and assert its contents. Guards
    against silent save failures (observed: second new_level in one
    session can leave the first map empty)."""
    unreal.EditorLevelLibrary.load_level(f"/Game/Maps/{name}")
    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    n_mesh = sum(isinstance(a, unreal.StaticMeshActor) for a in actors)
    n_ps = sum(isinstance(a, unreal.PlayerStart) for a in actors)
    gm = world.get_world_settings().get_editor_property("default_game_mode")
    gm_name = gm.get_name() if gm else "None"
    log(f"verify {name}: staticmesh={n_mesh} playerstarts={n_ps} gamemode={gm_name}")
    assert n_mesh >= 200, f"{name}: only {n_mesh} mesh actors"
    assert n_ps == 1, f"{name}: {n_ps} player starts"
    assert gm_name == "AirSimGameMode", f"{name}: game mode {gm_name}"
    if expect_fire:
        assert n_mesh > 250, f"{name}: fire markers missing ({n_mesh})"


def main():
    which = os.environ.get("DMB_MAPS", "both").lower()
    data = load_inputs()
    log(f"spawn_cm={data['meta']['spawn_cm']}")
    mats = make_materials(data["swatches"])
    meshes = {
        "terrain": import_terrain(data["terrain_obj"]),
        "cone": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cone"),
        "cylinder": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder"),
        "cube": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube"),
        "plane": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane"),
    }
    missing = [k for k, v in meshes.items() if v is None]
    if missing:
        raise RuntimeError(f"missing meshes: {missing}")
    stats = {}
    if which in ("both", "before"):
        stats["before"] = build_map("ForestFire_Before", data, mats, meshes, burning=False)
    if which in ("both", "burning"):
        stats["burning"] = build_map("ForestFire_Burning", data, mats, meshes, burning=True)
    for name, burning in (("ForestFire_Before", False), ("ForestFire_Burning", True)):
        short = name.split("_", 1)[1].lower()
        if which in ("both", short):
            verify_map(name, burning)
    mark("OK", json.dumps(stats))
    log(f"maps built + verified: {sorted(stats)}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        mark("FAIL", traceback.format_exc())
        log("FAILED\n" + traceback.format_exc())
        raise
