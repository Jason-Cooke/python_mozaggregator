import os
from datetime import datetime
import zlib
import json


def format_payload_bytes_decoded(ping):
    # fields are created in tests/dataset.py
    return {
        "normalized_app_name": ping["application"]["name"],
        "normalized_channel": ping["application"]["channel"],
        "normalized_os": ping["environment"]["system"]["os"]["name"],
        "sample_id": ping["meta"]["sampleId"],
        "submission_timestamp": int(
            datetime.strptime(ping["meta"]["submissionDate"], "%Y%m%d").strftime("%s")
        )
        * 10 ** 6,
        "payload": zlib.compress(json.dumps(ping)),
    }


def bigquery_testing_enabled():
    return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.environ.get(
        "PROJECT_ID"
    )
