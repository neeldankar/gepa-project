# HoVer necrosis kill-switch — results

**Date:** 2026-07-01 · run dir `necrosis` · **spend $1.9602** · logfile `logs/necrosis_step1.log`

**CAN conclude DEAD** (≈0/negative residual vs ΔU → won't survive the powered LORO screen → kill). **CANNOT conclude ALIVE** — a positive in-sample residual at n=1 run is necessary, not sufficient (no cross-run generalization tested). A pass = the powered $90–190 screen is *justified*, **never** "the scorer works."

## Run
reflection events: **33** · accepted candidates: **10** · LM calls: task 1848 + reflection 33 · event↔trace aligned: True · accept-inference matches candidates: True

## Outcome health
ΔU (PRIMARY): nonzero on **12%** of events, mean 0.0061, sd 0.0173. **⚠ ΔU is SPARSE/degenerate** — the necrosis read leans on the secondary (minibatch-improvement), flagged weaker.

minibatch-improvement (SECONDARY, robustness only — measured on the gate's own examples, collider-prone): mean -0.0000, sd 0.0907.

## Necrosis table (PRIMARY = ΔU)

scorer | raw ρ | residualized ρ [95% CI] | verdict | (c) delta resid ρ
---|---|---|---|---
`knn_novelty` (b) | -0.098 | -0.150 [-0.47,+0.19] | DEAD | -0.127
`ncd_novelty` (b) | +0.080 | +0.041 [-0.33,+0.43] | DEAD | -0.108
`actionability` (b) | +0.202 | +0.134 [-0.28,+0.46] | INCONCLUSIVE | -0.024
`nov_x_act` (b) | +0.210 | +0.091 [-0.29,+0.41] | INCONCLUSIVE | +0.118
`failure_mode` (b) | +0.265 | +0.225 [-0.06,+0.47] | INCONCLUSIVE | +0.225

**Feedback-only (a) sanity — should be ~null:**

scorer | raw ρ | residualized ρ [95% CI] | verdict
---|---|---|---
`knn_novelty` (a) | +0.009 | +0.006 [-0.45,+0.48] | DEAD
`ncd_novelty` (a) | +0.162 | +0.241 [-0.04,+0.57] | INCONCLUSIVE
`actionability` (a) | +0.064 | +0.092 [-0.34,+0.47] | INCONCLUSIVE
`nov_x_act` (a) | +0.018 | +0.016 [-0.42,+0.45] | DEAD

**SECONDARY (minibatch-improvement — robustness check, NOT the headline):**

scorer | raw ρ | residualized ρ [95% CI] | verdict
---|---|---|---
`knn_novelty` (b) | -0.159 | +0.004 [-0.39,+0.38] | DEAD
`ncd_novelty` (b) | +0.128 | +0.088 [-0.32,+0.45] | INCONCLUSIVE
`actionability` (b) | +0.373 | +0.136 [-0.20,+0.46] | INCONCLUSIVE
`nov_x_act` (b) | +0.370 | +0.199 [-0.15,+0.53] | INCONCLUSIVE
`failure_mode` (b) | +0.243 | +0.003 [-0.32,+0.36] | DEAD

## Verbatim reflection events (rich object)

### event 7 · predictor `gen_query` · ΔU=0.0000 · mbi=+0.000 · recall(ex1)=0.67  (byte-complete)
```
The area where the Changle River originates was formerly called Linchuan District.
['The Changle River originates from Daoshangling Mountain in Dongyang, Zhejiang Province.', 'The Changle River was formerly called Xijiang or West River.', 'Linchuan District is a district of Fuzhou city in Jiangxi Province, separate from Zhejiang Province.', 'There is no evidence linking the origin area of the Changle River to Linchuan District.', 'The Changle River originates from Daoshangling Mountain in Dongyang, Zhejiang Province.', 'Linchuan District is a district of Fuzhou city in Jiangxi Province, separate from Zhejiang Province.', 'There is no evidence linking the origin area of the Changle River to Linchuan District.', 'The Changle River originates from Daoshangling Mountain in Dongyang, Zhejiang Province.', 'Linchuan District is a district of Fuzhou city in Jiangxi Province, which is a separate province from Zhejiang.', 'There is no evidence linking the origin area of the Changle River to Linchuan District.']

The claim states that the area where the Changle River originates was formerly called Linchuan District. According to the notes, the Changle River originates from Daoshangling Mountain in Dongyang, Zhejiang Province. Linchuan District is located in Fuzhou city, Jiangxi Province, which is geographically separate from Dongyang, Zhejiang. Furthermore, there is no evidence that the origin area of the Changle River was ever called Linchuan District. Therefore, the claim seems inaccurate.
Was the area around Daoshangling Mountain in Dongyang, Zhejiang Province, formerly known as Linchuan District at any point in history?

Correctly retrieved 2/3 gold documents: ['Changle River', 'Linchuan District']. Documents remaining to be retrieved: ['Shengzhou'].
```
### event 31 · predictor `append_notes` · ΔU=0.0000 · mbi=+0.000 · recall(ex1)=0.67  (trimmed)
```
The TV series Soul Mates starred Christian Van Vuuren and an actor. Australian Broadcasting Corporation airs the show developed by the actor.
['Soul Mates is an Australian comedy series starring Christiaan Van Vuuren and Nicholas Boshier, aired on ABC2, part of the Australian Broadcasting Corporation.', 'Nicholas Boshier, co-star of Soul Mates, also helped develop the show.', 'Nicholas Boshier is an Australian actor and co-star of Soul Mates.', 'Nicholas Boshier helped develop the TV series Soul Mates.', 'Soul Mates stars Christiaan Van Vuuren and Nicholas Boshier.', 'Soul Mates aired on ABC2, part of the Australian Broadcasting Corporation.', 'Soul Mates is an Australian comedy series starring Christiaan Van Vuuren and Nicholas Boshier.', 'Nicholas Boshier is an Australian actor who co-starred in Soul Mates alongside Christiaan Van Vuuren.', 'Nicholas Boshier helped develop the TV series Soul Mates.', 'Soul Mates aired on ABC2, which is part of the Australian Broadcasting Corporation.', 'The Australian Broadcasting Corporation airs the show Soul Mates, which was developed by actor Nicholas Boshier.']
['Soul Mates (TV series) | Soul Mates is an Australian comedy series starring Chr …[trimmed]
```
### event 33 · predictor `gen_query` · ΔU=0.0000 · mbi=+0.111 · recall(ex1)=0.67  (trimmed)
```
The TV series Soul Mates starred Christian Van Vuuren and an actor. Australian Broadcasting Corporation airs the show developed by the actor.
['Soul Mates is an Australian comedy series starring Christiaan Van Vuuren and Nicholas Boshier.', 'The series aired on ABC2, which is part of the Australian Broadcasting Corporation.', 'Nicholas Boshier is an actor who co-starred in and helped develop Soul Mates.', 'Christiaan Van Vuuren and Nicholas Boshier were key figures in the creation and performance of Soul Mates.', 'Soul Mates is an Australian comedy series that starred Christiaan Van Vuuren and actor Nicholas Boshier.', 'Nicholas Boshier not only acted in Soul Mates but also helped develop it.', 'The series was aired on ABC2, which is part of the Australian Broadcasting Corporation.', 'Soul Mates is an Australian comedy series starring Christiaan Van Vuuren and Nicholas Boshier.', 'Nicholas Boshier is an actor who co-starred in and helped develop Soul Mates.', 'The series aired on ABC2, a channel under the Australian Broadcasting Corporation.', 'Christiaan Van Vuuren and Nicholas Boshier were key figures in both creation and performance of Soul Mates.']

The claim contains multiple  …[trimmed]
```

## Verdict — INCONCLUSIVE (not a clean kill)
**INCONCLUSIVE — the cheap kill-switch did NOT achieve a clean kill.** ΔU is sparse (nonzero on 12% of 33 events; the expected zero-inflated regime, as on IFBench), so the residual CIs are wide and exclude 0 for no scorer. **Clearly dead/null:** `knn_novelty`, `ncd_novelty`. **Inconclusive (positive point, underpowered):** `actionability`, `nov_x_act`, `failure_mode` — strongest `failure_mode` (resid +0.225 [-0.06,+0.47], (c) delta +0.225), whose signal is output-origin (rich reasoning+passage channel). This does NOT license killing the scorer set, and does NOT prove life. Resolving it needs the powered screen's redundancy-robust LOO target (not sparse ΔU) across multiple runs — funding it is a judgment call, neither auto-justified nor ruled out here.


**Power caveat:** n=33 events, ΔU nonzero on only 12% — bootstrap CIs are ~±0.4; the feedback-only (a) sanity did not cleanly reproduce a null (e.g. ncd_novelty(a) positive), consistent with low power. Reads are directional, not resolved. CAN conclude DEAD (clear ≤0); CANNOT conclude ALIVE.

