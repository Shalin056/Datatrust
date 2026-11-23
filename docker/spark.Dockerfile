# spark.Dockerfile — recipe for a Linux "box" that has Python + Java + PySpark installed.
# Why: Spark is written in Java/Scala and expects Linux. Running it inside Docker means
# it works the same on your Windows laptop, in GitHub Actions, and on any other computer.
#
# Uses: requirements.txt, requirements-pipeline.txt, requirements-dev.txt
# Used by: docker-compose.yml (the "pipeline" service)

# Start from a small official Python 3.12 image based on Debian Linux ("bookworm").
FROM python:3.12-slim-bookworm

# Install Java 17, which Spark 4 needs. "--no-install-recommends" skips extras we don't
# need, and deleting the apt lists afterwards keeps the image smaller.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*

# Tell Spark where Java lives.
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
# Print Python output immediately (no buffering), so logs show up live.
ENV PYTHONUNBUFFERED=1

# All project files will live in /app inside the container.
WORKDIR /app

# Copy ONLY the requirements files first, then install. Docker caches each step,
# so this slow install is skipped on rebuilds unless the requirements change.
COPY requirements.txt requirements-pipeline.txt ./
RUN pip install --no-cache-dir -r requirements-pipeline.txt

# Testing tools (pytest, ruff), so the Spark tests can run inside this container.
# A separate step AFTER the PySpark install: changing dev tools never re-downloads PySpark.
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# The rest of the code is NOT copied in. docker-compose "mounts" your project folder
# into /app instead, so code edits on Windows are seen instantly without rebuilding.
