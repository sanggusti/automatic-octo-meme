# Render notes (2026-11-04 debug log)

How the forest worlds were made to render under Gazebo Harmonic +
ogre2 (software GL). Every entry below cost at least one container
render; read before touching the builder or the manifest.

## What works (verified in frames)

* **Oak tree** (OpenRobotics, CC0): textured broadleaf, correct scale.
  Peat overstory backbone. DAE bounds ±250 look scary but both nodes
  carry a 0.0254 scale matrix (inches->m); renders ~6 m.
* **Pine Tree** (OpenRobotics, CC0): textured conifer. Generic
  `forest_fire` mix only -- botanically wrong for peat swamp.
* **Smoke / flame / haze**: `caguero/smoke_generator` numerics +
  texture and `Fog Emitter Dense` numerics, rehosted as SDF
  `<particle_emitter>` link blocks with model:// albedo URIs.
* **Ground**: thin BOX with dark peat diffuse. (Not `<plane>` -- see
  below.) 600x600 m single box renders correctly.
* **Scene fog**: linear fog start 80 / end 520 lightens the treeline;
  sky renders through `<sky/>`.

## Retired assets (do not re-add without re-vetting)

* **facugu123/Tree (apple)**: renders as a 2.6 m leafless white
  skeleton even with textures resolving (zero-error log). Blender
  export quirks beyond texture names (duplicate `*.001.jpg` refs were
  only the first layer).
* **Grass Plane**: a single instance sprawls ~500 m of plane visuals;
  renders black under ogre2. Not a tuft.
* **grasspatch**: 15 m planes; renders black under ogre2.
* **Oak tint variants**: ogre2 ignores legacy pass `diffuse` -- sun /
  shade / control rendered pixel-identical. Removed.
* **baylands_vegetation_***: 101 MB single-mesh whole-landscape
  diorama, not an instancable bush.

## Renderer rules learned the hard way

1. **Plane geometry renders black** under ogre2 here (ground plane,
   grass planes). Boxes with identical materials render fine. No
   `<plane>` anywhere in generated worlds.
2. **Harmonic ignores model `<plugin>` particle blocks.** The
   ParticleEmitter system only processes `<particle_emitter>` SDF
   elements (verified in gz-sim8 `ParticleEmitter.cc`: the plugin's
   own SDF is an unused parameter). All plugin-style emitters were
   silently dead; six param variants confirmed none emit.
3. **Ogre emitters shoot +X natively** (hardcoded `UNIT_X` in
   `Ogre2ParticleEmitter.cc`, gz-rendering8). The up-pitch MUST sit on
   the `<particle_emitter>` element: model-level pitch is ignored and
   lays jets flat along +X (proved by single-emitter isolation: the
   same jet reads as a column end-on and a streak side-on). Never
   pitch both (double pitch also lays flat).
4. **Ogre mesh/material lookup bypasses sdformat path order.** Shading
   a pinned dir with a staged copy of the same name is unreliable for
   meshes; staged copies use unique dir + config names
   (`canopy-broadleaf-hd`, `oak-tree-sun`) -- or, where shadowing was
   unavoidable, the pinned extracted copy got the same repair.
5. **Color ramps don't resolve.** `<color_range_image>` fails for
   relative AND model:// paths (ogre-side lookup). Ramps omitted;
   albedo texture + diffuse carry the look.
6. **`<scale>` under `<include>` is invalid SDF.** gz warns and
   ignores it (750 warnings/run). Per-instance size needs staged
   model copies -- not implemented; yaw/position/species variation
   only.
7. **Fuel self-references use config names.** Model SDFs reference
   `model://<config-name>/...`, so the resource root needs alias
   symlinks (`grass_plane -> grass-plane`, `Oak tree -> oak-tree`,
   ...). `fetch_models.create_aliases()` owns this.
8. **`<collision>`/`<visual>` need `name=`** (gz rejects unnamed),
   and camera pitch-down is **+90 deg about Y** (cameras look +X).

## Density guidance

* 1500 oaks / 600x600 m (~1/240 m^2): 14-21% nadir closure
  (varies by spot). Reads as degraded-peatland mosaic -- the honest
  target (see V1 recalibration in visual-prd.md).
* Memory wall: 3000 instances OOM-killed the container here (each
  `<include>` duplicates mesh/texture buffers; no instancing in
  gz-rendering). 1500 is the verified ceiling on modest hosts; GPU
  workers with 16 GB+ can try 2000-4000 but should watch RSS.
* True dipterocarp closure (85%+) needs ~8000 crowns: infeasible via
  naive includes; needs GPU instancing or merged-crown impostors
  (open work).

## Frames

`renders/kalimantan-1500-{nadir,oblique,low}.png`: 1500-tree world,
pitched emitters, dark peat ground (current baseline).
`renders/kalimantan-{nadir,oblique,low}.gif`: 5 s promo loops (12
frames @ 420 ms, 480x270) from the same world; smoke/flame evolve
live. `renders/modal-firms-k1.gif`: 5 s 2D trajectory of the Modal
run (cropped to the flight area, fire ignitions overlaid).
Software GL (llvmpipe); GPU-worker frames pending and will differ in
shadows/AA, not layout. Nadir cam is offset 45 m from the ignition
(a cam directly overhead whites out inside the 100 m+ smoke column);
off-nadir columns show parallax lean, which is correct projection,
not a bug.
