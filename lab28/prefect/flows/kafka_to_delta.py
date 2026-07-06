import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from kafka import KafkaConsumer
from prefect import flow, task

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DELTA_PATH = Path(os.getenv("DELTA_PATH", "delta-lake/raw"))


@task(retries=2, retry_delay_seconds=5)
def consume_records() -> list[dict]:
    consumer = KafkaConsumer(
        "data.raw",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=5000,
        group_id="lab28-delta-writer",
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
    )
    try:
        records = [message.value for message in consumer]
        if records:
            consumer.commit()
        return records
    finally:
        consumer.close()


@task
def write_parquet(records: list[dict]) -> str | None:
    if not records:
        print("No new Kafka records")
        return None

    DELTA_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    output = DELTA_PATH / f"batch_{timestamp}.parquet"
    pd.DataFrame(records).to_parquet(output, index=False)
    print(f"Wrote {len(records)} records to {output}")
    return str(output)


@flow(name="Kafka to Delta Pipeline", log_prints=True)
def kafka_to_delta_flow() -> str | None:
    return write_parquet(consume_records())


if __name__ == "__main__":
    kafka_to_delta_flow()
