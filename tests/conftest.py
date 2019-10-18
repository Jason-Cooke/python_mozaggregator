import os

import pandas as pd
from google.cloud import bigquery
from pyspark.sql import SparkSession

import pytest
from dataset import generate_pings
from utils import bigquery_testing_enabled, format_payload_bytes_decoded


@pytest.fixture()
def spark():
    spark = SparkSession.builder.getOrCreate()
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    yield spark
    spark.stop()


@pytest.fixture()
def sc(spark):
    return spark.sparkContext


@pytest.mark.skipif(
    not bigquery_testing_enabled(),
    reason="requires valid gcp credentials and project id",
)
@pytest.fixture
def bq_testing_table():
    bq_client = bigquery.Client()

    project_id = os.environ["PROJECT_ID"]
    dataset_id = "{project_id}.pytest_mozaggregator_test".format(project_id=project_id)
    bq_client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
    bq_client.create_dataset(dataset_id)

    schema = bq_client.schema_from_json(
        os.path.join(os.path.dirname(__file__), "decoded.1.bq")
    )
    # create the main and saved-session tables
    main_table_id = "{dataset_id}.telemetry_telemetry__main_v4".format(
        dataset_id=dataset_id
    )
    main_table = bq_client.create_table(bigquery.table.Table(main_table_id, schema))
    saved_session_table_id = "{dataset_id}.telemetry_telemetry__saved_session_v4".format(
        dataset_id=dataset_id
    )
    saved_session_table = bq_client.create_table(
        bigquery.table.Table(saved_session_table_id, schema)
    )

    # use load_table instead of insert_rows to avoid eventual consistency guarantees
    df = pd.DataFrame([format_payload_bytes_decoded(ping) for ping in generate_pings()])

    bq_client.load_table_from_dataframe(df, main_table).result()
    bq_client.load_table_from_dataframe(df, saved_session_table).result()

    yield

    bq_client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
