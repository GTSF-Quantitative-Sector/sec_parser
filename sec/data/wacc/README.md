The steps below should be completed at the beginning of every year.

### WACC data source
link: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html

Look for "Costs of Capital by Industry (in US $)" and download the file for the given year in the "US" column.
For example, download the file at the "1/24" link and name it 2024.csv in this directory. The library accesses the "Cost of Capital" column within this file -- **ensure the values in this column are formatted as decimals (and not as percentages).**

If a new year rolls around and there is no file yet at the above link, simply duplicate the file from the previous year in this directory and name it for the current year. This is a temporary fix to ensure that we will not have an error thrown when trying to access current WACC for a company. Keep checking back to see when the new file for this year is posted, and then download it (replacing the temporary duplicate file we created).

### Ticker to industry mapping
link: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/databreakdown.html

Download the indname.xlsx spreadsheet located at the link under the "Company Lookup" section. Older workbooks have a "US By Industry" sheet with "Ticker" and "Industry Group" columns. The current workbook has a global "By industry" sheet with "Exchange:Ticker" and "Industry Group" columns. Filter to US trading venues (NYSE, NasdaqGS, NasdaqGM, NasdaqCM, NYSEAM, BATS and OTCPK) before removing the exchange prefix; otherwise foreign symbols can collide with US symbols. Keep only the ticker and industry, strip surrounding industry whitespace, rename the columns `ticker` and `industry`, and export as industries.csv. Reject duplicate ticker keys.

Retain existing mappings only for tickers absent from the refreshed source to support historical queries. These retained rows are legacy classifications, not newly verified data. Document any added ticker aliases or manual classifications below. The mapping is not point-in-time: historical WACC queries use the current industry mapping with the selected year's rates.

### Verification of new files
Sometimes the industry names in the WACC files have typos or are slightly altered year over year. This will cause an error when we query the WACC file using the proper industry name that is given in industries.csv. Such errors and variations must be manually corrected so that the industry names are consistent. To do this, call `get_wacc()` on all companies in the S&P500 and note any that throw an error. Determine which industry is being queried, and find the closest one in the new year's WACC file. Then change the name of the industry in the WACC file to the one that is being queried by the failing company. Repeat this process until no errors are thrown.

### Date of last data update
2026-11-04.

- Replaced the 2025 placeholder (its parsed contents were identical to 2024.csv) with the actual January 2025 US data: https://pages.stern.nyu.edu/~adamodar/pc/archives/wacc24.xls. The archive filename ends in 24, but the workbook's update date is 2025-01-05.
- Added January 2026 US data from https://pages.stern.nyu.edu/~adamodar/pc/datasets/wacc.xls (workbook update date 2026-01-05). The current year's workbook is linked from https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html before it appears in the archives.
- Extracted the `Industry Averages` table from each workbook, preserving numeric rates as decimal values. Each annual file has 96 rows, including the two market aggregates. Neither file is a placeholder.
- Refreshed https://pages.stern.nyu.edu/~adamodar/pc/datasets/indname.xlsx: 6,937 source rows from US trading venues, 10 documented additions, and 1,606 legacy-only rows retained, totaling 8,553 unique ticker mappings. Removed two unclassified legacy rows (LTNC and MGL) whose previous industry was `#N/A`. The CSV reader preserves the valid ticker `NA` as text.

### Mapping additions

Share-class aliases use the same issuer's current source classification: BRK.B from BRK.A, FOX from FOXA, GOOG from GOOGL, and NWS from NWSA.

Verified ticker changes retain the prior ticker's source classification:

- BNY from BK: https://www.bny.com/corporate/global/en/about-us/newsroom/press-release/bny-announces-planned-change-of-stock-ticker-symbol-to-bny-130465.html
- MRSH from MMC: https://www.marsh.com/en/corp/about/news/marsh-mclennan-to-change-nyse-symbol-to-mrsh.html
- ECHO from SATS: https://ir.echostar.com/news-releases/news-release-details/echostar-changing-stocker-ticker-sats-echo-marking-companys-next

The following are maintainer classifications based on the companies' described businesses, not classifications supplied in the January workbook:

- FDXF: `Trucking`, reflecting its less-than-truckload freight business: https://investor.fedex.com/news-and-events/investor-news/investor-news-details/2026/FedEx-Completes-Spin-Off-of-FedEx-Freight/default.aspx
- HONA: `Aerospace/Defense`, reflecting its aerospace and defense business: https://investor.honeywellaerospace.com/static-files/cef62ef4-bf52-4d3f-9572-6f04f08699f5
- VMRK: `R.E.I.T.`, consistent with both predecessor companies (AVB and EQR): https://investors.vivmarkresidential.com/news-events/press-releases/detail/113/vivmark-residential-launches-as-one-of-the-countrys-leading-real-estate-companies

### Reproduce validation

After installing the checkout, run `python scripts/validate_maintenance.py` from the repository root. This checks history ordering and duplicate keys, coverage in the [packaged SEC issuer lookup](../cik/README.md), decimal WACC values, and `Stock.get_wacc()` for every latest-source constituent in both 2025 and 2026. The WACC-only check bypasses the constructor's unrelated financial-data load; a separate check exercises the full constructor where financial files exist and reports missing SEC files. Refreshing SEC financials is separate from these maintenance datasets. A successful constructor check confirms the file loads, so check its latest filing date before use.

Validation on 2026-11-04 passed WACC lookups for all 503 latest-source tickers in both annual files. Full construction and WACC lookup passed for 455 tickers; 48 lack packaged SEC financial files and require a separate financial-data refresh before normal `Stock(ticker)` use.

Source workbook SHA-256 checksums:

- 2025: `812345650229c0a1c50921f5bab7ea3198dd5f48f05e7956d175cb349a508dea`
- 2026: `d38b149c731bba6847d077ef67c9a4bfa0a54f947ba480b2f9ea89f5451d39a6`
- Company lookup: `79d481bf820bc8cdd2f4ddf8b910d77cf05f37c657de2d7ac001a817ad08f6bc`
