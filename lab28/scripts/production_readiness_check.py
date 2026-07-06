import subprocess

import redis
import requests

results: dict[str, str] = {}


def check(name, function) -> None:
    try:
        function()
        results[name] = "PASS"
        print(f"  [PASS] {name}")
    except Exception as exc:
        results[name] = f"FAIL: {exc}"
        print(f"  [FAIL] {name}: {exc}")


def require_url(url: str) -> None:
    requests.get(url, timeout=10).raise_for_status()


def require_api_validation() -> None:
    response = requests.post("http://localhost:8000/api/v1/chat", json={}, timeout=10)
    if response.status_code != 422:
        raise RuntimeError(f"expected 422, received {response.status_code}")


def require_collection() -> None:
    response = requests.get("http://localhost:6333/collections/documents", timeout=10)
    response.raise_for_status()


def require_kafka_topic() -> None:
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "kafka", "kafka-topics",
            "--list", "--bootstrap-server", "localhost:9092",
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    if "data.raw" not in result.stdout.splitlines():
        raise RuntimeError("topic data.raw does not exist")


print("\n=== RELIABILITY ===")
check("Health endpoint", lambda: require_url("http://localhost:8000/health"))
check("API documentation", lambda: require_url("http://localhost:8000/docs"))

print("\n=== OBSERVABILITY ===")
check("Prometheus", lambda: require_url("http://localhost:9090/-/healthy"))
check("Grafana", lambda: require_url("http://localhost:3000/api/health"))
check("Metrics endpoint", lambda: require_url("http://localhost:8000/metrics"))

print("\n=== SECURITY AND VALIDATION ===")
check("Invalid request rejected", require_api_validation)

print("\n=== DATA SERVICES ===")
check("Qdrant", lambda: require_url("http://localhost:6333/healthz"))
check("Documents collection", require_collection)
check("Redis", lambda: redis.Redis(host="localhost", port=6379).ping())
check("Kafka topic", require_kafka_topic)

passed = sum(value == "PASS" for value in results.values())
total = len(results)
score = passed / total * 100
print("\n" + "=" * 48)
print(f"Production Readiness Score: {passed}/{total} = {score:.0f}%")
print(f"Target: >80% - Status: {'READY' if score > 80 else 'NOT READY'}")
