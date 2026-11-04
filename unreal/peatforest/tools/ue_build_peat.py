"""Build PeatBefore + PeatBurning maps in-editor (#65).

Runs headless inside UnrealEditor-cmd:
  UnrealEditor-cmd.exe ForestFire.uproject -run=pythonscript
    -script=ue_build_peat.py -unattended -nopause -nosplash

Reads <project>/inputs/peatforest/{terrain.obj, albedo_2k.png,
grove_*.obj, heights.json, meta.json, fronts.json, canals.json,
ops.json} (see unreal/peatforest/tools). Reuses the proven rig from
ue_build_maps.py: sun=10 (75k whites out), emissive-mirror swatch
materials, BGR swatch order, delete-first everything, reload-verify.

Grid mapping: local meters (x=east, y=north) -> UE cm (X=y*100, Y=x*100).
"""

import json
import os
import time
import traceback

import unreal

STATUS_DIR = os.path.join(unreal.Paths.project_dir(), "Saved")


def mark(status, detail=""):
    with open(os.path.join(STATUS_DIR, f"PeatBuild_{status}.txt"), "w") as fh:
        fh.write(detail or status)


def log(msg):
    unreal.log("PeatBuild: " + msg)


def load_inputs():
    root = os.path.join(unreal.Paths.project_dir(), "inputs", "peatforest")
    out = {}
    for name in ("heights", "meta", "fronts", "canals", "ops"):
        fname = {"heights": "heights.json", "meta": "meta.json",
                 "fronts": "fronts.json", "canals": "canals.json",
                 "ops": "ops.json"}[name]
        with open(os.path.join(root, fname)) as fh:
            out[name] = json.load(fh)
    out["dir"] = root
    out["swatches"] = os.path.join(unreal.Paths.project_dir(), "inputs", "swatches")
    # BGR-swapped derived PBR (gen_textures --pbr-src); assets_raw stays
    # pristine/hash-pinned and is never imported directly.
    out["pbr"] = os.path.join(root, "pbr")
    return out


def sample_height(heights, east_m, north_m):
    step, n, hs = heights["step_m"], heights["n"], heights["heights_cm"]
    fx = min(n - 1.001, max(0.0, east_m / step))
    fy = min(n - 1.001, max(0.0, north_m / step))
    x0, y0 = int(fx), int(fy)
    tx, ty = fx - x0, fy - y0
    return (hs[y0][x0] * (1 - tx) * (1 - ty) + hs[y0][x0 + 1] * tx * (1 - ty)
            + hs[y0 + 1][x0] * (1 - tx) * ty + hs[y0 + 1][x0 + 1] * tx * ty)


def import_mesh(obj_path, dest_dir, name, complex_collision=False):
    full = f"{dest_dir}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    task = unreal.AssetImportTask()
    task.set_editor_property("automated", True)
    task.set_editor_property("destination_path", dest_dir)
    task.set_editor_property("destination_name", name)
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
    mesh = unreal.EditorAssetLibrary.load_asset(full)
    if mesh is None:
        raise RuntimeError(f"mesh import failed: {name}")
    try:
        st = mesh.get_editor_property("nanite_settings")
        st.set_editor_property("enabled", True)
        mesh.set_editor_property("nanite_settings", st)
        unreal.EditorAssetLibrary.save_asset(full)
    except Exception as exc:  # noqa: BLE001 - nanite is garnish
        log(f"nanite unavailable on {name} ({exc}); standard mesh stands")
    if complex_collision:
        try:
            mesh.get_editor_property("body_setup").set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            unreal.EditorAssetLibrary.save_asset(full)
        except Exception as exc:
            log(f"complex collision unavailable ({exc}); box fallback stands")
    return mesh


def import_texture(img_path, name, srgb=True, wrap=False, normal=False):
    full = f"/Game/Peat/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    task = unreal.AssetImportTask()
    task.set_editor_property("automated", True)
    task.set_editor_property("destination_path", "/Game/Peat")
    task.set_editor_property("destination_name", name)
    task.set_editor_property("filename", img_path)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tools.import_asset_tasks([task])
    tex = unreal.EditorAssetLibrary.load_asset(full)
    if tex is None:
        raise RuntimeError(f"texture import failed: {name}")
    if normal:
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings",
                                unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif not srgb:
        tex.set_editor_property("srgb", False)
    if wrap:
        tex.set_editor_property("address_x", unreal.TextureAddress.TA_WRAP)
        tex.set_editor_property("address_y", unreal.TextureAddress.TA_WRAP)
        got = (tex.get_editor_property("address_x"),
               tex.get_editor_property("address_y"))
        if got != (unreal.TextureAddress.TA_WRAP, unreal.TextureAddress.TA_WRAP):
            raise RuntimeError(f"{name}: wrap addressing failed ({got})")
    unreal.EditorAssetLibrary.save_asset(full)
    return tex


def _new_mat(name):
    full = f"/Game/Peat/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset(name, "/Game/Peat", unreal.Material,
                             unreal.MaterialFactoryNew())
    # Nanite meshes render DEFAULT GRAY without this usage flag (probed:
    # "missing bUsedWithNanite" in the packaged log). Harmless on the
    # non-Nanite BasicShapes materials (flame/smoke/glow/burn/water).
    mat.set_editor_property("used_with_nanite", True)
    return mat


def _finish_mat(name):
    unreal.EditorAssetLibrary.save_asset(f"/Game/Peat/{name}")


def make_materials(data):
    lib = unreal.MaterialEditingLibrary
    MP = unreal.MaterialProperty

    def sample(mat, texture):
        node = lib.create_material_expression(
            mat, unreal.MaterialExpressionTextureSample)
        node.set_editor_property("texture", texture)
        return node

    def const(mat, v):
        node = lib.create_material_expression(
            mat, unreal.MaterialExpressionConstant)
        node.set_editor_property("r", float(v))
        return node

    def mul(mat):
        return lib.create_material_expression(
            mat, unreal.MaterialExpressionMultiply)

    def out(mat, node, pin, prop, tag):
        ok = lib.connect_material_property(node, pin, prop)
        assert ok, f"{tag}: connect {pin} -> {prop} failed"

    def wire_uv(mat, texture, scale=None, scroll=None):
        """Sample with optional UV tiling (texcoord x const) / scroll."""
        node = sample(mat, texture)
        uv_src, uv_pin = None, None
        if scale is not None:
            tc = lib.create_material_expression(
                mat, unreal.MaterialExpressionTextureCoordinate)
            tc.set_editor_property("coordinate_index", 0)
            m = mul(mat)
            assert lib.connect_material_expressions(tc, "", m, "A")
            assert lib.connect_material_expressions(const(mat, scale), "", m, "B")
            uv_src, uv_pin = m, ""
        if scroll is not None:
            pan = lib.create_material_expression(
                mat, unreal.MaterialExpressionPanner)
            pan.set_editor_property("speed_x", float(scroll[0]))
            pan.set_editor_property("speed_y", float(scroll[1]))
            uv_src, uv_pin = pan, ""
        if uv_src is not None:
            assert lib.connect_material_expressions(uv_src, uv_pin, node, "UVs")
        return node

    def lift(mat, node, amount):
        """node.RGB x const -> multiply node (emissive lifts)."""
        m = mul(mat)
        assert lib.connect_material_expressions(node, "RGB", m, "A")
        assert lib.connect_material_expressions(const(mat, amount), "", m, "B")
        return m

    sw = data["swatches"]
    meadow = {n: import_texture(os.path.join(sw, f"{n}.png"), f"T_Peat_{n}")
              for n in ("black", "water")}
    tx = os.path.join(data["dir"], "tex")
    proctex = {n: import_texture(os.path.join(tx, f"{n}.png"), f"T_Peat_{n}")
               for n in ("leaf_card", "frond", "flame", "smoke", "glow",
                         "burn_patch", "clouds")}
    raw = data["pbr"]
    bark = import_texture(os.path.join(raw, "bark_diff.jpg"), "T_Peat_Bark",
                          wrap=True)
    bark_n = import_texture(os.path.join(raw, "bark_nor.png"), "T_Peat_BarkN",
                            normal=True, wrap=True)
    mud = import_texture(os.path.join(raw, "mud_diff.jpg"), "T_Peat_Mud",
                         wrap=True)
    mud_n = import_texture(os.path.join(raw, "mud_nor.png"), "T_Peat_MudN",
                           normal=True, wrap=True)
    burn = import_texture(os.path.join(raw, "burn_diff.jpg"), "T_Peat_Burn")
    albedo = import_texture(os.path.join(data["dir"], "albedo_2k.png"),
                            "T_Peat_Albedo")
    mats = {}

    # Ground: S2 albedo x tiled peat-mud detail + detail normal, lit.
    mat = _new_mat("M_Peat_Ground")
    m = mul(mat)
    assert lib.connect_material_expressions(sample(mat, albedo), "RGB", m, "A")
    assert lib.connect_material_expressions(
        wire_uv(mat, mud, scale=400.0), "RGB", m, "B"), "ground detail"
    out(mat, m, "", MP.MP_BASE_COLOR, "ground")
    out(mat, wire_uv(mat, mud_n, scale=400.0), "RGB", MP.MP_NORMAL,
        "ground-n")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Ground")
    mats["ground"] = mat

    # Trunk: bark PBR + normal, lit.
    mat = _new_mat("M_Peat_Trunk")
    out(mat, sample(mat, bark), "RGB", MP.MP_BASE_COLOR, "trunk")
    out(mat, sample(mat, bark_n), "RGB", MP.MP_NORMAL, "trunk-n")
    _finish_mat("M_Peat_Trunk")
    mats["trunk"] = mat

    # Charred: bark x 0.22 (keeps furrows, near-black) + normal.
    mat = _new_mat("M_Peat_Charred")
    m = mul(mat)
    assert lib.connect_material_expressions(sample(mat, bark), "RGB", m, "A")
    assert lib.connect_material_expressions(const(mat, 0.22), "", m, "B")
    out(mat, m, "", MP.MP_BASE_COLOR, "charred")
    out(mat, sample(mat, bark_n), "RGB", MP.MP_NORMAL, "charred-n")
    _finish_mat("M_Peat_Charred")
    mats["charred"] = mat

    # Canopy: dense cluster fill, masked + slight emissive lift.
    # Clip 0.2 keeps the punched depth holes while holding the crown.
    mat = _new_mat("M_Peat_Canopy")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.2)
    node = sample(mat, proctex["leaf_card"])
    out(mat, node, "RGB", MP.MP_BASE_COLOR, "canopy")
    out(mat, node, "A", MP.MP_OPACITY_MASK, "canopy-mask")
    out(mat, lift(mat, node, 0.18), "", MP.MP_EMISSIVE_COLOR, "canopy-lift")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Canopy")
    mats["canopy"] = mat

    # Fronds: feather alpha, masked, double-sided.
    mat = _new_mat("M_Peat_Frond")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.3)
    node = sample(mat, proctex["frond"])
    out(mat, node, "RGB", MP.MP_BASE_COLOR, "frond")
    out(mat, node, "A", MP.MP_OPACITY_MASK, "frond-mask")
    out(mat, lift(mat, node, 0.15), "", MP.MP_EMISSIVE_COLOR, "frond-lift")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Frond")
    mats["frond"] = mat

    # Flame: scrolling tongues, masked + hot emissive.
    mat = _new_mat("M_Peat_Flame")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.5)
    node = wire_uv(mat, proctex["flame"], scroll=(0.0, -1.2))
    out(mat, sample(mat, meadow["black"]), "RGB", MP.MP_BASE_COLOR,
        "flame-base")
    out(mat, node, "A", MP.MP_OPACITY_MASK, "flame-mask")
    out(mat, lift(mat, node, 3.0), "", MP.MP_EMISSIVE_COLOR, "flame-hot")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Flame")
    mats["flame"] = mat

    # Smoke: soft sprites, translucent, slow rise.
    mat = _new_mat("M_Peat_Smoke")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    node = wire_uv(mat, proctex["smoke"], scroll=(0.0, -0.15))
    out(mat, node, "RGB", MP.MP_BASE_COLOR, "smoke")
    out(mat, node, "A", MP.MP_OPACITY, "smoke-alpha")
    out(mat, lift(mat, node, 0.5), "", MP.MP_EMISSIVE_COLOR, "smoke-lift")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Smoke")
    mats["smoke"] = mat

    # Glow: hot ground disc.
    mat = _new_mat("M_Peat_Glow")
    node = sample(mat, proctex["glow"])
    out(mat, sample(mat, meadow["black"]), "RGB", MP.MP_BASE_COLOR,
        "glow-base")
    out(mat, lift(mat, node, 4.0), "", MP.MP_EMISSIVE_COLOR, "glow-hot")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Glow")
    mats["glow"] = mat

    # Burn scar: charred ground, radial alpha.
    mat = _new_mat("M_Peat_Burn")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    bnode = sample(mat, burn)
    anode = sample(mat, proctex["burn_patch"])
    out(mat, bnode, "RGB", MP.MP_BASE_COLOR, "burn")
    out(mat, anode, "A", MP.MP_OPACITY, "burn-alpha")
    _finish_mat("M_Peat_Burn")
    mats["burn"] = mat

    # Path: dirt track (mud squared = darker; two-sided because
    # ribbon winding follows path direction).
    mat = _new_mat("M_Peat_Path")
    m = mul(mat)
    pnode = sample(mat, mud)
    assert lib.connect_material_expressions(pnode, "RGB", m, "A")
    assert lib.connect_material_expressions(pnode, "RGB", m, "B")
    out(mat, m, "", MP.MP_BASE_COLOR, "path")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Path")
    mats["path"] = mat

    # Clouds: unlit drifting bank on the sky dome.
    mat = _new_mat("M_Peat_Clouds")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    cnode = wire_uv(mat, proctex["clouds"], scroll=(0.004, 0.001))
    out(mat, sample(mat, meadow["black"]), "RGB", MP.MP_BASE_COLOR,
        "cloud-base")
    out(mat, cnode, "A", MP.MP_OPACITY, "cloud-alpha")
    out(mat, lift(mat, cnode, 1.2), "", MP.MP_EMISSIVE_COLOR, "cloud-lit")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Clouds")
    mats["clouds"] = mat

    # Water: unchanged flat stand-in.
    mat = _new_mat("M_Peat_Water")
    out(mat, sample(mat, meadow["water"]), "RGB", MP.MP_BASE_COLOR, "water")
    out(mat, sample(mat, meadow["water"]), "RGB", MP.MP_EMISSIVE_COLOR,
        "water-e")
    mat.set_editor_property("two_sided", True)
    _finish_mat("M_Peat_Water")
    mats["water"] = mat
    return mats


def spawn_mesh(location, mesh, material, scale, collide=True, yaw=0.0):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(*location),
        unreal.Rotator(pitch=0.0, yaw=yaw, roll=0.0))
    comp = actor.static_mesh_component
    comp.set_static_mesh(mesh)
    comp.set_material(0, material)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    if not collide:
        # Auto-decomposed hulls on km-scale merged meshes are solid rock
        # filling the world (drones spawn inside, moves die). Use the
        # collision PROFILE: set_collision_enabled reverts to BLOCK on
        # save+reload (probed), the "NoCollision" profile persists.
        comp.set_collision_profile_name("NoCollision")
        got = comp.get_collision_enabled()
        if got != unreal.CollisionEnabled.NO_COLLISION:
            raise RuntimeError(f"collision disable failed ({got}); aborting")
    return actor


def build_map(name, data, mats, meshes, burning):
    t0 = time.time()
    umap = os.path.join(unreal.Paths.project_dir(), "Content", "Peat", f"{name}.umap")
    if unreal.EditorAssetLibrary.does_asset_exist(f"/Game/Peat/{name}"):
        assert unreal.EditorAssetLibrary.delete_asset(f"/Game/Peat/{name}"), \
            f"{name}: delete existing map failed"
    new_ok = unreal.EditorLevelLibrary.new_level(f"/Game/Peat/{name}")
    world = unreal.EditorLevelLibrary.get_editor_world()
    log(f"new_level({name}) -> {new_ok}")
    log(f"building {name} (burning={burning})")

    stats = {"meshes": 0, "flames": 0, "smoke": 0}
    ground = spawn_mesh((0.0, 0.0, 0.0), meshes["terrain"], mats["ground"],
                        (1, 1, 1), collide=False)
    ground.set_actor_label("PeatTerrain")
    stats["meshes"] += 1
    # Hidden collision shell: the 500x500 visual mesh silently cooks with
    # no collision; this 100x100 shell carries complex collision instead.
    shell = spawn_mesh((0.0, 0.0, 0.0), meshes["collision"], mats["ground"],
                       (1, 1, 1), collide=True)
    shell.set_actor_label("PeatCollision")
    shell.set_actor_hidden_in_game(True)
    stats["meshes"] += 1
    # Groves: NO merged-mesh collision (auto hulls on 2 km meshes are
    # solid rock; tree collision returns with the foliage/Quixel pass).
    for key, label in (("trunk", "GroveTrunk"),
                         ("frond", "GroveFrond"),
                         ("canopy", "GroveCanopy")):
        a = spawn_mesh((0.0, 0.0, 0.0), meshes[key],
                       mats[key], (1, 1, 1), collide=False)
        a.set_actor_label(label)
        stats["meshes"] += 1
    if burning:
        a = spawn_mesh((0.0, 0.0, 0.0), meshes["charred"],
                       mats["charred"], (1, 1, 1), collide=False)
        a.set_actor_label("GroveCharred")
        stats["meshes"] += 1
        for f in data["fronts"]:
            ex = (f["lon"] - 114.318) * 111320.0 * 0.9988
            ny = (f["lat"] - -2.86) * 110540.0
            gz = sample_height(data["heights"], ex, ny)
            ux, uy = ny * 100.0, ex * 100.0
            # Big fire: nested tongue cones + tall smoke columns.
            for fz, fs in ((380.0, (5.5, 5.5, 4.2)),
                           (460.0, (3.6, 3.6, 5.2)),
                           (520.0, (2.2, 2.2, 6.0))):
                spawn_mesh((ux, uy, gz + fz), meshes["cone"], mats["flame"],
                           fs, collide=False)
                stats["flames"] += 1
            for sz, ss in ((420.0, (3.0, 3.0, 9.0)),
                           (700.0, (4.5, 4.5, 12.0))):
                spawn_mesh((ux, uy, gz + sz), meshes["cube"], mats["smoke"],
                           ss, collide=False)
                stats["smoke"] += 1
            spawn_mesh((ux, uy, gz + 18.0), meshes["plane"], mats["burn"],
                       (9.0, 9.0, 1.0), collide=False)
            spawn_mesh((ux, uy, gz + 30.0), meshes["plane"], mats["glow"],
                       (5.0, 5.0, 1.0), collide=False)
            # Fire light: orange point glow, no shadows (10 shadow-casting
            # point lights would tank the frame budget).
            lamp = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PointLight, unreal.Vector(ux, uy, gz + 600.0),
                unreal.Rotator(0, 0, 0))
            lamp.set_actor_label("FireLight")
            plc = lamp.get_component_by_class(unreal.PointLightComponent)
            plc.set_mobility(unreal.ComponentMobility.MOVABLE)
            plc.set_editor_property("intensity", 6000.0)
            plc.set_editor_property("attenuation_radius", 3500.0)
            plc.set_editor_property("light_color",
                                    unreal.Color(255, 120, 30, 255))
            plc.set_editor_property("cast_shadows", False)
            stats["lights"] = stats.get("lights", 0) + 1
    # Canals (both variants): flat water strips along wet rows.
    for c in data["canals"]:
        (x0, y0), (x1, y1) = c["from_m"], c["to_m"]
        length_m = abs(x1 - x0) + abs(y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        gz = min(sample_height(data["heights"], x0, y0),
                 sample_height(data["heights"], x1, cy),
                 sample_height(data["heights"], cx, y1)) + 20.0
        # BasicShapes Plane is 400x400 cm; scale to strip.
        yaw = 0.0 if abs(x1 - x0) >= abs(y1 - y0) else 90.0
        along = length_m * 100.0 / 400.0
        across = c["width_m"] * 100.0 / 400.0
        sx, sy = (across, along) if yaw == 0.0 else (along, across)
        spawn_mesh((cy * 100.0, cx * 100.0, gz), meshes["plane"],
                   mats["water"], (sx, sy, 1.0), collide=False, yaw=yaw)
        stats["meshes"] += 1
    # Hidden-path ribbons (both variants; the eval scores discovery).
    pa = spawn_mesh((0.0, 0.0, 0.0), meshes["paths"], mats["path"],
                    (1, 1, 1), collide=False)
    pa.set_actor_label("PeatPaths")
    stats["meshes"] += 1
    stats["paths"] = 3
    # Cloud domes: two squashed spheres over the tile center, slow drift.
    for label, pos, scl in (("CloudFar", (100000.0, 100000.0, -400.0),
                             (9000.0, 9000.0, 2600.0)),
                            ("CloudNear", (100000.0, 100000.0, -300.0),
                             (5500.0, 5500.0, 1800.0))):
        ca = spawn_mesh(pos, meshes["sphere"], mats["clouds"], scl,
                        collide=False)
        ca.set_actor_label(label)
        stats["meshes"] += 1
    log(f"instances: {stats}")

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0, 0, 800),
        unreal.Rotator(pitch=-50.0, yaw=130.0, roll=0.0))
    sun.set_actor_label("Sun")
    sun_light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_light.set_editor_property("intensity", 10.0)
    try:
        sun_light.set_editor_property("atmosphere_sun_light", True)
    except Exception as exc:
        raise RuntimeError(f"atmosphere_sun_light failed: {exc}")
    try:
        sun_light.set_editor_property("use_temperature", True)
        sun_light.set_editor_property("temperature", 8000.0)
    except Exception as exc:
        log(f"sun temperature unavailable ({exc}); white sun stands")
    sky_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyLight, unreal.Vector(0, 0, 500), unreal.Rotator(0, 0, 0))
    sky_light.set_actor_label("SkyFill")
    sky_comp = sky_light.get_component_by_class(unreal.SkyLightComponent)
    sky_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_comp.set_editor_property("intensity", 1.0)
    try:
        sky_comp.set_editor_property("real_time_capture", True)
    except Exception as exc:
        raise RuntimeError(f"sky real_time_capture failed: {exc}")
    unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog = fog_actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    try:
        fog.set_editor_property("fog_density", 0.022 if burning else 0.0012)
    except Exception as exc:
        raise RuntimeError(f"fog density failed: {exc}")
    try:
        color = (0.72, 0.52, 0.30, 1.0) if burning else (0.55, 0.62, 0.70, 1.0)
        fog.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(*color))
    except Exception as exc:
        log(f"fog tint unavailable ({exc}); density stands")

    spawn_z = sample_height(data["heights"], 0.0, 0.0) + 8.0
    # Sidecar unit guard: spawn sits ON the terrain, so it must fall inside
    # the DEM range in cm. A meters/cm slip (spawn 15 cm vs terrain 700 cm
    # buried the drone 6.8 m underground) fails the build here, loudly.
    lo = data["meta"]["dem_min_m"] * 100.0 - 50.0
    hi = data["meta"]["dem_max_m"] * 100.0 + 50.0
    if not (lo <= spawn_z <= hi):
        raise RuntimeError(f"spawn_z {spawn_z} outside DEM cm range [{lo}, {hi}]")
    start = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(0.0, 0.0, spawn_z), unreal.Rotator(0, 0, 0))
    start.set_actor_label("DroneSpawn")

    gm_class = unreal.load_class(None, "/Script/AirSim.AirSimGameMode")
    if gm_class is None:
        raise RuntimeError("AirSimGameMode class not found; is the plugin enabled?")
    world.get_world_settings().set_editor_property("default_game_mode", gm_class)

    saved = unreal.EditorAssetLibrary.save_asset(f"/Game/Peat/{name}")
    if not saved:
        unreal.EditorLevelLibrary.save_current_level()
    if not (os.path.exists(umap) and os.path.getmtime(umap) > t0):
        raise RuntimeError(f"{name}: save failed")
    log(f"saved {name} (save_asset={saved})")
    return stats


def verify_map(name, expect_fire):
    unreal.EditorLevelLibrary.load_level(f"/Game/Peat/{name}")
    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    n_mesh = sum(isinstance(a, unreal.StaticMeshActor) for a in actors)
    n_ps = sum(isinstance(a, unreal.PlayerStart) for a in actors)
    gm = world.get_world_settings().get_editor_property("default_game_mode")
    gm_name = gm.get_name() if gm else "None"
    log(f"verify {name}: staticmesh={n_mesh} playerstarts={n_ps} gamemode={gm_name}")
    terr = [a for a in actors if (a.get_actor_label() or "") == "PeatTerrain"][0]
    ext = terr.get_actor_bounds(False)[1]
    log(f"verify {name}: terrain extent=({ext.x:.0f},{ext.y:.0f},{ext.z:.0f})")
    assert ext.z < ext.x / 10.0, f"{name}: terrain not flat {ext}"
    assert n_mesh >= 6, f"{name}: only {n_mesh} mesh actors"
    assert n_ps == 1, f"{name}: {n_ps} player starts"
    assert gm_name == "AirSimGameMode", f"{name}: game mode {gm_name}"
    if expect_fire:
        assert n_mesh > 30, f"{name}: fire markers missing ({n_mesh})"


def main():
    which = os.environ.get("DMB_MAPS", "both").lower()
    data = load_inputs()
    mats = make_materials(data)
    meshes = {
        "terrain": import_mesh(os.path.join(data["dir"], "terrain.obj"),
                               "/Game/Peat", "SM_PeatTerrain"),
        "collision": import_mesh(os.path.join(data["dir"], "terrain_collision.obj"),
                                 "/Game/Peat", "SM_PeatCollision",
                                 complex_collision=True),
        "trunk": import_mesh(os.path.join(data["dir"], "trunk.obj"),
                               "/Game/Peat", "SM_GroveTrunk"),
        "frond": import_mesh(os.path.join(data["dir"], "frond.obj"),
                             "/Game/Peat", "SM_GroveFrond"),
        "canopy": import_mesh(os.path.join(data["dir"], "canopy.obj"),
                              "/Game/Peat", "SM_GroveCanopy"),
        "charred": import_mesh(os.path.join(data["dir"], "charred.obj"),
                               "/Game/Peat", "SM_GroveCharred"),
        "paths": import_mesh(os.path.join(data["dir"], "paths.obj"),
                               "/Game/Peat", "SM_PeatPaths"),
        "cone": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cone"),
        "cube": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube"),
        "plane": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane"),
        "sphere": unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Sphere"),
    }
    missing = [k for k, v in meshes.items() if v is None]
    if missing:
        raise RuntimeError(f"missing meshes: {missing}")
    stats = {}
    if which in ("both", "before"):
        stats["before"] = build_map("PeatBefore", data, mats, meshes, burning=False)
    if which in ("both", "burning"):
        stats["burning"] = build_map("PeatBurning", data, mats, meshes, burning=True)
    for name, burning in (("PeatBefore", False), ("PeatBurning", True)):
        short = name[4:].lower()
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
