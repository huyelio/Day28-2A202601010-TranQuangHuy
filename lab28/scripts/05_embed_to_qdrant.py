import os
import uuid

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

EMBED_URL = os.getenv("EMBED_NGROK_URL", "").rstrip("/")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
COLLECTION = "documents"


def stable_point_id(document_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"lab28:{document_id}"))


def embed_and_store(records: list[dict]) -> int:
    if not EMBED_URL:
        raise RuntimeError("Set EMBED_NGROK_URL before running this script")

    response = requests.post(
        f"{EMBED_URL}/embed",
        json={"texts": [record["text"] for record in records]},
        timeout=60,
    )
    response.raise_for_status()
    embeddings = response.json()["embeddings"]
    if len(embeddings) != len(records) or any(len(vector) != 384 for vector in embeddings):
        raise ValueError("Embedding service must return one 384-dimensional vector per record")

    qdrant = QdrantClient(host=QDRANT_HOST, port=6333)
    if not qdrant.collection_exists(COLLECTION):
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    points = [
        PointStruct(id=stable_point_id(record["id"]), vector=vector, payload=record)
        for record, vector in zip(records, embeddings)
    ]
    qdrant.upsert(collection_name=COLLECTION, points=points, wait=True)
    print(f"Integration 5 OK: stored {len(points)} vectors in Qdrant")
    return len(points)


if __name__ == "__main__":
    embed_and_store(
        [
            {"id": "doc_001", "text": "AI platform integration test"},
            {"id": "doc_002", "text": "Kafka to Prefect pipeline"},
        ]
    )
