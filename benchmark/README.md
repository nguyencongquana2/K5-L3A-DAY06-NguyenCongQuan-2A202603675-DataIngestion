# Benchmark declaration

The 20 questions in `questions.json` were fixed before retrieval experiments on 2026-11-13. The split is 15 development questions and 5 held-out test questions. Questions q07, q10 and q18 exercise a caller-supplied `category` filter; q18 is held out in the test split.

Gold evidence is checked against normalized text from the stated physical PDF page by `starter/scripts/validate_benchmark.py`. The query sent to the embedder contains only `question`; expected answers and gold source/page are never appended to it. Strategy C applies `filter` only when it is present in the benchmark record.

The selection rule was fixed before inspecting test retrieval: maximize development Evidence Hit@3, then development Hit@1, then prefer higher manual grounding and lower ingestion cost. Test results are reported once after selecting on development results and are not used to tune parameters.

The questions and evidence were drafted with AI assistance and mechanically checked against the source. The student must review the gold labels and disclose any correction; a corrected test set is no longer an untouched holdout unless replaced before rerunning.
