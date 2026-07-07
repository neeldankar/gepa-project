# gepa-si-curriculum

A curriculum over **side-information (SI)** for [GEPA](https://github.com/gepa-ai/gepa)'s
reflection step. GEPA currently samples its reflection minibatch uniformly at random;
this project selects the examples whose *feedback is most useful to reflect on* — where
"useful" means **novel** and **actionable**, not merely hard.

> Status: research / WIP. Read `docs/proposition.md` for the full plan.

## Idea in one paragraph

Each GEPA iteration shows a proposer LLM ~3 examples plus their SI (the textual
diagnostic of a failure) and asks for an improved prompt. We replace the random draw
with a per-example **usefulness score** and oversample high scorers. The bet: SI
usefulness is a distinct axis from example difficulty. Framed as *acquisition / active
learning* (Expected Model Change / Expected Error Reduction), with novelty as
archive-based novelty search over diagnostic descriptors.

## Scorers

- **Novelty** — embedding k-NN, NCD/compression, failure-signature (SI points at a
  failure mode not yet addressed this run).
- **Actionability** — specificity of a single SI string.
- **Novelty × actionability** — the conjunctive hypothesis.
- Difficulty / parent identity / iteration are **controls**, not treatments.

## Method (see `docs/proposition.md`)

- Outcome = ΔU on `D_pareto` with rejected attempts = 0 (hurdle model), not acceptance.
- Offline **screening** via off-policy evaluation (IPS/DR, propensities known) +
  leave-one-run-out ranking → top 1–2 scorers.
- Live **confirmation**: paired-seed design, ≥6 seeds, pre-registered endpoint.
- Minibatch picked by diverse-batch selection (DPP), not top-k.

## Build order

1. **Logging hook** — capture the SI text GEPA discards (`src/.../logging/si_hook.py`).
2. **Static SI precompute** — one fixed reference prompt over `D_feedback`.
3. **Baselines** — ~5 random + 1–2 `b=1`, logging SI (static + faithful) and ΔU.
4. **Offline screen** — scorers, hurdle model, LORO ranking.
5. **Live confirm** — winner vs random, paired seeds.

## Repo layout

```
docs/        problem statement, proposition (v3), literature synthesis
src/         si_hook, curriculum sampler, scorers, offline analysis
experiments/ baseline run configs + scripts
tests/
```

## Dev

Cheap GEPA text benchmark (HotpotQA / HoVer). Dev budget ≤ $200; scorers are pennies,
cost = full runs.
