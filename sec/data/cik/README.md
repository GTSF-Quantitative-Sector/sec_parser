The packaged SEC ticker lookup is used to select issuer files from `companyfacts.zip`.
When refreshing S&P 500 membership, verify every added or renamed ticker against
the issuer's SEC filings. This lookup has one CIK per ticker and does not resolve
historical ticker reuse. Keep distinct historical ticker aliases for the same
issuer so older membership snapshots can still be processed.

### November 2026 refresh

Corrected `BNY` to Bank of New York Mellon. Its NYSE ticker changed from `BK`,
which remains an alias. The previous `BNY` entry referred to a BlackRock municipal
income trust and must not be used to process Bank of New York Mellon filings.
Added eleven missing mappings for the August 18 membership snapshot.
Corrected `FERG` to Ferguson Enterprises, which succeeded Ferguson plc as the
public issuer on August 1, 2024 and retained the ticker.

| Ticker | CIK | SEC source |
| --- | --- | --- |
| BNY | 0001390777 | [Bank of New York Mellon](https://www.sec.gov/Archives/edgar/data/1390777/000139077726000071/R1.htm) |
| ECHO | 0001415404 | [EchoStar](https://www.sec.gov/edgar/browse/?CIK=1415404) |
| EXE | 0000895126 | [Expand Energy](https://www.sec.gov/Archives/edgar/data/895126/000110465926108003/0001104659-26-108003-index.htm) |
| FDXF | 0002082247 | [FedEx Freight](https://www.sec.gov/Archives/edgar/data/2082247/000162828026068246/fdxf-20260930.htm) |
| FERG | 0002011641 | [Ferguson Enterprises](https://www.sec.gov/Archives/edgar/data/2011641/000201164124000005/ferg-20240731.htm) |
| FISV | 0000798354 | [Fiserv](https://www.sec.gov/Archives/edgar/data/798354/000079835426000031/0000798354-26-000031-index.htm) |
| HONA | 0002089271 | [Honeywell Aerospace](https://www.sec.gov/edgar/browse/?CIK=2089271) |
| MRSH | 0000062709 | [Marsh](https://www.sec.gov/Archives/edgar/data/62709/000087666126000867/0000876661-26-000867-index.htm) |
| PSKY | 0002041610 | [Paramount Skydance](https://www.sec.gov/Archives/edgar/data/2041610/000110465926113573/0001104659-26-113573-index.htm) |
| Q | 0002058873 | [Qnity Electronics](https://www.sec.gov/Archives/edgar/data/2058873/000205887326000030/0002058873-26-000030-index.htm) |
| SNDK | 0002023554 | [Sandisk](https://www.sec.gov/edgar/browse/index.html?cik=2023554) |
| VMRK | 0000906107 | [Vivmark Residential](https://www.sec.gov/edgar/browse/index.html?cik=906107) |
| XYZ | 0001512673 | [Block](https://www.sec.gov/Archives/edgar/data/1512673/000162828026069513/0001628280-26-069513-index.htm) |
