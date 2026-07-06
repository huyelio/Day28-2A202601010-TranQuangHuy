import os
import subprocess

import redis
import requests

BASE_URL = "http://localhost:8000"


def test_health_check():
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_chat_request_is_rejected():
    response = requests.post(f"{BASE_URL}/api/v1/chat", json={}, timeout=5)
    assert response.status_code == 422


def test_kafka_topic_exists():
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "kafka", "kafka-topics",
            "--list", "--bootstrap-server", "localhost:9092",
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    assert "data.raw" in result.stdout.splitlines()


def test_prometheus_scrapes_api_gateway():
    response = requests.get(
        "http://localhost:9090/api/v1/query",
        params={"query": 'up{job="api-gateway"}'},
        timeout=10,
    )
    response.raise_for_status()
    result = response.json()["data"]["result"]
    assert result
    assert result[0]["value"][1] == "1"


def test_grafana_is_accessible():
    response = requests.get("http://localhost:3000/api/health", timeout=5)
    assert response.status_code == 200


def test_feature_store_has_features():
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    assert client.keys("feature:*")


def test_qdrant_has_documents():
    response = requests.get("http://localhost:6333/collections/documents", timeout=5)
    response.raise_for_status()
    assert response.json()["result"]["points_count"] > 0


def test_full_inference_when_configured():
    if not os.getenv("VLLM_NGROK_URL"):
        import pytest

        pytest.skip("VLLM_NGROK_URL is not configured")
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"query": "What is platform engineering?", "embedding": [0.1] * 384},
        timeout=90,
    )
    response.raise_for_status()
    assert len(response.json()["answer"]) > 10
