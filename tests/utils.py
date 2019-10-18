import json
import os
import zlib
from datetime import datetime


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


def runif_bigquery_testing_enabled(func):
    """A decorator that will skip the test if the current environment is not set up for running tests.

        @runif_bigquery_testing_enabled
        def test_my_function_that_uses_bigquery_spark_connector(table_fixture):
            ...
    """
    # importing this at module scope will break test discoverability
    import pytest

    bigquery_testing_enabled = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    ) and os.environ.get("PROJECT_ID")
    return pytest.mark.skipif(
        not bigquery_testing_enabled,
        reason="requires valid gcp credentials and project id",
    )(func)
