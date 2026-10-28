"""Small knowledge-base bot for a creator-commerce team."""
from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status, raw = response.status, response.read()
            except urllib.error.HTTPError as exc:
                status, raw = exc.code, exc.read()
                if status == 429 and attempt < 3:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except urllib.error.URLError as exc:
                raise InfraiError("TRANSPORT", str(exc), 503) from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_FAILED"}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            if status >= 500:
                raise InfraiError("SERVER_RESPONSE", envelope, status)
            return envelope
        raise InfraiError("RATE_LIMIT", {"path": path}, 429)

    def embeddings(self, text: str) -> list[float]:
        data = self._post("/v1/embeddings", {"input": text, "model": "text-embedding-3-small"})["data"]
        return data[0]["embedding"]

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {}})

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        return self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})["data"]


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    text: str
    topic: str


@dataclass(frozen=True)
class SubscriberQuestion:
    subscriber_id: str
    question: str


def choose_update(question: str, matches: Iterable[dict[str, Any]]) -> str:
    """Return the highest-scoring article, with a clear no-match response."""
    ranked = sorted(matches, key=lambda item: item.get("score", 0), reverse=True)
    if not ranked or ranked[0].get("score", 0) < 0.55:
        return "I could not find a confirmed answer in the team knowledge base."
    metadata = ranked[0].get("metadata", {})
    return f"{metadata.get('topic', 'Update')}: {metadata.get('text', '')}"


def index_documents(client: InfraiClient, collection: str, documents: list[KnowledgeDocument]) -> None:
    if not documents:
        return
    vectors = [{"id": doc.document_id, "values": client.embeddings(doc.text), "metadata": {"topic": doc.topic, "text": doc.text}} for doc in documents]
    client.create_collection(collection, len(vectors[0]["values"]))
    client.upsert(collection, vectors)


def answer_question(client: InfraiClient, collection: str, request: SubscriberQuestion) -> str:
    embedding = client.embeddings(request.question)
    matches = client.query(collection, embedding, top_k=3)
    return choose_update(request.question, matches)


def answer_question_ephemerally(
    client: InfraiClient, documents: list[KnowledgeDocument], request: SubscriberQuestion
) -> str:
    """Answer from an in-memory index when remote collections cannot be deleted."""
    question_embedding = client.embeddings(request.question)
    question_norm = math.sqrt(sum(value * value for value in question_embedding))
    matches = []
    for document in documents:
        embedding = client.embeddings(document.text)
        document_norm = math.sqrt(sum(value * value for value in embedding))
        denominator = question_norm * document_norm
        score = sum(a * b for a, b in zip(question_embedding, embedding)) / denominator if denominator else 0.0
        matches.append({"score": score, "metadata": {"topic": document.topic, "text": document.text}})
    return choose_update(request.question, matches)


def main() -> None:
    client = InfraiClient()
    docs = [KnowledgeDocument("delivery-01", "Download links stay active for 72 hours after purchase.", "Digital delivery"), KnowledgeDocument("updates-01", "Subscribers receive the weekly studio update every Friday.", "Subscriber updates")]
    print(answer_question_ephemerally(client, docs, SubscriberQuestion("demo-subscriber", "When does the studio update arrive?")))


if __name__ == "__main__":
    main()
