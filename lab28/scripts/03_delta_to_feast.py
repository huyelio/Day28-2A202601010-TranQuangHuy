import glob
import json
import os

import pandas as pd
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
DELTA_GLOB = os.getenv("DELTA_GLOB", "delta-lake/raw/*.parquet")


def materialize_features() -> int:
    files = glob.glob(DELTA_GLOB)
    if not files:
        print(f"No Parquet files found at {DELTA_GLOB}")
        return 0

    frame = pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)
    frame = frame.drop_duplicates(subset=["id"], keep="last")
    client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    client.ping()

    with client.pipeline() as pipeline:
        for row in frame.to_dict(orient="records"):
            pipeline.set(
                f"feature:{row['id']}",
                json.dumps(
                    {
                        "text": row["text"],
                        "timestamp": row.get("timestamp"),
                        "processed": True,
                    }
                ),
            )
        pipeline.execute()

    print(f"Integration 3+4 OK: stored {len(frame)} features in Redis")
    return len(frame)


if __name__ == "__main__":
    materialize_features()
