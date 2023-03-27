import pandas as pd
import requests
from sec import constants
import os


def _get_cik_lookup() -> pd.DataFrame:
    """
    Get a DataFrame of all tickers and their corresponding CIK numbers.

    Returns:
        pd.DataFrame: DataFrame of CIK numbers and tickers.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers=constants.HEADING)
    lookup = pd.DataFrame(r.json()).T
    lookup.set_index("ticker", inplace=True)
    return lookup


def _get_industry_lookup() -> pd.DataFrame:
    """
    Get a DataFrame of all tickers and their corresponding industries.

    Returns:
        pd.DataFrame: DataFrame of industries and tickers.
    """
    return pd.read_csv(
        os.path.join(constants.WACC_DATA_DIR, "industries.csv"), index_col=0
    )


def _get_sp500_lookup() -> pd.DataFrame:
    """
    Get a DataFrame of all tickers in the S&P 500 on certain dates.

    Returns:
        pd.DataFrame: DataFrame of tickers and dates.
    """
    lookup = pd.read_csv(
        os.path.join(constants.SP500_DATA_DIR, "sp500_historical.csv"), index_col=0
    )
    lookup["tickers"] = lookup["tickers"].apply(lambda x: sorted(x.split(",")))
    return lookup


_cik_lookup = _get_cik_lookup()
_industry_lookup = _get_industry_lookup()
_sp500_lookup = _get_sp500_lookup()


def get_cik(ticker) -> str:
    """
    Get the CIK number for a given ticker.

    Args:
        ticker (str): ticker to get CIK for.

    Returns:
        str: CIK number.
    """
    return str(_cik_lookup.loc[ticker, "cik_str"]).zfill(10)


def get_industry(ticker) -> str:
    """
    Get the industry of a given ticker for use with WACC data.

    Args:
        ticker (str): Ticker to get industry for.

    Returns:
        str: Industry of the ticker.
    """
    return _industry_lookup.loc[ticker, "industry"]


def get_sp500_tickers(query_date: str) -> list:
    """Get a list of tickers for all stocks in the S&P 500 on a given date.

    Args:
        query_date (str): Date in YYYY-MM-DD format. Defaults to None.

    Returns:
        list: List of tickers.
    """
    if query_date is None:
        return _sp500_lookup.iloc[-1]["tickers"]
    return _sp500_lookup[_sp500_lookup.index <= query_date].iloc[-1]["tickers"]
