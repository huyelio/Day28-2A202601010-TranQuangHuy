import json
import os
import time

from kafka import KafkaProducer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


def ingest_data(records: list[dict]) -> None:
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    try:
        for record in records:
            producer.send("data.raw", value=record).get(timeout=10)
            print(f"Sent: {record['id']}")
        producer.flush()
    finally:
        producer.close()


if __name__ == "__main__":
    now = time.time()
    ingest_data(
        [
            {"id": "doc_001", "text": "AI platform integration test", "timestamp": now},
            {"id": "doc_002", "text": "Kafka to Prefect pipeline", "timestamp": now},
        ]
    )
    print("Integration 1 OK: Data -> Kafka")
