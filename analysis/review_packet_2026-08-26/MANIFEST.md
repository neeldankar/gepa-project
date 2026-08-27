# Manifest

Review packet assembled 2026-08-26. 18 files.

Supporting files are unmodified copies of repository artifacts. `PACKET.md`,
`MANIFEST.md` and `TRACEABILITY.md` were written for this packet.

| file | bytes | sha256 | what it is |
|---|---|---|---|
| `D1_swap_read.md` | 6633 | `4d14925da82b95589f626455c2825c03fe0c8505d57b29b47790259142453f54` | The pre-registered interpretation map for the HoVer batch swap, quoted verbatim from the brief that froze it, plus the recorded verdict. |
| `DECISIONS.md` | 3013 | `f59f689de51d148ea55cf90317995adfb03f188fa8a7bc4c7748a1eb9a401f3b` | Load-bearing decisions with reasons. Includes the 2026-07-22 endpoint estimator change that forbids tabling the state-dependent endpoints alongside the earlier specificity figure. |
| `MANIFEST.md` | 4802 | `6ebc6979d602c7edcd369b0b986368eb1ed4d4c9bbbc3b2b3b4bbab75d92deed` | This file list, with sha256 for each entry. |
| `PACKET.md` | 29775 | `0e5c3d1574750f3c2339cde8a3143844557c5bf6849812c88824e9dfef5630e4` | The review document. Read first. |
| `TRACEABILITY.md` | 13861 | `9e46cdf52f59151282f896ed9664ad6ce684460d8c8e597a35d4895a081b563d` | Maps every number in PACKET.md to a supporting file and line. |
| `design_v2_frozen.md` | 81600 | `a581f4386ae03b43657a8a7b3124e4712a29340ab8fd18cf3f1185bd1bb74bfc` | The frozen design. Hypotheses (section 3), arms (section 4), endpoint (section 8), interpretation map (section 9), statistical analysis plan (section 10), power and gate (section 11), pre-registered threat list (section 15). |
| `dose.json` | 64675 | `9f39646103a63d7d243f6c6e5c6a6a82035ad8e0d3ede8b95369b4c975b17768` | Dose artifact. Pooled and per-seed D, and the per-event record of all 6 novelty scores for 235 events. Input to the degeneracy descriptive. |
| `emit_descriptives.py` | 15001 | `a1cfed65d46ee19f4c33dab4a2e14fa6503c9341f09b680feb934892dcfc5f34` | Regenerates state_dep_degeneracy_descriptive.md from dose.json and the per-run summaries. Same double-computation discipline. |
| `emit_results.py` | 15630 | `c60cd689821cd8cd0d0c0087f50f4b8107fa2e6d27572c359f35c1aae9c62b8e` | Regenerates state_dep_results.md from the per-run artifacts. Every statistic computed twice by independent code paths, asserted to 1e-12. |
| `findings_summary.md` | 23338 | `822daaefdb588489e6820d12f066c1f29bee520cb99e2f4d6331471a322a32ec` | Running project ledger. Source for the IFBench block, the HoVer batch-swap block, the heterogeneity screen, and the state-dependent entry. Carries its own traceability map at the end. |
| `hover_screen_results.md` | 77439 | `eb466310c47de3d4cb35e1a0f06a9e1eeb2a63df5bcc29130268cf932df6c717` | The 108-cell heterogeneity screen. Source table for the surviving scorer's beta, interval, permutation p and leave-one-run-out count. |
| `liverun_ledger.json` | 3862 | `5e923a3a6299edd623ec807f6cb3dddc133e406bec18f120583551a1f6f916db` | Per-run API spend for the 24 optimization runs and their 24 scoring passes. |
| `mde_sim.py` | 6964 | `6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc` | Computes the MDE from the backfilled endpoints and evaluates the pre-registered gate. Zero cost, no network. |
| `stage1_backfill_endpoints.json` | 45399 | `d43805228bfdef2960e34c059a3ed1ef8ca0be571a39ec23531aa9f71c152a22` | The 8 backfilled Stage-1 endpoints under the current estimator. Input distribution for the MDE simulation. |
| `state_dep_degeneracy_descriptive.md` | 7466 | `9af86c071d05aac844f914ba70441df87ca6a19626b681f896175ad3e5ea4757` | The section 15-12 degeneracy distribution over 235 events and the section 15-4 monitored descriptives. Numbers only. |
| `state_dep_plan.md` | 65104 | `2ac8660e35f0e0a1089d456e07db8777387b4a8737c6a377ba70f90a850a68a3` | Working plan for the state-dependent experiment. Section 2 holds the pre-registration record: framing label, MDE, dose, gate arithmetic and simulator hash, written before results were read. |
| `state_dep_results.md` | 7436 | `cf1d254efb4628ea89fac4267d44abc7715fe0fdfcaa5e4fea6912cdfb11cee8` | Emitted results of the three-arm experiment. Per-run endpoints, per-arm means, the three contrasts with both bootstrap intervals and exact sign-flip p, and full provenance. Numbers only. |
| `verification_postswap.md` | 9331 | `16e21409e96e50248b4a35dae662309be262c59da2c27ef610bc3edfec42a2e3` | Independent verification pass behind the IFBench 2x2 swap figures, the same-input accept-disagreement figure, and the batch-size decision-flip figures. |

## Regenerating results at zero cost

`mde_sim.py`, `emit_results.py` and `emit_descriptives.py` make no model calls and no
network requests. The two emitters need the per-run artifact directories from the source
repository, which are not shipped here for size; `mde_sim.py` runs against
`stage1_backfill_endpoints.json` in this folder.

