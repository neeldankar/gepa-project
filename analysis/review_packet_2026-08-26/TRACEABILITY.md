# Traceability: every number in PACKET.md

Generated mechanically. Each numeric token in `PACKET.md` was searched for, as a literal
string, in every supporting file in this folder. The table gives the first file and line
where each appears.

- distinct numeric tokens checked: **249**
- traced to a supporting file: **246**
- not literal in any supporting file: **3** (listed first, with derivation)

Structural numbers (section numbers, counts of items in a list, the year, powers of two
used in prose) are excluded from the check. Every number that states a measurement,
an interval, a bound or a cost is included.

## Flagged: derived, not literal in any file

These are kept in PACKET.md rather than dropped, and are flagged here as required.

| value | PACKET.md lines | derivation |
|---|---|---|
| 1.615 | 216 | Derived. MDE / SD of the 8 backfilled endpoints = 0.06332 / 0.039206. The endpoints are in stage1_backfill_endpoints.json and the MDE is in state_dep_plan.md and state_dep_results.md, so the ratio is checkable, but the number itself is not literal in any shipped file. |
| 8.3355 | 506 | Reconstructed from run logs, which are NOT shipped in this packet. Dose computation spend, summed across three process restarts because per-process meters reset. PACKET.md section 8 says so explicitly. Not checkable here. |
| 39.39 | 506 | Reconstructed from run logs, which are NOT shipped in this packet. Stage-1 backfill spend, summed across per-seed meters plus one abandoned process. PACKET.md section 8 says so explicitly. Not checkable here. |

## Traced

| value | PACKET.md lines | first appears in |
|---|---|---|
| 26. | 3 | `D1_swap_read.md:6` |
| 17 | 4, 513 | `D1_swap_read.md:13` |
| 92.2 | 42 | `findings_summary.md:6` |
| 219 | 43, 43 | `design_v2_frozen.md:87` |
| 487 | 66 | `dose.json:191` |
| 382 | 66, 70, 93, 94 | `dose.json:9` |
| 54 | 66 | `design_v2_frozen.md:75` |
| 0.000 | 76 | `D1_swap_read.md:6` |
| 95 | 76, 78, 92, 93, 127, 151... | `D1_swap_read.md:47` |
| 0.243 | 76 | `findings_summary.md:41` |
| +0.04 | 77 | `D1_swap_read.md:49` |
| 0.111 | 78 | `dose.json:308` |
| 0.359 | 78 | `findings_summary.md:44` |
| 0.011 | 83 | `design_v2_frozen.md:227` |
| 0.90 | 84 | `DECISIONS.md:38` |
| 121 | 84 | `design_v2_frozen.md:75` |
| 0.2 | 84 | `D1_swap_read.md:80` |
| 0.340 | 88 | `findings_summary.md:51` |
| 0.313 | 88 | `findings_summary.md:51` |
| 0.367 | 88 | `dose.json:1123` |
| 0.63 | 88 | `design_v2_frozen.md:226` |
| 7.74 | 89 | `findings_summary.md:51` |
| +0.0054 | 92 | `design_v2_frozen.md:227` |
| -0.0116 | 93 | `design_v2_frozen.md:227` |
| +0.0242 | 93 | `design_v2_frozen.md:227` |
| 0.033 | 93 | `design_v2_frozen.md:227` |
| -0.0011 | 93 | `findings_summary.md:21` |
| -0.0243 | 93 | `findings_summary.md:82` |
| +0.0228 | 93 | `dose.json:2617` |
| 6.7 | 107, 403 | `findings_summary.md:69` |
| 267 | 107, 403 | `dose.json:438` |
| 6.0 | 108 | `D1_swap_read.md:6` |
| 0.415 | 111, 115, 402, 472 | `design_v2_frozen.md:469` |
| 764 | 111, 402 | `dose.json:10` |
| 0.203 | 112, 402 | `dose.json:2264` |
| 0.104 | 113, 403 | `dose.json:165` |
| 0.372 | 113 | `findings_summary.md:93` |
| 0.309 | 113 | `dose.json:1206` |
| 243 | 121 | `D1_swap_read.md:14` |
| 100 | 121 | `design_v2_frozen.md:188` |
| 300, | 122, 453 | `design_v2_frozen.md:236` |
| 4.1 | 122, 453, 487 | `design_v2_frozen.md:236` |
| 74.09 | 123 | `D1_swap_read.md:14` |
| +0.0274 | 129, 406 | `D1_swap_read.md:49` |
| +0.0149 | 129, 143, 407 | `D1_swap_read.md:49` |
| +0.0415 | 129, 407 | `D1_swap_read.md:49` |
| 0.0191 | 129, 144 | `D1_swap_read.md:49` |
| 0.0177 | 129 | `D1_swap_read.md:49` |
| +0.0169 | 130, 410 | `D1_swap_read.md:50` |
| -0.0040 | 130, 410 | `D1_swap_read.md:50` |
| +0.0367 | 130, 410 | `D1_swap_read.md:50` |
| 0.0293 | 130, 411 | `D1_swap_read.md:50` |
| 108 | 148 | `design_v2_frozen.md:239` |
| +0.03794 | 153 | `design_v2_frozen.md:242` |
| +0.01045 | 153 | `design_v2_frozen.md:243` |
| +0.07031 | 153 | `design_v2_frozen.md:243` |
| 0.0013 | 153, 154 | `design_v2_frozen.md:243` |
| +0.03877 | 154 | `design_v2_frozen.md:244` |
| +0.01068 | 154 | `findings_summary.md:159` |
| +0.07011 | 154 | `findings_summary.md:159` |
| +0.19560 | 155 | `findings_summary.md:160` |
| +0.09344 | 155 | `findings_summary.md:160` |
| +0.29185 | 155 | `findings_summary.md:160` |
| 0.0009 | 155 | `findings_summary.md:160` |
| 0.0429 | 157, 169 | `design_v2_frozen.md:254` |
| 235 | 157, 217, 308, 320, 321, 502 | `DECISIONS.md:26` |
| +0.00122 | 158 | `findings_summary.md:164` |
| 0.9126 | 158 | `findings_summary.md:164` |
| 17. | 159 | `D1_swap_read.md:13` |
| 118 | 164, 466 | `design_v2_frozen.md:258` |
| 198 | 164, 466 | `design_v2_frozen.md:258` |
| 0.03794 | 169 | `design_v2_frozen.md:242` |
| +0.1247 | 172 | `findings_summary.md:175` |
| 0.0709 | 172 | `findings_summary.md:175` |
| 0.0994 | 177 | `dose.json:155` |
| 20 | 195, 329 | `D1_swap_read.md:6` |
| 50 | 205 | `D1_swap_read.md:36` |
| 150 | 205, 502 | `design_v2_frozen.md:102` |
| 24 | 206, 261, 423, 494, 500, 505... | `D1_swap_read.md:13` |
| 0.06332 | 216, 219, 436, 451 | `emit_results.py:47` |
| 1.4431827353722393 | 217 | `dose.json:4` |
| 0.08213 | 218, 219 | `dose.json:371` |
| 0.0273768 | 220, 278, 281, 281, 437 | `findings_summary.md:265` |
| 15 | 243 | `D1_swap_read.md:49` |
| 256 | 248 | `design_v2_frozen.md:4` |
| 10,000 | 249 | `emit_results.py:49` |
| 20260709, | 249 | `design_v2_frozen.md:71` |
| -0.001111 | 254 | `findings_summary.md:258` |
| -0.025833 | 254 | `findings_summary.md:258` |
| +0.031667 | 254, 283 | `findings_summary.md:258` |
| -0.022500 | 254, 256 | `findings_summary.md:258` |
| +0.039722 | 254, 283 | `findings_summary.md:258` |
| 0.9688 | 254 | `findings_summary.md:258` |
| -0.012778 | 255 | `findings_summary.md:259` |
| -0.039444 | 255 | `findings_summary.md:259` |
| +0.021118 | 255, 284 | `findings_summary.md:259` |
| -0.035556 | 255, 268, 271 | `findings_summary.md:259` |
| +0.029444 | 255, 284 | `findings_summary.md:259` |
| 0.4844 | 255 | `dose.json:13` |
| -0.011667 | 256, 299 | `findings_summary.md:260` |
| -0.023611 | 256 | `findings_summary.md:260` |
| +0.001667 | 256, 285 | `findings_summary.md:260` |
| +0.003056 | 256, 285 | `findings_summary.md:260` |
| 0.1328 | 256, 299 | `dose.json:1102` |
| 0.599167 | 258 | `findings_summary.md:262` |
| 0.029118 | 258 | `findings_summary.md:262` |
| 0.587500 | 258 | `findings_summary.md:262` |
| 0.023576 | 259 | `findings_summary.md:262` |
| 0.586389 | 259 | `findings_summary.md:263` |
| 0.031144 | 259 | `findings_summary.md:263` |
| 0.633333 | 265 | `stage1_backfill_endpoints.json:1003` |
| 0.628889 | 265 | `state_dep_results.md:24` |
| 0.571111 | 265, 272 | `state_dep_results.md:45` |
| -0.057778 | 265 | `state_dep_results.md:45` |
| -0.062222 | 265 | `state_dep_results.md:66` |
| -0.004444 | 265, 271, 272 | `state_dep_results.md:24` |
| 0.617778 | 266 | `state_dep_results.md:25` |
| 0.593333 | 266 | `stage1_backfill_endpoints.json:634` |
| 0.568889 | 266, 268, 269, 272 | `state_dep_results.md:28` |
| -0.024444 | 266, 266 | `state_dep_results.md:25` |
| -0.048889 | 266 | `state_dep_results.md:67` |
| 0.564444 | 267 | `state_dep_results.md:26` |
| 0.591111 | 267, 270 | `state_dep_results.md:26` |
| 0.575556 | 267, 272 | `state_dep_results.md:31` |
| -0.015556 | 267, 337 | `state_dep_results.md:47` |
| +0.011111 | 267 | `state_dep_results.md:28` |
| +0.026667 | 267 | `state_dep_results.md:26` |
| 0.602222 | 268 | `state_dep_results.md:27` |
| 0.566667 | 268 | `state_dep_results.md:27` |
| +0.002222 | 268, 272 | `state_dep_results.md:48` |
| -0.033333 | 268 | `state_dep_results.md:69` |
| 0.557778 | 269 | `state_dep_results.md:28` |
| 0.657778 | 269, 335 | `findings_summary.md:303` |
| +0.100000 | 269, 336 | `DECISIONS.md:38` |
| +0.088889 | 269 | `state_dep_results.md:70` |
| -0.011111 | 269, 270 | `state_dep_results.md:28` |
| 0.584444 | 270 | `stage1_backfill_endpoints.json:27` |
| 0.573333 | 270 | `stage1_backfill_endpoints.json:272` |
| -0.017778 | 270 | `state_dep_results.md:71` |
| -0.006667 | 270, 272 | `state_dep_results.md:29` |
| 0.640000 | 271 | `hover_screen_results.md:36` |
| 0.608889 | 271 | `state_dep_results.md:30` |
| 0.604444 | 271 | `state_dep_results.md:51` |
| -0.031111 | 271 | `state_dep_results.md:30` |
| 0.041718 | 312 | `state_dep_degeneracy_descriptive.md:32` |
| 0.019122 | 312 | `state_dep_degeneracy_descriptive.md:32` |
| 0.009070 | 312 | `hover_screen_results.md:73` |
| 0.026553 | 312 | `state_dep_degeneracy_descriptive.md:32` |
| 0.039240 | 312 | `state_dep_degeneracy_descriptive.md:32` |
| 0.053986 | 312 | `state_dep_degeneracy_descriptive.md:32` |
| 0.099093 | 312 | `state_dep_degeneracy_descriptive.md:32` |
| 0.111916 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.053113 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.019604 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.069448 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.100014 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.147389 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.281178 | 313 | `state_dep_degeneracy_descriptive.md:33` |
| 0.059437 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 0.026932 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 0.013339 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 0.038506 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 0.058594 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 0.074774 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 0.149801 | 314 | `state_dep_degeneracy_descriptive.md:34` |
| 1.655675 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 0.776979 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 0.351328 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 1.037291 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 1.553828 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 2.142307 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 3.850752 | 315 | `state_dep_degeneracy_descriptive.md:35` |
| 4.444318 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 2.155840 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 0.845162 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 2.676116 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 4.028318 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 5.925279 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 10.595353 | 316 | `state_dep_degeneracy_descriptive.md:36` |
| 2.357535 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 1.094513 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 0.533328 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 1.534253 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 2.282464 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 3.008203 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 5.650293 | 317 | `state_dep_degeneracy_descriptive.md:37` |
| 0.533 | 322 | `findings_summary.md:280` |
| 1.500000 | 329 | `dose.json:11` |
| 1.5 | 329 | `dose.json:11` |
| 0.345631 | 350 | `state_dep_degeneracy_descriptive.md:108` |
| 0.102666 | 350 | `state_dep_degeneracy_descriptive.md:116` |
| 31.2500 | 350 | `findings_summary.md:291` |
| 3.3700 | 350 | `state_dep_degeneracy_descriptive.md:110` |
| 11.5000 | 350 | `findings_summary.md:291` |
| 2.0000 | 350 | `D1_swap_read.md:1` |
| 0.255815 | 351 | `state_dep_degeneracy_descriptive.md:109` |
| 0.085197 | 351 | `state_dep_degeneracy_descriptive.md:117` |
| 26.0000 | 351 | `D1_swap_read.md:6` |
| 2.0702 | 351 | `state_dep_degeneracy_descriptive.md:117` |
| 7.5000 | 351 | `emit_results.py:127` |
| 1.7728 | 351 | `state_dep_degeneracy_descriptive.md:117` |
| 0.383817 | 352 | `state_dep_degeneracy_descriptive.md:110` |
| 0.081259 | 352 | `state_dep_degeneracy_descriptive.md:118` |
| 23.3750 | 352 | `state_dep_degeneracy_descriptive.md:110` |
| 1.4079 | 352 | `state_dep_degeneracy_descriptive.md:118` |
| 9.8750 | 352 | `state_dep_degeneracy_descriptive.md:110` |
| 1.4577 | 352 | `state_dep_degeneracy_descriptive.md:118` |
| 32 | 358, 359, 361 | `D1_swap_read.md:59` |
| 0.312500 | 358, 359, 361 | `state_dep_degeneracy_descriptive.md:124` |
| 27 | 358, 360, 362, 365 | `D1_swap_read.md:49` |
| 0.222222 | 358, 360, 363 | `state_dep_degeneracy_descriptive.md:129` |
| 23 | 358, 360, 362, 362, 364 | `DECISIONS.md:26` |
| 0.391304 | 358, 360, 362, 362, 364 | `state_dep_degeneracy_descriptive.md:136` |
| 30 | 359 | `design_v2_frozen.md:64` |
| 0.100000 | 359 | `DECISIONS.md:38` |
| 22 | 359, 365 | `D1_swap_read.md:80` |
| 0.454545 | 359 | `state_dep_degeneracy_descriptive.md:141` |
| 35 | 360 | `DECISIONS.md:26` |
| 0.228571 | 360 | `state_dep_degeneracy_descriptive.md:126` |
| 25 | 361, 363, 364, 365 | `D1_swap_read.md:67` |
| 0.320000 | 361, 363 | `dose.json:1811` |
| 0.230769 | 361, 363 | `state_dep_degeneracy_descriptive.md:137` |
| 13 | 362, 365 | `D1_swap_read.md:67` |
| 0.481481 | 362, 365 | `state_dep_degeneracy_descriptive.md:128` |
| 36 | 363 | `D1_swap_read.md:50` |
| 29 | 364 | `D1_swap_read.md:50` |
| 0.413793 | 364 | `state_dep_degeneracy_descriptive.md:130` |
| 0.280000 | 364, 365 | `dose.json:67` |
| 11 | 365 | `D1_swap_read.md:13` |
| 0.500000 | 365 | `design_v2_frozen.md:538` |
| 5.5 | 397, 443 | `state_dep_degeneracy_descriptive.md:83` |
| 5.8 | 418 | `state_dep_plan.md:45` |
| 16 | 423 | `D1_swap_read.md:50` |
| 2.3 | 436 | `design_v2_frozen.md:612` |
| 5.9 | 462 | `state_dep_degeneracy_descriptive.md:36` |
| 764. | 472 | `dose.json:10` |
| 0.0 | 485 | `D1_swap_read.md:6` |
| 3.2 | 486 | `design_v2_frozen.md:137` |
| 3000, | 487 | `dose.json:1412` |
| 300 | 488 | `design_v2_frozen.md:236` |
| 50, | 491 | `D1_swap_read.md:36` |
| 150, | 492 | `design_v2_frozen.md:102` |
| 189 | 504 | `dose.json:235` |
| 3.2336 | 505 | `state_dep_plan.md:8` |
| 5.1942 | 505 | `state_dep_plan.md:8` |
| 132.7603 | 505, 510 | `state_dep_plan.md:137` |

