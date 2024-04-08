import os
import zipfile

import orjson
import pandas as pd
import requests

from sec import constants, lookups

os.makedirs(constants.DATA_DIR, exist_ok=True)
os.makedirs(constants.DOWNLOADED_DATA_DIR, exist_ok=True)
os.makedirs(constants.PROCESSED_DATA_DIR, exist_ok=True)


def download_sec_data(force_update: bool = True) -> None:
    """
    Download all company facts from SEC.

    Args:
        force_update (bool, optional): If True, download SEC bulk data regardless of whether it already exists. Defaults to True.
    """
    # if data/companyfacts.zip does not exist, download it
    if force_update or not os.path.exists(
        os.path.join(constants.DOWNLOADED_DATA_DIR, "companyfacts.zip")
    ):
        print("Downloading companyfacts.zip...")
        url = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
        r = requests.get(url, headers=constants.HEADING)
        with open(
            os.path.join(constants.DOWNLOADED_DATA_DIR, "companyfacts.zip"), "wb"
        ) as f:
            f.write(r.content)
    # if JSON files do not exist, unzip them
    if force_update or not os.path.exists(
        os.path.join(constants.DOWNLOADED_DATA_DIR, "CIK000032019.json")
    ):
        print("Unzipping companyfacts.zip...")
        with zipfile.ZipFile(
            os.path.join(constants.DOWNLOADED_DATA_DIR, "companyfacts.zip"), "r"
        ) as zip_ref:
            zip_ref.extractall(constants.DOWNLOADED_DATA_DIR)


def process_sec_json(ticker: str) -> None:
    """
    Process SEC JSON file for a given ticker.

    Args:
        ticker (str): ticker to process data for.
    """

    # find SEC data for ticker
    cik = lookups.get_cik(ticker)
    try:
        with open(os.path.join(constants.DOWNLOADED_DATA_DIR, f"CIK{cik}.json")) as f:
            sec_data = orjson.loads(f.read())
    except FileNotFoundError:
        raise FileNotFoundError(
            f"SEC data for {ticker} not found. Please download SEC data first [download_sec_data()]."
        )

    # process SEC data
    data = {"annual": {}}
    for item in sec_data["facts"]["dei"]:
        for unit in sec_data["facts"]["dei"][item]["units"]:
            for entry in sec_data["facts"]["dei"][item]["units"][unit]:
                filing_date = entry["filed"]
                if f"{item}_{unit}" not in data:
                    data[f"{item}_{unit}"] = {}
                data[f"{item}_{unit}"][filing_date] = entry["val"]
                data["annual"][filing_date] = True if entry["fp"] == "FY" else False
    for item in sec_data["facts"]["us-gaap"]:
        for unit in sec_data["facts"]["us-gaap"][item]["units"]:
            for entry in sec_data["facts"]["us-gaap"][item]["units"][unit]:
                filing_date = entry["filed"]
                if f"{item}_{unit}" not in data:
                    data[f"{item}_{unit}"] = {}
                data[f"{item}_{unit}"][filing_date] = entry["val"]
                data["annual"][filing_date] = True if entry["fp"] == "FY" else False
    df = pd.DataFrame(data)

    # save processed data
    df.index.name = "filing_date"
    df = df.sort_index()
    df.to_csv(os.path.join(constants.PROCESSED_DATA_DIR, f"{ticker}.csv"))
