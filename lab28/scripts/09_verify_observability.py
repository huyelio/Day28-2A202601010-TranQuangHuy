import os

import requests


def check_prometheus() -> None:
    response = requests.get(
        "http://localhost:9090/api/v1/query",
        params={"query": 'up{job="api-gateway"}'},
        timeout=10,
    )
    response.raise_for_status()
    result = response.json()["data"]["result"]
    if not result or result[0]["value"][1] != "1":
        raise RuntimeError("Prometheus is not scraping api-gateway")
    print("Integration 9 OK: Prometheus metrics are flowing")


def check_langsmith() -> None:
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("Integration 10 SKIP: LANGCHAIN_API_KEY is not configured")
        return

    from langsmith import Client

    project = os.getenv("LANGCHAIN_PROJECT", "lab28-platform")
    runs = list(Client(api_key=api_key).list_runs(project_name=project, limit=1))
    if not runs:
        raise RuntimeError(f"No LangSmith runs found in project {project}")
    print("Integration 10 OK: LangSmith trace found")


if __name__ == "__main__":
    check_prometheus()
    check_langsmith()
