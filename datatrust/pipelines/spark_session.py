"""
spark_session.py — creates the Spark "session", the entry point to everything in Spark.
Every pipeline job calls create_spark() once at the start and spark.stop() at the end.

Imports / uses: pyspark
Used by: datatrust/pipelines/inspect_raw.py (and later every Spark job + Spark tests)
"""

from pyspark.sql import SparkSession


# Starts Spark in "local mode": one computer, using all of its CPU cores.
# Inputs: app_name — a label for this job (shows up in Spark's logs).
# Returns: a SparkSession object.
def create_spark(app_name="datatrust"):
    spark = (
        SparkSession.builder.appName(app_name)
        # local[*] = run on this machine, one worker thread per CPU core.
        .master("local[*]")
        # Memory for Spark's main process. Our data is small (MBs), 2 GB is plenty.
        .config("spark.driver.memory", "2g")
        # When Spark groups or joins data it splits work into "partitions" (chunks).
        # The default (200) is made for big clusters; for our size, 8 is much faster.
        .config("spark.sql.shuffle.partitions", "8")
        # Treat all times as UTC so dates never shift by time zone.
        .config("spark.sql.session.timeZone", "UTC")
        # Spark's web dashboard isn't reachable from Docker anyway, so turn it off.
        .config("spark.ui.enabled", "false")
        # Hide the "[Stage 0: ====>]" progress bars, which clutter our printed results.
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    # Hide Spark's very chatty INFO messages; show only warnings and errors.
    spark.sparkContext.setLogLevel("WARN")
    return spark
