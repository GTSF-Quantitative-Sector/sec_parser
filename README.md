# sec_parser
An engine to parse data from the SEC's EDGAR database. Includes a few helpful functions to also grab data from Polygon.io.

## Installation
```
pip install git+https://github.com/GTSF-Quantitative-Sector/sec_parser.git
```

## Example Usage
```
from sec import stock, processor

aapl = stock.Stock("AAPL")

# get ebit from most recent annual filing
aapl.get_ebit()

# get accounts payable from most recent filing, including quarterly filings
aapl.get_accounts_payable(quarterly=True)

# get earnings per share from most recent filing before 2019-01-01, including quarterly filings
aapl.get_earnings_per_share(query_date="2019-01-01", quarterly=True)

# get price on 2013-08-11
await aapl.get_price(query_date="2013-08-11")

# download most recent SEC data
processor.download_sec_data()

# format SEC data for AAPL. required for data retrieval functions in stock.Stock
processor.process_sec_json("AAPL")
```