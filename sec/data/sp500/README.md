The steps below should be completed monthly.

### S&P500 data source
link: https://github.com/fja05680/sp500

From this repository, download `S&P 500 Historical Components & Changes (Updated).csv` (the upstream name previously included a date). Name this file sp500_historical.csv and replace the file currently stored in this directory. Preserve the full history and the `date,tickers` schema. Dates must be unique and ascending, with comma-separated tickers inside the quoted `tickers` field.

### Date of last data update
2026-11-04. Downloaded the latest upstream file, containing 2,720 snapshots through **2026-08-18**, with 503 securities in the final snapshot. This is the source's coverage date, not a claim of independently verified November membership.

Source: https://github.com/fja05680/sp500/blob/master/S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv

Downloaded file SHA-256: `36326709d46d6cd25834de5df457b16f5f96fad3a06b9beac28f7b88aa0b0d54`.
