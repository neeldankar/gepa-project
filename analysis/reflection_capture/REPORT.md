# GEPA reflection-input EXACT capture + corpus audit — REPORT

**Method:** direct capture on a minimal IFBench GEPA run (6 train / 6 val, b=3, max_metric_calls=40,
task LM = reflection LM = `gpt-4.1-mini`). Two independent capture layers + the same run's logger.

## Run facts
- **Reflection calls fired: 4** (proposal_end=4). **Total LM calls ≈ 46** (≈42 task evals from 8
  evaluation_end × b=3 + 3 valset_evaluated × 6, plus the 4 reflection calls). The wire filter matched
  **exactly 4** → it caught the reflection calls and nothing else.
- **Actual spend: $0.0371** (task $0.0296 + reflection $0.0075).

## Three-way byte equality — PASS (this is the certainty, not inference)
For all 4 reflection calls, byte-for-byte:
**Layer A (wrapper: `CaptureLM.__call__` input) == Layer B (litellm wire `kwargs["messages"][0].content`)
== logged `proposal_end.prompts.system_prompt`.**

| call | len (chars) | A==B (wire) | A==logged |
|---|---|---|---|
| 1 | 3990 | ✅ | ✅ |
| 2 | 12648 | ✅ | ✅ |
| 3 | 9348 | ✅ | ✅ |
| 4 | 8790 | ✅ | ✅ |

⇒ The object the reflection LM receives **is** the litellm payload **is** the corpus field
`proposal_end.prompts.system_prompt`. Proven by capture; no reconstruction, no code/log inference.

## The exact object (call 1, raw .txt, verbatim, byte-complete)

```
I provided an assistant with the following instructions to perform a task for me:
` ``
You are a helpful assistant. Read the user's request carefully and follow every instruction and formatting constraint exactly.
` ``

The following are examples of different task inputs provided to the assistant along with the assistant's response for each of them, and some feedback on how the assistant's response could be better:
` ``
# Example 1
## Inputs
Find the integers \( n \) greater than or equal to 2 such that, if \( a \) denotes the smallest prime divisor of \( n \), one can find a positive divisor of \( n \) denoted \( d \) such that \( n = a^3 + d^3 \). Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.', 'I think yes.', 'I think no.', 'I think maybe.') The last word of each sentence, before punctuation, should be the word internal.

## Generated Outputs
I think yes internal.

## Feedback
Satisfied 1/2 constraints.
✗ [detectable_format:constrained_response] FAILED — Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')
✓ [last_word:last_word_sent] satisfied — The last word of each sentence, before punctuation, should be the word internal.

# Example 2
## Inputs
Maria owns a large estate with a total area of 240 hectares. … In your entire response, refrain from the use of any commas.

## Generated Outputs
Maria owns a total of 240 hectares. … Therefore Maria uses 115 hectares of land for agricultural production.

## Feedback
Satisfied 1/1 constraints.
✓ [punctuation:no_comma] satisfied — In your entire response, refrain from the use of any commas.

# Example 3
## Inputs
A tourist plans to visit the Grand Nord region of Mayotte … Answer with less than 2 letters. In your response, the word sandwich should appear less than 2 times.

## Generated Outputs
4 PM

## Feedback
Satisfied 1/2 constraints.
✗ [letters:letter_counting] FAILED — Answer with less than 2 letters.
✓ [keywords:frequency] satisfied — In your response, the word sandwich should appear less than 2 times.
` ``

Your task is to write a new instruction for the assistant.
Read the inputs carefully and identify the input format and infer detailed task description about the task I wish to solve with the assistant.
Read all the assistant responses and the corresponding feedback. Identify all niche and domain specific factual information … include it in the instruction …
Provide the new instructions within ``` blocks.
```
(Example 2/3 bodies elided here for readability; Example 1 is byte-complete. The full verbatim file is
`analysis/reflection_capture/reflect_1.txt` (3990 chars, all 3 records complete).)

## Structure of the per-example slice the proposer sees (b=3 batch; one slice = one curriculum unit)
`# Example N` → `## Inputs` (the actual task prompt) → `## Generated Outputs` (the parent model's
actual response) → `## Feedback` (the evaluator per-constraint checklist). **Predictor = Predict /
DefaultAdapter → NO reasoning/CoT field exists.**

## Prong-3 corpus audit (against the captured object)
| component of the reflection object | in 487-corpus? | field | recover |
|---|---|---|---|
| full rendered reflection prompt | ✅ | `proposal_end.prompts.system_prompt` | **$0 — proven byte-equal** |
| per-example **Inputs** | ✅ | `reflective_dataset_built.dataset[c][i].Inputs` | $0 |
| per-example **Generated Outputs** (parent output) | ✅ | `…[i]."Generated Outputs"` | $0 |
| per-example **Feedback** | ✅ | `…[i].Feedback` | $0 |
| current instruction (`<curr_param>`) | ✅ | embedded in `prompts`; also reconstructable | $0 |
| raw proposer output | ✅ | `proposal_end.raw_lm_outputs` | $0 |
| reasoning trace | n/a | — | never existed (Predict) |

## Branch → verdict
**ALL components the proposer sees are in the corpus, $0-recoverable; the only absent piece (reasoning)
never existed because the program is Predict.** → The usefulness eyeball can re-run on the REAL
reflection object (Inputs + parent Output + Feedback per example) for **$0**, directly off
`reflective_dataset_built` / `proposal_end.prompts`. No ~$30 re-log is needed. **PROCEED.**

**Note for the scorer work:** every scorer/probe to date scored only the **Feedback** string. The
captured object shows the proposer also reads the **Inputs** (task prompt) and **Generated Outputs**
(parent response) — the components never scored, and both are already in the corpus at $0.
