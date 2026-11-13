# Five-dimension benchmark analysis

## 1. Retrieval accuracy

| Strategy | Split | Hit@1 | Evidence Hit@3 |
|---|---|---|---|
| A | dev | 6/15 (40.0%) | 10/15 (66.7%) |
| A | test | 4/5 (80.0%) | 5/5 (100.0%) |
| B | dev | 9/15 (60.0%) | 13/15 (86.7%) |
| B | test | 3/5 (60.0%) | 5/5 (100.0%) |
| C | dev | 9/15 (60.0%) | 13/15 (86.7%) |
| C | test | 3/5 (60.0%) | 5/5 (100.0%) |

The predeclared selection rule chooses B: it has the highest development Evidence Hit@3, ties C on retrieval, and requires no caller filter. Test contains only five questions, so the 5/5 Hit@3 result is illustrative rather than evidence of general superiority. A's higher test Hit@1 conflicts with its weaker development results and lower coherence; it was not used to revise the selection.

## 2. Chunk coherence

The midpoint of each of the first ten sorted content-page IDs was fixed as the audit position. The containing chunk was reviewed using the 0–2 rubric. A scored 11/20 (mean 1.1/2); B and C each scored 18/20 (mean 1.8/2). Fixed windows frequently begin or end inside sentences. Paragraph blocks usually preserve a full explanation, although page boundaries and a paragraph ending with a colon can still leave context incomplete. Full labels and chunk text are in `manual_audit.json`.

## 3. Metadata usefulness

All 45 audited records (5 test questions × top-3 × 3 strategies) contained the correct `document_id`, `source`, physical `page`, and manifest-derived `category`; each chunk text was checked against the stated source page. Results were 15/15 for A, B and C. For C's filtered test question q18, all 3/3 results complied with `category=virtual_environments` (1/1 filtered question). Filter compliance is N/A for A and B because those strategies intentionally do not apply filters.

`page` makes every hit directly auditable, while `category` removes out-of-scope sections when the caller supplies a trusted scope. A limitation is that category is assigned from documented page ranges: it is reliable for this book but would need a new extraction rule for another corpus. Metadata completeness alone also does not guarantee retrieval relevance.

## 4. Grounding quality

For each strategy, all five test top-3 sets were rated 2/2: 0 questions at score 0, 0 at score 1, and 5 at score 2 (mean 2.0/2). Each set contains the complete recorded evidence and a physical page. This rates evidence sufficiency only; no answer-generation model was run, so these values must not be described as LLM answer accuracy. The labels are AI-assisted and non-independent; the student should confirm them before submission.

## 5. Data-strategy impact and failures

A→B changes only chunking. B uses 308 chunks versus A's 381, raises dev Hit@1 from 6/15 to 9/15 and dev Hit@3 from 10/15 to 13/15, and raises coherence from 1.1 to 1.8. Its measured initial embedding/upsert time was 8.519 seconds versus A's 10.762 seconds on this run. This supports paragraph-aware chunking for this structured PDF, without claiming the result transfers to other corpora.

B→C changes only caller-supplied metadata filtering. Aggregate exact-hit metrics tie because only three benchmark questions carry filters. On test q18, C removes the unrelated `modules` result that appears at rank 2 for B; all C results remain inside `virtual_environments`. However, q10 remains a miss for both B and C: filtering narrows the chapter but cannot repair semantic ranking or a chunk that does not include the complete recorded evidence.

Two representative errors:

- q14: A retrieves the correct page and nearly the complete evidence at rank 1, but the fixed boundary drops the beginning of the sentence. Under the declared definition, incomplete evidence is a miss. B/C instead rank material about `finally` and loop `else`, illustrating ambiguity around the word “else.”
- q10: A's top result begins in the middle of the relevant explanation, while B/C retrieve other package-import passages. The `modules` filter removes other categories but does not promote the exact `__init__.py`/`__all__` evidence into top-3.

The experiment is deterministic at the data/configuration level but HNSW implementation details, CPU timing and library versions can affect exact rankings and elapsed time. The audit reviewer also helped implement the pipeline, creating optimistic-label risk.
