"""Create the raw-store bucket if it does not exist (development and CI only)."""

from __future__ import annotations

import os
import sys
import time

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"Variabile mancante: {name}")
    return value


def main() -> None:
    client = boto3.client(
        "s3",
        endpoint_url=env("SAP_RAW_ENDPOINT_URL"),
        region_name=os.environ.get("SAP_RAW_REGION", "auto"),
        aws_access_key_id=env("SAP_RAW_ACCESS_KEY_ID"),
        aws_secret_access_key=env("SAP_RAW_SECRET_ACCESS_KEY"),
    )
    bucket = env("SAP_RAW_BUCKET")
    for attempt in range(30):
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
            if attempt == 29:
                raise
        except EndpointConnectionError:
            if attempt == 29:
                raise
        time.sleep(2)


if __name__ == "__main__":
    main()
