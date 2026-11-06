"""Validate packaged maintenance data without downloading SEC financials.

Run after installing this checkout: python scripts/validate_maintenance.py
The WACC-only check deliberately bypasses Stock.__init__, which loads unrelated
SEC financials. A separate constructor check reports missing financial files.
"""

import argparse
import math
from pathlib import Path

import pandas as pd

from sec import constants, lookups
from sec.stock import Stock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="2026-11-04")
    args = parser.parse_args()
    history = pd.read_csv(Path(constants.SP500_DATA_DIR) / "sp500_historical.csv")
    if list(history.columns) != ["date", "tickers"]:
        raise SystemExit("S&P 500 history must have date and tickers columns")
    dates = pd.to_datetime(history.date, format="%Y-%m-%d")
    if not dates.is_unique or not dates.is_monotonic_increasing:
        raise SystemExit("S&P 500 snapshot dates must be unique and ascending")
    for row in history.itertuples():
        tickers = row.tickers.split(",")
        if not all(tickers) or len(tickers) != len(set(tickers)):
            raise SystemExit(f"Empty or duplicate ticker in snapshot {row.date}")
    mapping = pd.read_csv(
        Path(constants.WACC_DATA_DIR) / "industries.csv", keep_default_na=False
    )
    if list(mapping.columns) != ["ticker", "industry"]:
        raise SystemExit("Industry mapping must have ticker and industry columns")
    if (
        not mapping.ticker.is_unique
        or mapping.isna().any().any()
        or mapping.eq("").any().any()
    ):
        raise SystemExit("Industry mapping contains duplicate tickers or empty values")
    if lookups.get_industry("NA") != "Semiconductor":
        raise SystemExit("Expected NA to resolve to Semiconductor")
    members = lookups.get_sp500_tickers(query_date=args.date)
    for ticker in members:
        try:
            lookups.get_cik(ticker)
        except KeyError as error:
            raise SystemExit(f"Missing SEC issuer mapping for {ticker}") from error
    failures = []
    for year in ("2025", "2026"):
        table = pd.read_csv(Path(constants.WACC_DATA_DIR) / f"{year}.csv")
        if not table["Industry Name"].is_unique:
            raise SystemExit(f"{year} WACC table contains duplicate industries")
        if not table["Cost of Capital"].between(0, 1).all():
            raise SystemExit(f"{year} WACC table contains invalid decimal rates")
        for ticker in members:
            try:
                stock = Stock.__new__(Stock)
                stock.ticker = ticker
                stock.industry = lookups.get_industry(ticker)
                value = stock.get_wacc(query_date=f"{year}-12-31")
                if not (math.isfinite(value) and 0 < value < 1):
                    raise ValueError(f"invalid WACC rate {value!r}")
            except Exception as error:
                failures.append(f"{year} {ticker}: {error}")
    if failures:
        raise SystemExit("WACC validation failed:\n" + "\n".join(failures))
    missing = []
    for ticker in members:
        if not (Path(constants.PROCESSED_DATA_DIR) / f"{ticker}.csv").exists():
            missing.append(ticker)
            continue
        value = Stock(ticker).get_wacc(query_date=args.date)
        if not (math.isfinite(value) and 0 < value < 1):
            raise SystemExit(f"{ticker}: invalid WACC rate {value!r}")
    print(f"WACC passed: {len(members)} tickers in each of 2025 and 2026.")
    print(
        f"History: {len(history)} snapshots, {history.date.iloc[0]} through {history.date.iloc[-1]}."
    )
    print(f"Industry mapping: {len(mapping)} unique tickers.")
    print(f"Stock constructor and WACC passed: {len(members) - len(missing)} tickers.")
    print(
        f'Separate SEC financial-data refresh needed for {len(missing)} tickers: {", ".join(missing)}'
    )


if __name__ == "__main__":
    main()
