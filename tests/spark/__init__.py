"""
tests/spark/__init__.py — marks the Spark tests folder as a package.
Tests in this folder need PySpark, so they only RUN inside the Docker "pipeline" container;
on Windows (no PySpark in .venv) they are automatically SKIPPED.

Imports / uses: nothing
Used by: pytest
"""
