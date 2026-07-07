# IFBench raw SI dump — the eyeball test

10 FAILED examples (score<1) from baseline logs, spanning seeds ['0', '1', '2', '3', '4']. Verbatim `reflective_dataset_built[...]['Feedback']` strings (the side-information the reflection proposer sees). Read-only on logs/ (phase2 untouched).

### [0] seed0 — types: keywords
```
Satisfied 2/3 constraints.
✓ [keywords:word_once] satisfied — Include keyword internet in your response.
✗ [keywords:keyword_specific_position] FAILED — Include keyword freedom in the 10-th sentence, as the 26-th word of that sentence.
✓ [keywords:forbidden_words] satisfied — Do not include keywords ['camp', 'catch', 'friend', 'heavy'] in the response.
```

### [1] seed0 — types: detectable_format, first_word, keywords, last_word
```
Satisfied 2/4 constraints.
✗ [keywords:exclude_word_harder] FAILED — Do not include keyword to in the response.
✗ [first_word:first_word_sent] FAILED — The first word of each sentence should be the word bit.
✓ [last_word:last_word_answer] satisfied — The last word of your response should be the word sensitive.
✓ [detectable_format:title] satisfied — Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.
```

### [2] seed1 — types: detectable_format, first_word, length_constraints
```
Satisfied 1/3 constraints.
✓ [detectable_format:title] satisfied — Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.
✗ [length_constraints:number_sentences] FAILED — Your response should contain less than 7 sentences.
✗ [first_word:first_word_sent] FAILED — The first word of each sentence should be the word visit.
```

### [3] seed1 — types: detectable_content, detectable_format, keywords, punctuation
```
Satisfied 2/4 constraints.
✗ [punctuation:punctuation_dot] FAILED — In your entire response, refrain from the use of . (i.e. dots) as punctuation and in general.
✗ [keywords:start_end] FAILED — Start and end your response with the same word (do not write anything after the last word, not even punctuation).
✓ [detectable_content:postscript] satisfied — At the end of your response, please explicitly add a postscript starting with P.P.S
✓ [detectable_format:multiple_sections] satisfied — Your response must have 6 sections. Mark the beginning of each section with Sec. X, such as:
Sec. 1
[content of section 1]
Sec. 2
[content of section 2]
```

### [4] seed2 — types: first_word, length_constraints
```
Satisfied 1/2 constraints.
✗ [first_word:first_word_sent] FAILED — The first word of each sentence should be the word bed.
✓ [length_constraints:number_words] satisfied — Answer with less than 517 words.
```

### [5] seed2 — types: change_case
```
Satisfied 0/1 constraints.
✗ [change_case:english_lowercase] FAILED — Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.
```

### [6] seed3 — types: detectable_format, first_word, keywords
```
Satisfied 2/3 constraints.
✓ [keywords:palindrome] satisfied — Include a palindrome in your response.
✓ [detectable_format:number_highlighted_sections] satisfied — Highlight at least 7 sections in your answer with markdown, i.e. *highlighted section*.
✗ [first_word:first_word_sent] FAILED — The first word of each sentence should be the word physics.
```

### [7] seed3 — types: first_word, language, paragraphs
```
Satisfied 2/3 constraints.
✓ [paragraphs:paragraphs2] satisfied — There should be 2 paragraphs. Paragraphs and only paragraphs are separated with each other by two line breaks. 
✓ [language:response_language] satisfied — Your ENTIRE response should be in Hebrew language, no other language is allowed.
✗ [first_word:first_word_answer] FAILED — The first word of your response should be the word school.
```

### [8] seed4 — types: copy, detectable_format, keywords, length_constraints
```
Satisfied 2/5 constraints.
✗ [copy:repeat_phrase] FAILED — Repeat the phrase The pen is mightier than sword exactly 2 times, transforming it slightly each time by replacing only one word in the center of the phrase.
✓ [keywords:frequency] satisfied — In your response, the word quiet should appear less than 3 times.
✗ [length_constraints:nth_paragraph_first_word] FAILED — There should be 7 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\n\n' in python. Paragraph 3 must start with word market.
✗ [keywords:keyword_specific_position] FAILED — Include keyword promotion in the 7-th sentence, as the 2-th word of that sentence.
✓ [detectable_format:title] satisfied — Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.
```

### [9] seed4 — types: keywords
```
Satisfied 0/1 constraints.
✗ [keywords:word_count_different_numbers] FAILED — In your response, the word swimming should appear 2 times.
```

## Note (fixed template vs varying — literal observation)
1. **Structure is 100% fixed**: every string is `Satisfied k/n constraints.` followed by one `✓/✗ [category:id] satisfied|FAILED — <description>` line per constraint. No free-form or semantically-variable prose appears anywhere.
2. **Descriptions are per-type templates with filled slots**, not free text — e.g. `Include keyword <W> in the <N>-th sentence, as the <M>-th word`; `Your ENTIRE response should be in <language>`; `Wrap every word bigram in double angular brackets`. The same constraint id always yields the same sentence with different slot values.
3. **The only thing that varies across the 10 is WHICH constraint ids appear** (here 11 types: change_case, copy, detectable_content, detectable_format, first_word, keywords, language, last_word, length_constraints, paragraphs, punctuation) **and their slot values**. Strict scaffold punctuation alone is ~18% of characters; counting the fixed description templates too, essentially all of the string is boilerplate and only the id-set + args carry information. It is a checklist.
