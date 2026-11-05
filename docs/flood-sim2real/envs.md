# Flood hard environments + harder evals

Tracked in #81, shipped in #82. Three water worlds at hard
difficulty, built from real internet
assets (Fuel models, Polyhaven textures) against Wikimedia Commons
look references, evaluated with the same harder-eval harness as
FIRMS peat (`docs/firms-sim2real/harder-evals.md`) and
quake/slide (`docs/quake-slide-sim2real/envs.md`): several
animals/humans + routes, SAM 3.1 vs stub, single vs fleet, Baseten
frontier + Modal HuggingFace, Map POV + run + final segmentation
footage.

## Scenarios

| Scenario | Grid | World | Band (seed 7) | Victims (seed 7) |
|---|---|---|---|---|
| `flood_hard` | 60×60 | 300 m river town under ~1.1 m murky water | 0.73 hard | 5 (3h/1c/1a, trapped) |
| `flash_flood_hard` | 48×64 | 240×320 m valley on a swollen river | 0.76 hard | 6 (3h/2c/1a, mixed) |
| `tsunami_hard` | 60×60 | 300 m coastal strip, sea + scour + town | 0.73 hard | 5 (3h/1c/1a, mixed) |

- Flood town (`assets/structures/build_flood.py`): flooded
  house/shop rows, school shelter + evac post on a high-ground pad,
  marina dock, 2 rescue boats, channel buoys, submerged cars, drift
  debris, storm rain. 134 includes, seed 7.
- Flash valley: 24 m river channel with sand banks and mud bed,
  truss bridge as the only high crossing, bank homes, flank
  pine/oak forest + sluice boulders, rescue boat, storm rain. 98
  includes, seed 7.
- Tsunami coast: sand flat + surf, wooden pier, harbor dock, port
  warehouse, scoured town (collapsed homes + 10-piece debris
  field), 2 beached boats + 1 afloat, debris buoys, relief post on
  high ground, drizzle. 66 includes, seed 7.
- Look references (`refs/`): 2018 Ill river flood aerial, Windhoek
  flash-flood street, Mekong flooded building, Tohoku ASTER debris
  scene, Sendai + 2004 Banda Aceh tsunami aerials.
- Documented adaptations: staged school/ambulance/truss-bridge/pier
  gain PBR albedo (mesh-internal texture refs fail under ogre2);
  staged rescue-randy-sitting drops a nested remote-Fuel include;
  floodwater is a thin translucent PBR box (Polyhaven ships no
  water diffuse; high metalness mirrors the blue default sky, so
  the water is diffuse gray); `coast-water` retired (renders ~100x
  over nominal, cubemap-blue); staged wam-v scale experiment
  reverted (pinned renders correct — the scale shrank boats to
  invisibility); builds wipe the staging root so retired staged
  models cannot shadow pinned originals.

## Footage

- `renders/flood-town-{nadir,oblique,low}.{png,gif}`,
  `renders/flash-valley-{nadir,oblique,low}.{png,gif}`,
  `renders/tsunami-coast-{nadir,oblique,low}.{png,gif}`: verify
  stills + 5 s promo loops (12 frames @ 2 fps, 640 wide).
- `renders/flood-shelter-pad.png`, `renders/tsunami-harbor.png`:
  landmark closeups (school/PBR fix, dock/pier/buoys).
- `renders/survey-{flood_hard,flash_flood_hard,tsunami_hard}-7-nadir.{png,json}`:
  Map POV survey frames + yaw-90 sidecars (all 18 hazard zones
  project in-frame onto their water/damage sites, verified
  visually). Nadir frames are rotated 90° (image-up = world −X);
  the yaw-90 sidecar + `grid_to_pixel` encode this (same
  convention as quake/slide).

## SAM 3.1 on the new frames (live probe)

- Open-vocab on CG: flood `building:81` (road/vehicle/car/
  person/animal/water zero); flash `building:19, vehicle:2,
  car:2`; tsunami `building:34, vehicle:3, car:3`. Structures
  match; people/animals stay invisible as on peat/quake renders —
  and `water:0` everywhere, so the hazard concept needs prompts.
- Prompted mode (`hazard_point_proposer` with the `water` label,
  wired in `drone_mission` for the three flood scenarios):
  flood `water:8/8`, severity severe (0.33); flash `water:8/8`,
  moderate (0.11); tsunami `water:8/8`, severe (0.40).
- `water` was already in `HAZARD_CONCEPTS` (severity feed);
  `_hard` scenarios resolve to base flood/flash/tsunami concepts;
  survey frames load from all three renders dirs. SAM cells fuse
  the stub (1 scan/episode).

## Eval matrix

Tasks: `evals/flood.py` (`flood`, `flood_fleet`, `flash`,
`flash_fleet`, `tsunami`, `tsunami_fleet`), seed 7, mission
scorer. 48 LLM cells (4 models x 3 envs x single/fleet x
stub/SAM) + 6 greedy.

Models: Baseten `meta-models/muse-spark-open-1026` (frontier,
vision ON, temp 0), Modal Qwen2.5-7B / Mistral-7B-v0.3 /
Qwen2.5-14B-AWQ (text, temp 0, `DMB_VISION=text`). SAM cells: 1
scan/episode (static frame), fused stub.

Greedy baselines (scripted coverage, provider-free): flood
single/fleet 0.292 (1/5); flash single/fleet 0.252 (2/6);
tsunami single/fleet 0.103 (1/5). Steps 59, coverage 1.6-1.9%.

| run | comp | found | steps | tools | tokens | cover | min-d | routes |
|-----|------|-------|-------|-------|--------|-------|-------|--------|
| flood baseten single stub | 0.075 | 0/5 | 16 | 25 | 171,631 | 0.3% | 4 | 0 |
| flood baseten single SAM | 0.112 | 0/5 | 14 | 25 | 187,647 | 0.1% | 8 | 2 |
| flood baseten fleet stub | 0.340 | 1/5 | 21 | 31 | 117,871 | 0.3% | 1 | 0 |
| flood baseten fleet SAM | 0.150 | 0/5 | 20 | 30 | 126,096 | 0.2% | 6 | 1 |
| flood qwen7 single stub | 0.037 | 0/5 | 18 | 27 | 20,128 | 0.2% | 8 | 0 |
| flood qwen7 single SAM | 0.075 | 0/5 | 15 | 27 | 31,094 | 0.2% | 4 | 2 |
| flood qwen7 fleet stub | 0.200 | 1/5 | 17 | 19 | 13,885 | 0.2% | 2 | 0 |
| flood qwen7 fleet SAM | 0.000 | 0/5 | 20 | 43 | 23,400 | 0.1% | 8 | 1 |
| flood mistral single stub | 0.150 | 0/5 | 0 | 0 | 181,745 | 0.0% | — | 0 |
| flood mistral single SAM | 0.150 | 0/5 | 0 | 0 | 176,648 | 0.0% | — | 0 |
| flood mistral fleet stub | 0.150 | 0/5 | 0 | 0 | 166,093 | 0.1% | — | 0 |
| flood mistral fleet SAM | 0.150 | 0/5 | 0 | 0 | 205,093 | 0.1% | — | 0 |
| flood qwen14b single stub | 0.150 | 0/5 | 1 | 3 | 9,829 | 0.0% | 27 | 0 |
| flood qwen14b single SAM | 0.150 | 0/5 | 0 | 0 | 89,581 | 0.0% | — | 0 |
| flood qwen14b fleet stub | 0.112 | 0/5 | 12 | 14 | 2,479 | 0.2% | 7 | 0 |
| flood qwen14b fleet SAM | 0.150 | 0/5 | 10 | 16 | 125,735 | 0.2% | 9 | 0 |
| flash baseten single stub | 0.187 | 1/6 | 16 | 24 | 163,685 | 0.4% | 1 | 0 |
| flash baseten single SAM | 0.150 | 0/6 | 16 | 24 | 173,524 | 0.3% | 3 | 1 |
| flash baseten fleet stub | 0.150 | 0/6 | 25 | 32 | 107,888 | 0.5% | 3 | 0 |
| flash baseten fleet SAM | 0.298 | 1/6 | 26 | 32 | 73,664 | 0.5% | 2 | 0 |
| flash qwen7 single stub | 0.037 | 0/6 | 17 | 26 | 22,823 | 0.2% | 8 | 0 |
| flash qwen7 single SAM | 0.037 | 0/6 | 13 | 21 | 15,364 | 0.1% | 4 | 0 |
| flash qwen7 fleet stub | 0.112 | 0/6 | 13 | 21 | 22,892 | 0.2% | 8 | 0 |
| flash qwen7 fleet SAM | 0.000 | 0/6 | 16 | 30 | 34,577 | 0.4% | 4 | 0 |
| flash mistral single stub | 0.150 | 0/6 | 0 | 0 | 113,467 | 0.0% | — | 0 |
| flash mistral single SAM | 0.150 | 0/6 | 0 | 0 | 133,336 | 0.0% | — | 0 |
| flash mistral fleet stub | 0.150 | 0/6 | 0 | 0 | 191,244 | 0.1% | — | 0 |
| flash mistral fleet SAM | ERROR | — | — | — | — | — | — | — |
| flash qwen14b single stub | 0.075 | 0/6 | 10 | 19 | 18,545 | 0.2% | 4 | 0 |
| flash qwen14b single SAM | 0.280 | 1/6 | 15 | 22 | 23,020 | 0.3% | 0 | 0 |
| flash qwen14b fleet stub | 0.150 | 0/6 | 4 | 10 | 36,955 | 0.1% | 8 | 0 |
| flash qwen14b fleet SAM | 0.000 | 0/6 | 25 | 31 | 52,536 | 0.4% | 8 | 0 |
| tsunami baseten single stub | 0.112 | 0/5 | 11 | 24 | 171,384 | 0.2% | 10 | 0 |
| tsunami baseten single SAM | 0.112 | 0/5 | 19 | 25 | 176,044 | 0.3% | 6 | 0 |
| tsunami baseten fleet stub | 0.112 | 0/5 | 19 | 31 | 124,026 | 0.4% | 5 | 0 |
| tsunami baseten fleet SAM | 0.037 | 0/5 | 22 | 31 | 121,757 | 0.4% | 5 | 1 |
| tsunami qwen7 single stub | 0.075 | 0/5 | 12 | 18 | 11,837 | 0.1% | 8 | 0 |
| tsunami qwen7 single SAM | 0.150 | 0/5 | 0 | 0 | 9,403 | 0.0% | — | 0 |
| tsunami qwen7 fleet stub | 0.112 | 0/5 | 16 | 22 | 13,469 | 0.2% | 8 | 0 |
| tsunami qwen7 fleet SAM | 0.075 | 0/5 | 16 | 26 | 9,664 | 0.1% | 8 | 1 |
| tsunami mistral single stub | 0.150 | 0/5 | 0 | 0 | 184,479 | 0.0% | — | 0 |
| tsunami mistral single SAM | 0.150 | 0/5 | 0 | 0 | 140,629 | 0.0% | — | 0 |
| tsunami mistral fleet stub | ERROR | — | — | — | — | — | — | — |
| tsunami mistral fleet SAM | ERROR | — | — | — | — | — | — | — |
| tsunami qwen14b single stub | 0.150 | 0/5 | 2 | 10 | 8,390 | 0.0% | 27 | 0 |
| tsunami qwen14b single SAM | 0.150 | 0/5 | 13 | 20 | 27,710 | 0.1% | 10 | 0 |
| tsunami qwen14b fleet stub | 0.150 | 0/5 | 8 | 12 | 22,179 | 0.2% | 10 | 0 |
| tsunami qwen14b fleet SAM | 0.075 | 0/5 | 14 | 18 | 23,471 | 0.2% | 10 | 0 |
| flood greedy single | 0.292 | 1/5 | 59 | — | 0 | 1.6% | — | — |
| flood greedy fleet | 0.292 | 1/5 | 59 | — | 0 | 1.6% | — | — |
| flash greedy single | 0.252 | 2/6 | 59 | — | 0 | 1.9% | — | — |
| flash greedy fleet | 0.252 | 2/6 | 59 | — | 0 | 1.9% | — | — |
| tsunami greedy single | 0.103 | 1/5 | 59 | — | 0 | 1.6% | — | — |
| tsunami greedy fleet | 0.103 | 1/5 | 59 | — | 0 | 1.6% | — | — |

ERROR = Mistral 400 context overflow (prompt 16424 > 16384):
the fenced pseudo-call loop grows past the window and the episode
errors. 45/48 cells scored; the 3 remaining ERRORs failed 3
attempts each (2 more recovered on the final round).

Key findings:

- **5 finds in 45 scored** (flood baseten fleet-stub 0.34,
  flood qwen7 fleet-stub 0.20, flash baseten single-stub 0.19 +
  fleet-SAM 0.30, flash qwen14b single-SAM 0.28) — above the QS
  rate (1/36) but still a hard floor; tsunami is a perfect 0/14
  scored including the vision frontier.
- **Scripted coverage still wins**: greedy finds 1–2 victims per
  env at 1.6–1.9% coverage; LLM agents cover ~0.1–0.5% then
  submit. Coverage remains unscored, so early-submit stays
  score-rational.
- **SAM perception validates, routes don't discriminate**: SAM
  cells segment water 8/8 with severe/moderate severity and call
  `request_route_map` in 7 episodes, but with ~0 located victims
  calibrated routes cannot separate runs.
- **Mistral-7B fails the harness**: 0 actions in every completed
  cell (113–205k tokens of fenced pseudo-calls) plus 3 hard
  context-overflow errors after 3 attempts each — worse than QS,
  where the single overflow passed on retry.
- **Qwen14b slow-worker hang recurs**: one fleet cell stalled
  23 min mid-episode (killed); the capped retry
  (`--max-tokens 2048`) finished at 0.15.

## Footage index (runs)

- Run (fleet find): `renders/fl-flood-baseten-fleet-stub.gif`
  (+ `-final.png`) — frontier splits the town, finds 1/5.
- Run (fleet find): `renders/fl-flood-qwen7-fleet-stub.gif`
  (+ `-final.png`) — 7B model finds 1/5 at 14k tokens.
- Run (fleet SAM find): `renders/fl-flash-baseten-fleet-sam.gif`
  (+ `-final.png`, `-segmap.png`).
- Run (single SAM find): `renders/fl-flash-qwen14b-single-sam.gif`
  (+ `-final.png`, `-segmap.png`).
- Run (single find): `renders/fl-flash-baseten-single-stub.gif`
  (+ `-final.png`).
- Run (tsunami, 0 finds): `renders/fl-tsunami-baseten-fleet-sam.gif`
  (+ `-final.png`, `-segmap.png`).
