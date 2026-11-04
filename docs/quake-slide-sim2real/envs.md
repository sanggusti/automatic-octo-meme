# Quake / slide harder envs: earthquake_hard + landslide_hard

Date: 2026-11-04. The harder-eval harness (SAM-vs-stub, single-vs-fleet,
Baseten frontier + Modal HF, Map POV + run + final-segmentation
footage) applied to two new Gazebo-first environments built from real
internet assets against internet look references
(`refs/ref-{quake-street,quake-collapsed,slide-aerial,slide-road,slide-tapanuli}.jpg`,
Wikimedia Commons: 2011 Japan rubble street / collapsed building, 2021
Atami debris-flow aerial, road-block slide, North Tapanuli slide).

## Scenarios

- `earthquake_hard` (60x60, 300 m town): M7+ rupture, collapsed
  downtown core + industrial block + fire-station landmark, 6 hazard
  zones, aftershock phases that activate new rifts mid-run
  (`active_from_phase`). Victims: 2-4 human + 1-2 child + 1-2 animal,
  all trapped. Seed-7 draw: 5 victims, difficulty hard (0.73).
- `landslide_hard` (48x64, 240x320 m slope): monsoon slope failure,
  rock head-scarp, widening mud-and-boulder flow, blocked toe road,
  4 hazard zones, rain-coupled slip dynamics. Victims: 2-4 buried
  human + 0-1 buried child + 2-3 static animals. Seed-7 draw:
  6 victims, difficulty hard (0.70).

## Worlds (all meshes/textures pinned, no invented geometry)

- Quake town (`assets/structures/build_quake.py`): Fuel houses,
  apartments, collapsed structures, street rubble, tents, vehicles,
  barriers on a Polyhaven asphalt grid; dust columns + haze over
  collapse sites; eval victim draw placed. 76 includes, seed 7.
- Slide slope (`assets/structures/build_slide.py`): 12-deg tilted
  mud slope, rock scarp, 110 flow boulders, flank forest, buried
  cars, toe homes, blocked road, evac post; buried victims
  half-sunk. 213 includes, seed 7.
- Documented adaptations: staged house-1/house-2 copies gain PBR
  albedo (script-only materials render black under ogre2);
  `brown_mud_leaves_01` retired (giant salad at aerial scale) for
  fine-grain `brown_mud_02`; Fuel alias collisions fixed
  (first-wins: house-2's legacy `house_1` ref stole house-1's alias).

## Footage

- `renders/quake-town-{nadir,oblique,low}.{png,gif}`,
  `renders/slide-slope-{nadir,oblique,low}.{png,gif}`: verify
  stills + 5 s promo loops (12 frames @ 420 ms, 480x270).
- `renders/survey-{earthquake_hard,landslide_hard}-7-nadir.{png,json}`:
  Map POV survey frames + yaw-90 sidecars (all 10 hazard zones
  project in-frame onto their damage sites, verified visually).

## SAM 3.1 on the new frames (live probe 2026-11-04)

- Open-vocab on CG: quake `building:40, vehicle:2, car:2`
  (road/person/animal/tent zero); slide `road:1, building:2,
  vehicle:8, car:3` (person/animal zero). Structures match;
  people/animals stay invisible as on the peat renders.
- Prompted mode (new `hazard_point_proposer`: hazard-zone centers
  + offsets, phase-gated): quake `rubble:8/8`,
  severity minor(0.01); slide `debris:8/8`, severity minor(0.03).
- `rubble`/`debris` added to `HAZARD_CONCEPTS` (severity feed);
  `_hard` scenarios resolve to base concepts; survey frames load
  from both renders dirs. SAM cells fuse the stub (1 scan/episode).

## Eval matrix

Tasks: `evals/quake_slide.py` (`quake`, `quake_fleet`, `slide`,
`slide_fleet`), seed 7, mission scorer. 32 LLM cells (4 models x
2 envs x single/fleet x stub/SAM) + 4 greedy.

Models: Baseten `meta-models/muse-spark-open-1026` (frontier, vision
ON, temp 0, max-tokens 4096), Modal Qwen2.5-7B / Mistral-7B-v0.3 /
Qwen2.5-14B-AWQ (text, temp 0). SAM cells: 1 scan/episode (static
survey frame), fused stub. Tokens = total incl. cache/reasoning.

| run | comp | found | steps | tools | tokens | cover | min-d | routes |
|-----|------|-------|-------|-------|--------|-------|-------|--------|
| quake baseten single stub | 0.112 | 0/5 | 20 | 25 | 140,458 | 0.3% | 7 | 0 |
| quake baseten single SAM | 0.075 | 0/5 | 17 | 25 | 149,333 | 0.3% | 8 | 1 |
| quake baseten fleet stub | 0.248 | 1/5 | 20 | 31 | 102,493 | 0.3% | 2 | 0 |
| quake baseten fleet SAM | 0.112 | 0/5 | 20 | 31 | 129,206 | 0.3% | 3 | 0 |
| quake qwen7 single stub | 0.112 | 0/5 | 16 | 24 | 17,088 | 0.2% | 8 | 0 |
| quake qwen7 single SAM | 0.112 | 0/5 | 13 | 24 | 29,488 | 0.1% | 10 | 1 |
| quake qwen7 fleet stub | 0.075 | 0/5 | 20 | 26 | 23,625 | 0.2% | 8 | 0 |
| quake qwen7 fleet SAM | 0.075 | 0/5 | 16 | 22 | 24,754 | 0.2% | 10 | 0 |
| quake mistral single stub | 0.150 | 0/5 | 0 | 0 | 202,429 | 0.0% | — | 0 |
| quake mistral single SAM | 0.150 | 0/5 | 0 | 0 | 180,409 | 0.0% | — | 0 |
| quake mistral fleet stub | 0.150 | 0/5 | 0 | 0 | 176,906 | 0.0% | — | 0 |
| quake mistral fleet SAM | 0.150 | 0/5 | 0 | 0 | 185,426 | 0.0% | — | 0 |
| quake qwen14b single stub | 0.150 | 0/5 | 0 | 0 | 55,920 | 0.0% | — | 0 |
| quake qwen14b single SAM | 0.075 | 0/5 | 18 | 28 | 27,416 | 0.2% | 8 | 0 |
| quake qwen14b fleet stub | 0.112 | 0/5 | 13 | 15 | 23,686 | 0.2% | 10 | 0 |
| quake qwen14b fleet SAM | 0.150 | 0/5 | 4 | 6 | 80,919 | 0.1% | 8 | 0 |
| slide baseten single stub | 0.075 | 0/6 | 17 | 25 | 168,091 | 0.3% | 4 | 0 |
| slide baseten single SAM | 0.150 | 0/6 | 19 | 24 | 141,116 | 0.3% | 4 | 0 |
| slide baseten fleet stub | 0.150 | 0/6 | 22 | 31 | 118,830 | 0.4% | 2 | 0 |
| slide baseten fleet SAM | 0.150 | 0/6 | 17 | 26 | 138,390 | 0.3% | 4 | 0 |
| slide qwen7 single stub | 0.150 | 0/6 | 14 | 21 | 14,318 | 0.2% | 8 | 0 |
| slide qwen7 single SAM | 0.150 | 0/6 | 8 | 13 | 9,965 | 0.1% | 11 | 1 |
| slide qwen7 fleet stub | 0.150 | 0/6 | 8 | 14 | 1,835 | 0.1% | 8 | 0 |
| slide qwen7 fleet SAM | 0.150 | 0/6 | 16 | 28 | 19,849 | 0.2% | 8 | 0 |
| slide mistral single stub | 0.150 | 0/6 | 0 | 0 | 219,001 | 0.0% | — | 0 |
| slide mistral single SAM | 0.150 | 0/6 | 0 | 0 | 196,981 | 0.0% | — | 0 |
| slide mistral fleet stub | 0.150 | 0/6 | 0 | 0 | 145,309 | 0.0% | — | 0 |
| slide mistral fleet SAM | 0.150 | 0/6 | 0 | 0 | 153,577 | 0.0% | — | 0 |
| slide qwen14b single stub | 0.150 | 0/6 | 0 | 0 | 9,786 | 0.0% | — | 0 |
| slide qwen14b single SAM | 0.075 | 0/6 | 14 | 24 | 21,528 | 0.2% | 6 | 3 |
| slide qwen14b fleet stub | 0.150 | 0/6 | 32 | 35 | 43,362 | 0.5% | 8 | 0 |
| slide qwen14b fleet SAM | 0.112 | 0/6 | 6 | 10 | 47,379 | 0.1% | 6 | 0 |
| quake greedy single | 0.292 | 1/5 | 59 | — | 0 | 1.6% | — | — |
| quake greedy fleet | 0.290 | 1/5 | 60 | — | 0 | 1.6% | — | — |
| slide greedy single | 0.093 | 1/6 | 59 | — | 0 | 1.9% | — | — |
| slide greedy fleet | 0.091 | 1/6 | 60 | — | 0 | 1.9% | — | — |

Key findings:

- **Near-floor, but not uniform**: exactly 1 find in 32 LLM cells
  (quake Baseten fleet-stub, 0.248, min-d 2). Acting agents cover
  0.1-0.5% then submit; closest approaches 2-4 cells (Baseten)
  vs 6-11 (Modal). Smaller grids than firms (60x60/48x64 vs
  120x120) let greedy beat the floor (1 find each, 0.29/0.09).
- **SAM contributes routes, not finds**: SAM cells requested
  route maps in 4 episodes (quake baseten-single,
  quake qwen7-single, slide qwen7-single, slide qwen14b-single
  x3); every flown SAM cell saved seg artifacts
  (`rubble:8`/`debris:8`, severity minor 0.01-0.03). No SAM/stub
  find delta — victims stay subpixel at survey altitude.
- **Mistral non-agentic again**: all 8 cells 0 actions,
  145-219k tokens of fenced pseudo-calls. Its fleet prompts also
  sit 40 tokens over its 16k window — 3 first-attempt
  context-overflows, all passing on retry (marginal limit).
- **Qwen14b slide-stub hung 3x** (no first action in 10-26 min
  on a healthy endpoint; replicated requests return in 91-255 s):
  slow-worker + unbounded generation. Finished at 0.150 on the
  4th attempt with `--max-tokens 2048` (only cell with the cap).
- Fleet-vs-single shows no find delta (one action/step caveat
  as before); the lone find came from a fleet cell's spread pad.

Run footage (`renders/`): `qs-*-fleet-stub.gif` (the quake find),
`qs-quake-baseten-fleet-sam.gif`, `qs-slide-baseten-fleet-sam.gif`,
`qs-slide-qwen7-single-sam.gif`, `qs-quake-qwen7-single-sam.gif`,
`qs-slide-qwen14b-single-sam.gif` (+ `-final.png` each), and final
segmentations `qs-quake-baseten-fleet-sam-segmap.png`,
`qs-slide-qwen14b-single-sam-segmap.png`.
