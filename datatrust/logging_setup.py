"""
logging_setup.py — one shared way to print progress messages with time and level.

Imports / uses: Python's built-in logging module
Used by: datatrust/collector/*.py (and later every pipeline module)
"""

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


# Returns a logger that prints messages like "12:00:01 | INFO | collector | Fetched 1000".
# Inputs: name — a short label shown in every line, usually the module name.
# Returns: a logging.Logger object.
def get_logger(name):
    # basicConfig only takes effect the first time it is called, so calling it again is safe.
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%H:%M:%S")
    return logging.getLogger(name)
