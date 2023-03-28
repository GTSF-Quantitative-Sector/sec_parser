import os

# data directories
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DOWNLOADED_DATA_DIR = os.path.join(DATA_DIR, "downloaded")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
WACC_DATA_DIR = os.path.join(DATA_DIR, "wacc")
SP500_DATA_DIR = os.path.join(DATA_DIR, "sp500")

# requests headers
HEADING = {"User-Agent": "locke@gatech.edu"}
