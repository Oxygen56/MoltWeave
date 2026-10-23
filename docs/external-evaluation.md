# Independent public-material RAG readout

Status: completed by the main experiment runner after the adapter author's offline checks. `experiments/external-squad-v2` retains 48 actual model calls on the fixed 24 questions. Both g0 and g4 obtain EM 66.67%, F1 77.61 and gold-paragraph recall 91.67%; gain is zero. This is a reporting-only comparison after the core versions freeze. No outcome feeds back into optimization or version selection.

## Source, version and license

Dataset: official authors' SQuAD 1.1 development file, retrieved only from the pinned author repository.
- Repository: https://github.com/rajpurkar/SQuAD-explorer
- Commit: eee5fdbf62f8613a7812b03419e6b29617b74fd1
- File: dataset/dev-v1.1.json
- Pinned URL: https://raw.githubusercontent.com/rajpurkar/SQuAD-explorer/eee5fdbf62f8613a7812b03419e6b29617b74fd1/dataset/dev-v1.1.json
- Bytes: 4,854,279; expected version: 1.1; questions: 10,570, verified by counting this exact pinned file rather than relying on a dataset summary.
- SHA-256: 95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9
- Git blob SHA-1: e9a3f913ad1468ebe105b891334ca7b0bc0e2510

The initial source review read the pinned bytes in memory to verify these hashes and did not run question answering. The later actual readout cached the complete file outside the project; the full dataset is not committed.

The [official dataset page](https://rajpurkar.github.io/SQuAD-explorer/) distributes SQuAD under CC BY-SA 4.0. The repository's [software LICENSE](https://github.com/rajpurkar/SQuAD-explorer/blob/eee5fdbf62f8613a7812b03419e6b29617b74fd1/LICENSE) is MIT. Dataset content does not become MIT because the project or source repository software is MIT. Attribute Rajpurkar et al. and preserve the applicable data license for distributed excerpts/derivatives.

The adapter implements scoring definitions rather than executing a downloaded script: lowercase, remove ASCII punctuation and English articles, collapse whitespace; normalized exact match and multiset-token F1, maximizing over original answer annotations. See the authors' [evaluation implementation](https://github.com/rajpurkar/SQuAD-explorer/blob/eee5fdbf62f8613a7812b03419e6b29617b74fd1/evaluate-v2.0.py) for shared normalization/EM/token-F1 definitions and the [official viewer's metrics](https://github.com/rajpurkar/SQuAD-explorer/blob/gh-pages/javascripts/evaluate.js). This probe uses answerable v1.1 annotations and the classic v1.1 zero-common-token F1=0 convention; it does not add v2 no-answer thresholds.

## Fixed adaptation

Before results, freeze:
- 24 questions, seed 17; sort SHA-256(adapter version + seed + original question ID), then take the first 24.
- Original question and paragraph text retained.
- Each pool contains the annotated paragraph plus up to four other paragraphs from the same article. Choice and order use fixed hashes, never answers, ranking or model outcomes.
- No replacement because a question is difficult or either arm failed.
- Baseline g0 and the predeclared terminal generation gN only; a selected "best" intermediate generation is refused.
- One model/provider configuration; arm order alternates deterministically.
- 2,048 completion tokens per logical request. ModelClient records every physical attempt.

The loaded program's actual rag_score and rag_top_k select paragraphs through frozen runtime.rank. Paragraph metadata is age=0, trusted=1, global scope and no inferred entity assignment; no artificial recency/authority advantage is invented. Several scoring changes may therefore be rank-equivalent, and zero improvement is a valid possible result.

Each program prompt is used with the same fixed extractive-JSON instruction appended. The model sees only selected paragraphs and the original question. Answers, gold-paragraph identity and unselected paragraphs stay host-only. Memory, tools and retry mechanisms are not exercised here.

## Integrity and execution

Before model calls, the adapter checks the core manifest, completed status, terminal generation, transition chain and terminal hash. It creates a new output directory and freezes adapter/source/selection/program hashes.

Data is cached outside the source checkout, by default ~/.cache/moltweave/squad11. Every load verifies size, SHA-256 and Git-blob hash. No alternate mirror is accepted. A source/version mismatch is measurement failure, not a score.

After root freezes the official core run, invoke with a fresh output directory:

    PYTHONPATH=src python3 -m moltweave.external_eval \
      experiments/official-run experiments/external-squad-readout \
      --last-generation g4 --count 24 --seed 17 --distractors 4

This illustrates the interface; it does not assert those paths or g4 results exist. Credentials use ModelClient's environment; do not put them in command arguments or Git.

Outputs:
- manifest.json: source/data/adapter/core/program hashes, question IDs, configuration and status.
- calls/: original model requests/responses and physical-attempt records.
- predictions/: prediction, EM/F1, ranking/features, selected IDs, paragraph recall and citation visibility.
- result.json: EM/F1 on a 0–100 scale and terminal-minus-g0 differences.
- failed.json: incomplete measurement and completed work after an exception; missing scores are not invented.

EM/F1 are answer metrics; citation visibility and annotated-paragraph recall are separate diagnostics. Another paragraph may support the answer, so annotated-paragraph recall is not a perfect support oracle. Model self-grading is not used.

The full 10,570-question dataset stays in the external local cache. This release deliberately publishes the 48 raw readout receipts containing the selected public questions/paragraphs, with attribution and CC BY-SA 4.0 terms in `experiments/external-squad-v2/NOTICE.md` and `THIRD_PARTY_NOTICES.md`. They are not gitignored or private participant traces. Do not add private model calls or the full dataset to Git.

v3's exact execution host is archived. After maintenance changes the live client, a historical external reproduction can use the maintained transport-safety wrapper:

    python scripts/reproduce_frozen.py --experiment experiments/joint-v3 \
      --output experiments/my-squad-reproduction --external-only

The wrapper records a declared HTTPS/no-redirect/no-environment-proxy transport overlay; it does not promise bit-for-bit original transport. Reusing this public 24-question slice is reproduction, not a new untouched test.

## Claims and stopping boundary

Call this "a fixed 24-question adapted RAG/prompt readout on official public SQuAD 1.1 dev material." It is not native/full SQuAD, an official leaderboard score, cross-business validation or a direct causal P estimate.

The old public dataset may have appeared in model pretraining; exposure is unknown. This complements synthetic tests but does not establish contamination-free generalization.

Retain zero gain, regressions, wrong answers, format failures and incomplete measurements. Do not change questions, prompts, top-k or selected generation after seeing results. Later adjustments need a new declared experiment and separate holdout, retaining this readout.

Offline implementation checks cover metrics, deterministic construction, answer-independent selection and invalid-span rejection on a tiny fabricated fixture. If the pinned official source already exists in the external cache, an additional regression checks its integrity, 10,570 unique question IDs and fixed probe construction; tests never download it. A host-only source audit found zero invalid answer offsets across the full pinned file and confirmed the 24 selected questions each have five distinct candidate paragraphs. These checks do not measure real-model performance.

The first source-loading attempt, `experiments/external-squad-v1`, incorrectly expected 10,689 questions despite valid bytes/SHA/blob verification. It stopped before any model call and remains `measurement_incomplete`. The corrected attempt used a fresh output directory and completed; the question selection was unchanged. This was a data-loader repair, not an RSI improvement.

