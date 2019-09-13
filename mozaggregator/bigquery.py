import json
from datetime import datetime, timedelta

from pyspark.sql import Row, SparkSession


class BigQueryDataset:
    def __init__(self):
        self.spark = SparkSession.builder.getOrCreate()

    @staticmethod
    def _date_add(date_ds, days):
        dt = datetime.strptime(date_ds, "%Y%m%d")
        return datetime.strftime(dt + timedelta(days), "%Y-%m-%d")

    @staticmethod
    def _extract_payload(row):
        """
        The schema for the `payload_bytes_decoded` table is listed for reference.

            root
            |-- client_id: string (nullable = true)
            |-- document_id: string (nullable = true)
            |-- metadata: struct (nullable = true)
            |    |-- document_namespace: string (nullable = true)
            |    |-- document_type: string (nullable = true)
            |    |-- document_version: string (nullable = true)
            |    |-- geo: struct (nullable = true)
            |    |    |-- city: string (nullable = true)
            |    |    |-- country: string (nullable = true)
            |    |    |-- db_version: string (nullable = true)
            |    |    |-- subdivision1: string (nullable = true)
            |    |    |-- subdivision2: string (nullable = true)
            |    |-- header: struct (nullable = true)
            |    |    |-- date: string (nullable = true)
            |    |    |-- dnt: string (nullable = true)
            |    |    |-- x_debug_id: string (nullable = true)
            |    |    |-- x_pingsender_version: string (nullable = true)
            |    |-- uri: struct (nullable = true)
            |    |    |-- app_build_id: string (nullable = true)
            |    |    |-- app_name: string (nullable = true)
            |    |    |-- app_update_channel: string (nullable = true)
            |    |    |-- app_version: string (nullable = true)
            |    |-- user_agent: struct (nullable = true)
            |    |    |-- browser: string (nullable = true)
            |    |    |-- os: string (nullable = true)
            |    |    |-- version: string (nullable = true)
            |-- normalized_app_name: string (nullable = true)
            |-- normalized_channel: string (nullable = true)
            |-- normalized_country_code: string (nullable = true)
            |-- normalized_os: string (nullable = true)
            |-- normalized_os_version: string (nullable = true)
            |-- payload: binary (nullable = true)
            |-- sample_id: long (nullable = true)
            |-- submission_timestamp: timestamp (nullable = true)
        """
        data = json.loads(gzip.decompress(row.payload).decode("utf-8"))
        # add `meta` fields for backwards compatibility
        data["meta"] = {
            "submissionDate": datetime.strftime(row.submission_timestamp, "%Y%m%d"),
            "sampleId": row.sample_id,
        }
        return data

    def load(self, project_id, doc_type, submission_date, channels=None, filter_clause=None, fraction=1):

        start = self._date_add(submission_date, 0)
        end = self._date_add(submission_date, 1)

        date_clause = "submission_timestamp >= '{start}' AND submission_timestamp < '{end}'".format(
            start=start, end=end
        )

        filters = [date_clause]
        if channels:
            # build up a clause like "(normalized_channel = 'nightly' OR normalized_channel = 'beta')"
            clauses = ["normalized_channel = '{}'".format(channel) for channel in channels]
            joined = "({})".format(" OR ".join(clauses))
            filters.append(filters)
        if filter_clause:
            filters.append(filters)

        df = (
            self.spark.read.format("bigquery")
            # Assumes the namespace is telemetry and the version is v4
            .option(
                "table",
                "{project_id}.payload_bytes_decoded.telemetry_telemetry__{doc_type}_v4".format(
                    project_id=project_id, doc_type=doc_type
                ),
            )
            .option("filter", " AND ".join(filters))
            .load()
        )

        # Size of the RDD sample is not deterministic
        return df.rdd.map(self._extract_payload).sample(False, fraction)


if __name__ == "__main__":
    # export GOOGLE_APPLICATION_CREDENTIALS=...
    # gsutil gsutil cp gs://spark-lib/bigquery/spark-bigquery-latest.jar .
    # export SPARK_CLASSPATH=$(pwd)/spark-bigquery-latest.jar

    rdd = BigQueryDataset.load(
        project_id="moz-fx-data-shar-nonprod-efed",
        doc_type="main",
        submission_date="2019-08-22",
        filter_clause="normalized_app_name <> Fennec AND channel IN ('nightly', 'beta')",
    )
    rdd.count()
    print(json.dumps(rdd.first()))
