"""Create the raw-store bucket if it does not exist (development and CI only)."""

from __future__ import annotations

import sys
import time

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from soccer_analyst.core.config import load_raw_store_settings
from soccer_analyst.core.errors import ConfigError

ATTEMPTS = 30


def main() -> None:
    try:
        settings = load_raw_store_settings()
    except ConfigError as exc:
        sys.exit(str(exc))
    client = boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        region_name=settings.region,
        aws_access_key_id=settings.access_key_id.get_secret_value(),
        aws_secret_access_key=settings.secret_access_key.get_secret_value(),
    )
    bucket = settings.bucket
    # SeaweedFS has no healthcheck in docker-compose.yml: retry while it starts.
    for attempt in range(ATTEMPTS):
        try:
            client.head_bucket(Bucket=bucket)
            print(f"bucket {bucket}: esiste")
            return
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchBucket", "NotFound"}:
                client.create_bucket(Bucket=bucket)
                print(f"bucket {bucket}: creato")
                return
            if attempt == ATTEMPTS - 1:
                raise
        except EndpointConnectionError:
            if attempt == ATTEMPTS - 1:
                raise
        time.sleep(2)


if __name__ == "__main__":
    main()
