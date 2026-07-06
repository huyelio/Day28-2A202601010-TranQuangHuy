# Lab 28 Platform

## Start

```bash
# Edit .env with the Kaggle tunnel URLs.
python -m pip install -r requirements.txt
docker compose up -d --build
docker compose exec kafka kafka-topics --create --if-not-exists \
  --topic data.raw --bootstrap-server localhost:9092 \
  --partitions 1 --replication-factor 1
```

## Run the pipeline

```bash
python scripts/01_ingest_to_kafka.py
python prefect/flows/kafka_to_delta.py
python scripts/03_delta_to_feast.py
set -a && source .env && set +a
python scripts/05_embed_to_qdrant.py
```

## Verify

```bash
pytest smoke-tests/ -v
python scripts/production_readiness_check.py
```

Services: API `:8000`, Prometheus `:9090`, Grafana `:3000`, Prefect `:4200`,
Qdrant `:6333`, Kafka `:9092`, and Redis `:6379`.
