# Research discovery and decision memory

This module supplies research evidence to the RSI process. It does not replace
the process with a paper-news product. Discovery proposes sources; review creates
an immutable evidence packet; an operator records a decision; independent
experiments, when actually performed, produce separate effect records.

## What currently runs

- Public arXiv Atom, RSS 2, and RDF/RSS 1 discovery, with base-ID deduplication and
  separate version observations. Missing RSS versions remain **unknown**, never
  invented as v1. Observing an older or unversioned entry does not replace an
  already-known newer explicit version. Discovery records a source hash and time.
- Metadata/abstract packets without a model. Explicit HTML/text retrieval and an
  optional `llm.ModelClient` support model-assisted reading. The packet states the
  exact URL/version, text hash, characters read, truncation, failures, and scope.
- Local SQLite persistence with distinct `papers`, `versions`, `packs`,
  `decisions`, and `effects` tables. Packets and feedback/effect events are inserted
  as new records; adopting a proposal does not rewrite its facts or create an effect.
- Actor-scoped, context-aware long-term feedback retrieval. Matching is transparent
  lexical overlap, including Chinese bigrams. `project`, `tenant`, `environment`,
  and `scope` are strict filters when supplied. Synthetic feedback is excluded by
  default. Future reviews attach relevant decision IDs as local context references.
  With explicit `--use-decision-context`, selected historical reasons can also
  inform the model's proposal fit and evidence requests. This defaults to **off**.

This is **retrieval-based decision memory**, not a trained preference model or a
demonstration that the research-search policy P has evolved. Genuine human
decisions and later held-out evaluations are still needed for that claim. No
synthetic feedback is created by discovery or review.

## CLI

From the checkout, install the project in editable mode when packaging is ready,
or set `PYTHONPATH=src`. The examples below use the latter and Python 3.11+:

```bash
PYTHONPATH=src python3 -m moltweave.research discover \
  --query 'all:"agent memory"' --max-results 5 --store .moltweave/research

PYTHONPATH=src python3 -m moltweave.research discover \
  --feed-url https://rss.arxiv.org/rss/cs.AI --max-results 20

PYTHONPATH=src python3 -m moltweave.research papers

# Metadata/abstract only; does not call a model.
PYTHONPATH=src python3 -m moltweave.research review 2512.18746

# Explicitly fetch the arXiv HTML version; use the configured real ModelClient.
# Model credentials are read by moltweave.llm, not this module.
PYTHONPATH=src python3 -m moltweave.research review 2512.18746 \
  --full-text --model --context '{"project":"agent-memory"}'

# Explicit opt-in: SEND matching historical reasons/context to the configured
# model provider. --actor is provenance, not authenticated owner identity.
PYTHONPATH=src python3 -m moltweave.research review 2512.18746 \
  --full-text --model --actor owner --context '{"project":"agent-memory"}' \
  --use-decision-context

# Human-operated command: replace PACK_ID with a real local packet ID.
PYTHONPATH=src python3 -m moltweave.research feedback PACK_ID \
  --decision request_evidence --reason 'Need a comparison against the current retrieval mechanism' \
  --actor owner --context '{"project":"agent-memory","goal":"reliable retrieval"}'

PYTHONPATH=src python3 -m moltweave.research memory \
  --query 'retrieval mechanism' --actor owner --context '{"project":"agent-memory"}'

PYTHONPATH=src python3 -m moltweave.research show PACK_ID
```

`--store` is accepted before or after the command. `review --source-url URL`
supports an explicitly supplied public HTML/text source. Without `--model`, no
model-assisted deep analysis is claimed. `--model-factory module:callable` is an
alternative for a trusted, operator-specified client factory; never derive this
argument from a document. A partial review exits with code 2 and emits the partial
packet, including its unmet scope. Discovery failures are explicit errors.

`effect` records an operator-reported experiment separately:

```bash
PYTHONPATH=src python3 -m moltweave.research effect PACK_ID \
  --outcome inconclusive --experiment-id EXPERIMENT_ID \
  --metrics '{"description":"replace with actual measurements"}' \
  --evidence '{"receipt":"replace with an actual experiment receipt"}' --actor owner
```

These example commands are instructions, **not claims that an experiment ran**.
Effects remain `unverified_operator_report`; this module does not authenticate or
validate the independent experiment receipt. `--actor owner` is a local provenance
label, **not owner authentication or approval to deploy a mechanism**. The host
must enforce its actual approval and identity boundary. `adopt` only means admitted
for consideration/experiment; it is never interpreted as release permission.

## Python API

```python
from moltweave.research import ResearchStore, discover, review, record_feedback, search_feedback

store = ResearchStore(".moltweave/research")
receipt = discover('all:"recursive self-improvement"', store, max_results=10)
packet = review(receipt["changes"][0]["paper_id"], store, client=optional_model_client,
                full_text=True, actor="owner", context={"project": "agent-memory"})
# Record feedback only after a real operator decision.
# decision = record_feedback(store, packet["pack_id"], "defer", reason=human_reason,
#                            actor="owner", context={"project": "agent-memory"})
prior_decisions = search_feedback(store, "memory retrieval", actor="owner",
                                 context={"project": "agent-memory"})
```

The optional client needs `complete(messages, max_tokens=4096,
purpose='research_deep_review', metadata=None) -> dict`. By default no feedback
text, private operator context, or local traces are sent to that client. Model
input contains the public document and read scope; the packet links local
decisions by ID.

Python callers can explicitly pass `use_decision_context=True`, equivalent to the
CLI flag. This requires a model client, a nonempty actor and at least one nonempty
`project`, `tenant`, `environment` or `scope` filter. Up to five lexically similar,
actor-scoped, non-synthetic decisions are selected; all supplied isolation fields
must match. Their bounded reasons/context, decision IDs, source packet/version,
timestamps and provenance are sent as **untrusted historical preferences**.
The packet records selection, a content hash and whether data was provided to
`ModelClient`; the actual provider receipt is needed to confirm network completion.
The retained `private_feedback_sent_to_model` compatibility field means input was
provided to the client, not that a failed provider call necessarily completed.

This opt-in may disclose private decision reasons to the configured provider and
its local call logs. Inspect the chosen actor/context and provider before using
it. A model can tailor proposals to these preferences and cite decision IDs; it
must preserve source facts and cannot use preferences as a scientific label,
measured effect, authentication or release approval. No real human-judgment benefit
has been demonstrated. Local actor strings and filters are not server-side access
control; model instruction resistance alone is not a permission mechanism.

## Evidence and trust boundary

The document is untrusted data. A fixed system instruction asks the model for
architecture, experiment denominators/splits/baselines, limitations, proposed
changes, and exact evidence quotes. HTML scripts/styles/navigation are discarded;
there is no shell, code interpreter, repository runner, document-driven fetch, or
tool-call loop. Model output is only JSON data and remains pending review.

An exact quote match is recorded as `quote_found_in_read_scope`. It does **not**
prove that the quote supports the interpreted claim, that the authors are right,
or that the finding transfers. Facts extracted by the model stay `verified=false`;
semantic source checking and independent reproduction are separate work.

The HTTP boundary permits HTTPS port 443 only. Credentials in URLs, fragments,
control characters, local hostnames, non-global addresses, mixed public/private
DNS answers, and private redirect targets are blocked. The connection uses the
validated IP directly while preserving hostname SNI and certificate verification,
so a second DNS lookup cannot rebind it to a private address. Redirects, response
size, decompressed size and supported content types are bounded. Environment
proxy settings, cookies and user accounts are not used. XML DTD/entity declarations
and NUL-containing encodings are rejected before parsing.

These controls reduce document-instruction execution and SSRF exposure. They do
not make an LLM immune to semantic manipulation. A malicious document can still
produce misleading analysis, hence untrusted outputs, evidence checks, fixed
approval rules and external acceptance remain necessary.

## Deliberate gaps

- No automatic schedule is installed. Run `discover` from an explicitly configured
  scheduler later. No background task, account, email, or publication is created.
- No current popularity/trending score, OpenAlex connector, citation graph, full
  corpus synchronization, or automatic follow-up of links is implemented.
- HTML/text only. PDF extraction, OCR, visual table/figure reading, supplements,
  repository-code inspection, and experiment reproduction are not implemented.
  HTML truncation and failed full-text attempts are visible; neither counts as a
  complete paper reading. `full_text_read` means supplied arXiv HTML text was read
  within the cap, not every figure, equation or claim was checked. The reader
  requires an arXiv article marker and matching title before recording a complete
  HTML-text read; a successful HTTP response containing a browser challenge is
  recorded as a partial abstract-only packet.
- No authenticated multi-tenant server, cross-user learning, preference training,
  automatic P/source modification, candidate approval, or deployment. Local actor
  and strict context filters are retrieval boundaries, not server access control.
- A decision cannot establish scientific truth. A preference match cannot establish
  utility. An adoption event cannot establish model or business improvement.

## Tests and real evidence

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p test_research.py -v
```

Offline tests use synthetic feeds, synthetic model clients, and isolated temporary
stores. They exercise versions/deduplication, XML rejection, DNS pinning/private
redirect denial, scope, malicious document text, quote checks, actor/context
retrieval, and separation of facts/decisions/effects. Passing them does not prove
scientific quality or human-learning benefit. Public live discovery evidence, when
run, is stored separately under `examples/research/`; no private trace or fabricated
human feedback is used for that run.

On 2026-10-23, the implemented DNS-pinned fetcher performed two real HTTPS arXiv
API discoveries for `all:"recursive self-improvement"` (three results). The first
added three papers/explicit versions; the second added zero papers and zero
versions. The source hashes matched. The sanitized receipt is
[`examples/research/live-discovery-20261023.json`](../examples/research/live-discovery-20261023.json).
This validates discovery, persistence and deduplication against a public source;
it does not validate the papers' claims, model-assisted reading, human decision
learning, or RSI improvement. No model was called and no feedback was invented.

An additional real CLI run on the same date fetched Dream-RSI
[`2609.14858v2`](https://arxiv.org/html/2609.14858v2), extracted all 122,299 available
HTML-text characters within a 200,000-character cap, and called the configured
`deepseek-flash` model once. The completed call used 40,414 input and 2,696 output
tokens (`finish_reason=stop`). This was model-assisted reading, **not independent
validation of the generated analysis**. No historical decision context was sent,
no human feedback was invented, and repository inspection/experiment reproduction
remain unperformed. The public
[evidence projection](../examples/research/dream-rsi-v2-model-evidence.json) and
[redacted call receipt](../examples/research/dream-rsi-v2-model-call-receipt.json)
omit source full text, full response and request messages; their hashes link to
the local originals. The model returned more quote anchors than requested, so the
public projection retains only two short anchors; prompt compliance is not assumed.

Source references checked in the design research:

- [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html): versions,
  `published`/`updated`, query ordering and Atom metadata.
- [OpenAlex work attributes](https://help.openalex.org/data/works/attributes/):
  discovery metadata is distinct from source-version content and scientific quality.
- [PaperQA2 algorithm](https://github.com/Future-House/paper-qa#paperqa2-algorithm):
  candidate search, evidence gathering/ranking and cited answers are useful
  analysis components, not independent experiment verification.
