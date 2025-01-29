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

Retrieve and process most recent SEC data.
```python
from sec import processor

# download most recent SEC data
# this will take a while and takes up a lot of space on disk
processor.download_sec_data()

# if data that is currently downloaded is less than 30 days old, do nothing
# if data has not been downloaded yet or is more than 30 days old, download most recent data
# helpful to put at top of any strategies using this library to ensure data is up to date
processor.download_sec_data(max_stale_days=30)

# after the raw data is downloaded, it must be processed before it can be used via data retrieval functions in stock.Stock
# call this for every company that you would like to access data for (e.g. every company in the S&P500)
# this function only needs to be called once after downloading new data (above)
processor.process_sec_json("AAPL")
```

## Maintenance
Though new financials data from the SEC can be retrieved programatically (as shown above), there are two components of this library that require manual maintenance: the WACC data and list of S&P500 companies. Links to instructions for how to maintain these data sources are below:

[WACC Data](sec/data/wacc/README.md): To be completed at the beginning of every year.

[S&P500 Data](sec/data/sp500/README.md): To be completed monthly.

Any time you make changes to the library, you **must update the version number** in `setup.py`. Then, update or reinstall the package with `pip`. If the version number is not changed, `pip` will not update the library.