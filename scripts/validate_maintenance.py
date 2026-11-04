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
    assert list(history.columns) == ["date", "tickers"]
    dates = pd.to_datetime(history.date, format="%Y-%m-%d")
    assert dates.is_unique and dates.is_monotonic_increasing
    for row in history.itertuples():
        tickers = row.tickers.split(",")
        assert all(tickers) and len(tickers) == len(set(tickers)), row.date
    mapping = pd.read_csv(
        Path(constants.WACC_DATA_DIR) / "industries.csv", keep_default_na=False
    )
    assert list(mapping.columns) == ["ticker", "industry"]
    assert mapping.ticker.is_unique and not mapping.isna().any().any()
    assert mapping.ne("").all().all()
    assert lookups.get_industry("NA") == "Semiconductor"
    members = lookups.get_sp500_tickers(query_date=args.date)
    for ticker in members:
        try:
            lookups.get_cik(ticker)
        except KeyError as error:
            raise SystemExit(f"Missing SEC issuer mapping for {ticker}") from error
    failures = []
    for year in ("2025", "2026"):
        table = pd.read_csv(Path(constants.WACC_DATA_DIR) / f"{year}.csv")
        assert table["Industry Name"].is_unique
        assert table["Cost of Capital"].between(0, 1).all()
        for ticker in members:
            try:
                stock = Stock.__new__(Stock)
                stock.ticker = ticker
                stock.industry = lookups.get_industry(ticker)
                value = stock.get_wacc(query_date=f"{year}-12-31")
                assert math.isfinite(value) and 0 < value < 1
            except Exception as error:
                failures.append(f"{year} {ticker}: {error}")
    assert not failures, "\n".join(failures)
    missing = []
    for ticker in members:
        if not (Path(constants.PROCESSED_DATA_DIR) / f"{ticker}.csv").exists():
            missing.append(ticker)
            continue
        value = Stock(ticker).get_wacc(query_date=args.date)
        assert math.isfinite(value) and 0 < value < 1, ticker
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
