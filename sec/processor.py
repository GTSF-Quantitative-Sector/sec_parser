import os
import zipfile

import orjson
import pandas as pd
import requests

from sec import constants, lookups

os.makedirs(constants.DATA_DIR, exist_ok=True)
os.makedirs(constants.DOWNLOADED_DATA_DIR, exist_ok=True)
os.makedirs(constants.PROCESSED_DATA_DIR, exist_ok=True)


def download_sec_data(force_update: bool = False, max_stale_days: int = 30) -> None:
    """
    Download all company facts from SEC.

    Args:
        force_update (bool, optional): If True, download SEC bulk data regardless of whether it already exists/ if it is stale. Defaults to False. (kept for backwards compatibility)
        max_stale_days (int, optional): Maximum number of days to keep SEC bulk data before updating. Defaults to 30. Can be overwritten by force_update.
    """

    # force download if previous zip is stale or zip does not exist
    if os.path.exists(os.path.join(constants.DOWNLOADED_DATA_DIR, "last_update.txt")):
        with open(os.path.join(constants.DOWNLOADED_DATA_DIR, "last_update.txt")) as f:
            last_update = pd.to_datetime(f.read())
        if (pd.Timestamp.now() - last_update).days > max_stale_days:
            force_update = True
    else:
        force_update = True

    # download and unzip companyfacts.zip, then save last_update.txt
    if force_update:
        print("Downloading companyfacts.zip...")
        url = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
        r = requests.get(url, headers=constants.HEADING)
        with open(
            os.path.join(constants.DOWNLOADED_DATA_DIR, "companyfacts.zip"), "wb"
        ) as f:
            f.write(r.content)
        print("Unzipping companyfacts.zip...")
        with zipfile.ZipFile(
            os.path.join(constants.DOWNLOADED_DATA_DIR, "companyfacts.zip"), "r"
        ) as zip_ref:
            zip_ref.extractall(constants.DOWNLOADED_DATA_DIR)
        with open(os.path.join(constants.DOWNLOADED_DATA_DIR, "last_update.txt"), "w") as f:
            f.write(pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
    else:
        print("Data not stale. Skipping download. To override, set force_update=True or change max_stale_days.")


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
