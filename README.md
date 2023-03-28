# sec_parser
An engine to parse data from the SEC's EDGAR database. Includes a few helpful functions to also grab data from Polygon.io.

## Installation
```
pip install git+https://github.com/GTSF-Quantitative-Sector/sec_parser.git
```

## Example Usage

Get financials, price, RSI, and WACC data for a stock.
```python
from sec import stock, constants

aapl = stock.Stock("AAPL")

# get ebit from most recent annual filing
aapl.get_ebit()

# get accounts payable from most recent filing, including quarterly filings
aapl.get_accounts_payable(quarterly=True)

# get earnings per share from most recent filing before 2019-01-01, including quarterly filings
aapl.get_earnings_per_share(query_date="2019-01-01", quarterly=True)

# get price and RSI on 2013-08-11
# note that you must first set the Polygon API key for any functions involving price or RSI data
constants.set_polygon_key("YOUR_KEY_HERE")
await aapl.get_price(query_date="2013-08-11")
await aapl.get_rsi(query_date="2013-08-11")

# get WACC on 2016-04-13
aapl.get_wacc(query_date="2016-04-13")
```

Get list of tickers for every company in the S&P 500.
```python
from sec import lookups

# get current S&P 500 tickers
lookups.get_sp500_tickers()

# get S&P 500 tickers on 2019-01-01
lookups.get_sp500_tickers(query_date="2019-01-01")
```

Retrieve and process most recent SEC data. Note that data for most stocks is already processed and included in the package, so this is only necessary if you want to get data for a stock that is not included.
```python
from sec import processor

# download most recent SEC data
# this will take a while and takes up a lot of space on disk
processor.download_sec_data()

# format SEC data for AAPL
# required for data retrieval functions in stock.Stock
processor.process_sec_json("AAPL")
```