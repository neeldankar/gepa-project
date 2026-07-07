# RAW vs PARSED output diff — is anything stripped before storage?

$0, read-only on the frozen `logs/baseline_*`. Full terminal dump (byte blocks):
`analysis/raw_vs_parsed_diff.txt`. Generator: `scripts/diff_raw_vs_parsed.py`.

## The brief's named join does not exist (reported, not faked)
- **`raw_lm_outputs`** = dict keyed by COMPONENT, **1 entry per `proposal_end`** = the REFLECTION
  PROPOSER's raw output (the new instruction, fenced). **NOT** a per-example task completion.
- **"Generated Outputs"** = per-EXAMPLE field (b=3/event) in `reflective_dataset_built` = the task
  model's response.
- ⇒ 1-per-component vs 3-per-example have **no per-example join key**. Pairing them would fabricate a
  difference — refused, per the brief's guard.

## Task side — nothing stripped (the actual question)
`gepa default_adapter.py`: `batch_complete` (L132) → `assistant_response` (L139) →
`full_assistant_response = assistant_response` **verbatim** (L155) → `"Generated Outputs" =
full_assistant_response` (L195). No parse step. Corpus confirms: **0/394** events have any field on a
per-example record other than {Inputs, Generated Outputs, Feedback}. So **RAW(task) ≡ PARSED(task) by
construction** — "Generated Outputs" is the complete task completion. (Task LM = gpt-4.1-mini, a
non-reasoning model → `message.content` is the whole generation; no `reasoning_content` to strip.)

## The only raw-vs-parsed in the corpus = the PROPOSER's fence wrapper (not the task, not a signal)
Across **394 proposal_end events**: `raw_lm_outputs` vs `new_instructions` →
**0/394 equal, 394/394 raw longer, MAX len delta = 9 chars.** Example (iter 3): RAW 2755 → PARSED 2747
= **8 chars** = the ```` ``` ```` fence (` ```\n ` prefix + ` \n``` ` suffix); the parsed text is
otherwise byte-identical. So the single "stripped channel" anywhere is the markdown code-fence wrapper
on the candidate INSTRUCTION — **per-candidate, not per-example; no reasoning, no prose, ≤9 chars.**

## VERDICT
**No stripped task channel; no hidden reasoning anywhere.** "Generated Outputs" is the verbatim task
completion. The field the brief called RAW (`raw_lm_outputs`) is the proposer's own output at a
different granularity (per-component), and even its raw-vs-parsed delta is just a ≤9-char fence. The
three-section proposer object (Inputs + Generated Outputs + Feedback) is the whole task-side story —
the output-usefulness eyeball proceeds on the complete "Generated Outputs". **No new per-example signal
source exists in a stripped channel.**
