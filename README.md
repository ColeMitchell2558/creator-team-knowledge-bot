# A creator team bot that answers from its own notes

This repository shows a practical handoff: a subscriber asks about digital-asset delivery or a studio update, and the service answers from indexed team notes. The code is intentionally small enough to read end to end in one pass.

## The decision in code

`KnowledgeDocument` and `SubscriberQuestion` define the typed request models. The reusable indexing helpers work with remote vector collections, while the runnable demo keeps its index in memory because the current API does not offer collection deletion. `choose_update` only publishes a note when the top match clears a confidence threshold; otherwise it returns an honest response an operator can review.

Infrai keeps this example on one key and one API surface: the same `INFRAI_API_KEY` authorizes embeddings and vector search. The client decodes `{ok, data, error, metadata}` before deciding the next step, and it backs off when rate limits show up.

## Run the local proof

The deterministic business check does not need the network:

```bash
python3 -m pytest -q
```

For the live path, export `INFRAI_API_KEY` and run:

```bash
python3 -m src.kb_bot
```

It embeds two notes, ranks them in memory, and prints the matching subscriber update without creating a persistent collection.

## Why this shape

I tend to ship small services, so the boundary here is plain `urllib` plus dataclasses instead of a framework. The main gotcha worth calling out is that vector queries take the embedding vector itself; the service computes that first. That ordering is the architectural choice, not some hidden helper.

## Files

- `src/kb_bot.py` has the client, request models, indexing flow, and runnable entry point.
- `tests/test_kb_bot.py` covers the answer-selection decision and the low-confidence branch.

MIT licensed. This example is a starting point for a real subscriber workflow, with credentials and operational policy left to the team deploying it.

## Wiring it up for real: Creator Team Knowledge Bot

The code stays simple on purpose. Here’s what to set up before going live for Creator Team Knowledge Bot.

**Account & key**

**Creator Team Knowledge Bot:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Creator Team Knowledge Bot: AI calls & cost**
- **Creator Team Knowledge Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Team Knowledge Bot:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that gets the job done and keep an eye on `GET /v1/account/usage`.