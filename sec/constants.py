import os

# data directories
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DOWNLOADED_DATA_DIR = os.path.join(DATA_DIR, "downloaded")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
WACC_DATA_DIR = os.path.join(DATA_DIR, "wacc")
SP500_DATA_DIR = os.path.join(DATA_DIR, "sp500")
CIK_DATA_DIR = os.path.join(DATA_DIR, "cik")

# requests headers
HEADING = {"User-Agent": "locke@gatech.edu"}

# Polygon.io API key
POLYGON_KEY = None


def set_polygon_key(key: str) -> None:
    """
    Set the Polygon.io API key.

    Args:
        key (str): Polygon.io API key.
    """
    global POLYGON_KEY
    POLYGON_KEY = key
