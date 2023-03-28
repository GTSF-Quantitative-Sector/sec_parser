import concurrent.futures
import os
from datetime import date, datetime, timedelta

import aiohttp
import pandas as pd
from dateutil import relativedelta

from sec import constants, lookups


class Stock:
    def __init__(self, ticker) -> None:
        self.ticker = ticker
        self.financials = self.get_financials()
        self.industry = lookups.get_industry(ticker)

    def get_financials(self) -> pd.DataFrame:
        """
        Get the financials for the stock.

        Returns:
            pd.DataFrame: DataFrame of financials.
        """
        try:
            with open(
                os.path.join(constants.PROCESSED_DATA_DIR, self.ticker + ".csv")
            ) as f:
                return pd.read_csv(f, index_col=0)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Could not find financials for {self.ticker}. See processor.py to download and process financials."
            )

    def get_metric(
        self,
        metric: str,
        units: str,
        query_date: str = None,
        quarterly: bool = False,
        tolerance: int = 52,
    ) -> float:
        """
        Get a particular metric from the most recent financials before a given date.

        Args:
            metric (str): Metric to get.
            units (str): Units of the metric.
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: Value of the metric.
        """
        if query_date is None:
            query_date = datetime.today().strftime("%Y-%m-%d")
        if not quarterly:
            df = self.financials[self.financials["annual"] == True]
        else:
            df = self.financials
        column = f"{metric}_{units}"
        df = df[df[column].notna()]
        df = df[df.index <= query_date]
        df = df[
            df.index
            >= (
                datetime.strptime(query_date, "%Y-%m-%d") - timedelta(weeks=tolerance)
            ).strftime("%Y-%m-%d")
        ]
        if df.empty:
            period = "quarterly" if quarterly else "annual"
            if query_date is None:
                query_date = "today"
            raise ValueError(
                f"Could not find {period} {metric} for {self.ticker} within {tolerance} weeks of {query_date}."
            )
        return df[column].iloc[-1]

    def get_concept(
        self,
        concept: str,
        tags: list,
        units: str,
        query_date: str = None,
        quarterly: bool = False,
        tolerance: int = 52,
    ) -> float:
        """
        Get an overall concept for a company by trying several different XRBL tags. Returns the first value found.

        Args:
            concept (str): The name of the concept, strictly used for error messages.
            tags (list): List of XRBL tags to search for.
            units (str): Units of the concept. Assumes all tags have the same units.
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: Value of the concept.
        """
        for tag in tags:
            try:
                return self.get_metric(tag, units, query_date, quarterly, tolerance)
            except ValueError:
                pass
        period = "quarterly" if quarterly else "annual"
        if query_date is None:
            query_date = "today"
        raise ValueError(
            f"Could not find {period} {concept} for {self.ticker} within {tolerance} weeks of {query_date}."
        )

    async def get_price(
        ticker: str, query_date: str = None, timeout: int = 20
    ) -> float:
        """
        Get the price of a stock form Polygon.io.

        Args:
            ticker (str): Ticker symbol of the stock.
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            timeout (int): time to wait before raising TimeoutError.
        Returns:
            float: Price of the stock on the given date.
        """
        if query_date is None or query_date == date.today().strftime("%Y-%m-%d"):
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={constants.POLYGON_KEY}"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        response = await resp.json()
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"{ticker}: Timed out while retrieving price")

            return response["results"][0]["c"]
        else:
            url = f"https://api.polygon.io/v1/open-close/{ticker}/{query_date}?adjusted=true&apiKey={constants.POLYGON_KEY}"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        response = await resp.json()
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"{ticker}: Timed out while retrieving price")

                i = 0
                while response["status"] != "OK":
                    # markets will not close for more than 3 days at a time
                    # if price not found within 3 days, price likely does not exist for that time period
                    if i >= 2:
                        raise ValueError(
                            f"Could not find price for {ticker} on {query_date}"
                        )
                    i += 1
                    curr_date = datetime.strptime(query_date, "%Y-%m-%d").date()
                    query_date = (curr_date - timedelta(days=1)).strftime("%Y-%m-%d")
                    url = f"https://api.polygon.io/v1/open-close/{ticker}/{query_date}?adjusted=true&apiKey={constants.POLYGON_KEY}"
                    try:
                        async with session.get(url, timeout=timeout) as resp:
                            response = await resp.json()
                    except concurrent.futures.TimeoutError:
                        raise TimeoutError(
                            f"{ticker}: Timed out while retrieving price"
                        )
            return response["close"]

    async def get_rsi(ticker: str, query_date: str = None, timeout: int = 20) -> float:
        """
        Get the RSI of a stock form Polygon.io.

        Args:
            ticker (str): Ticker symbol of the stock.
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            timeout (int): time to wait before raising TimeoutError.

        Returns:
            float: RSI of the stock on the given date.
        """
        if query_date is None or query_date == date.today().strftime("%Y-%m-%d"):
            url = f"https://api.polygon.io/v1/indicators/rsi/{ticker}?timespan=day&adjusted=true&window=14&series_type=close&order=desc&apiKey={constants.POLYGON_KEY}"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        response = await resp.json()
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"{ticker}: Timed out while retrieving RSI")

            return response["results"]["values"][0]["value"]
        else:
            url = f"https://api.polygon.io/v1/indicators/rsi/{ticker}?timestamp={query_date}&timespan=day&adjusted=true&window=14&series_type=close&order=desc&apiKey={constants.POLYGON_KEY}"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        response = await resp.json()
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"{ticker}: Timed out while retrieving RSI")

                i = 0
                while response["status"] != "OK" or "values" not in response["results"]:
                    # markets will not close for more than 3 days at a time
                    # if price not found within 3 days, price likely does not exist for that time period
                    if i >= 2:
                        raise ValueError(
                            f"Could not find price for {ticker} on {query_date}"
                        )
                    i += 1
                    curr_date = datetime.strptime(query_date, "%Y-%m-%d").date()
                    query_date = (curr_date - timedelta(days=1)).strftime("%Y-%m-%d")
                    url = f"https://api.polygon.io/v1/indicators/rsi/{ticker}?timestamp={query_date}&timespan=day&adjusted=true&window=14&series_type=close&order=desc&apiKey={constants.POLYGON_KEY}"
                    try:
                        async with session.get(url, timeout=timeout) as resp:
                            response = await resp.json()
                    except concurrent.futures.TimeoutError:
                        raise TimeoutError(f"{ticker}: Timed out while retrieving RSI")
            return response["results"]["values"][0]["value"]

    # TODO: calculate WACC per company instead of using industry averages
    def get_wacc(self, query_date: str = None) -> float:
        """
        Get the weighted average cost of capital for the company using industry averages.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.

        Returns:
            float: The WACC for the company.
        """
        if query_date is None:
            query_date = datetime.today().strftime("%Y-%m-%d")
        year = query_date.split("-")[0]
        wacc_df = pd.read_csv(
            os.path.join(constants.WACC_DATA_DIR, f"{year}.csv")
        ).set_index("Industry Name")
        return wacc_df.loc[self.industry, "Cost of Capital"]

    def get_shares_outstanding(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the shares outstanding for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The shares outstanding.
        """
        tags = [
            "EntityCommonStockSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingBasic",
            "CommonStockSharesOutstanding",
        ]
        return self.get_concept(
            "shares outstanding", tags, "shares", query_date, quarterly, tolerance
        )

    def get_net_income(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the net income for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The net income.
        """
        tags = [
            "NetIncomeLoss",
            "ProfitLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic",
            "IncomeLossFromContinuingOperations",
        ]
        return self.get_concept(
            "net income", tags, "USD", query_date, quarterly, tolerance
        )

    def get_interest_expense(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the interest expense for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The interest expense.
        """
        tags = [
            "InterestExpense",
            "InterestExpenseDebt",
            "InterestAndDebtExpense",
            "InterestExpenseBorrowings",
            "InterestIncomeExpenseNonoperatingNet",
            "InterestCostsIncurred",
            "InterestIncomeExpenseNet",
            "InterestPaidNet",
            "InterestPaid",
        ]
        return abs(
            self.get_concept(
                "interest expense", tags, "USD", query_date, quarterly, tolerance
            )
        )

    def get_tax_expense(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the tax expense for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The tax expense.
        """
        try:
            tags = [
                "IncomeTaxExpenseBenefit",
                "IncomeTaxExpenseBenefitContinuingOperations",
                "CurrentIncomeTaxExpenseBenefit",
            ]
            return self.get_concept(
                "tax expense", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            pretax_income = self.get_concept(
                "pretax income", ["ProfitLoss"], "USD", query_date, quarterly, tolerance
            )
            net_income = self.get_net_income(query_date, quarterly, tolerance)
            return pretax_income - net_income

    def get_revenue(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the revenue for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The revenue.
        """
        tags = [
            "Revenues",
            "SalesRevenueNet",
            "SalesRevenueGoodsNet",
            "SalesRevenueServicesNet",
            "SalesRevenueNetOfInterestExpense",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "RevenuesNetOfInterestExpense",
            "OperatingLeasesIncomeStatementLeaseRevenue",
            "OperatingLeaseLeaseIncome",
            "RegulatedAndUnregulatedOperatingRevenue",
        ]
        return self.get_concept(
            "revenue", tags, "USD", query_date, quarterly, tolerance
        )

    def get_cost_of_revenue(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the cost of revenue for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The cost of revenue.
        """
        tags = [
            "CostOfRevenue",
            "CostOfGoodsAndServicesSold",
            "CostOfGoodsSold",
            "CostOfServices",
        ]
        return self.get_concept(
            "cost of revenue", tags, "USD", query_date, quarterly, tolerance
        )

    def get_operating_expenses(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the operating expenses for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The operating expenses.
        """
        tags = ["OperatingExpenses", "OperatingCostsAndExpenses"]
        return self.get_concept(
            "operating expenses", tags, "USD", query_date, quarterly, tolerance
        )

    def get_depreciation(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the depreciation for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The depreciation.
        """
        tags = ["Depreciation"]
        return self.get_concept(
            "depreciation", tags, "USD", query_date, quarterly, tolerance
        )

    def get_amortization(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the amortization for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The amortization.
        """
        tags = [
            "Amortization",
            "AmortizationOfIntangibleAssets",
            "AmortizationOfDebtDiscountPremium",
        ]
        return self.get_concept(
            "amortization", tags, "USD", query_date, quarterly, tolerance
        )

    def get_depreciation_and_amortization(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the depreciation and amortization for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The depreciation and amortization.
        """
        try:
            tags = [
                "DepreciationAndAmortization",
                "DepreciationDepletionAndAmortization",
                "DepreciationAmortizationAndAccretionNet",
                "OtherDepreciationAndAmortization",
            ]
            return self.get_concept(
                "depreciation and amortization",
                tags,
                "USD",
                query_date,
                quarterly,
                tolerance,
            )
        except:
            try:
                depreciation = self.get_depreciation(query_date, quarterly, tolerance)
            except:
                depreciation = 0
            try:
                amortization = self.get_amortization(query_date, quarterly, tolerance)
            except:
                amortization = 0
            if depreciation == 0 and amortization == 0:
                period = "quarterly" if quarterly else "annual"
                if query_date is None:
                    query_date = "today"
                raise ValueError(
                    f"Could not find {period} depreciation and amortization for {self.ticker} within {tolerance} weeks of {query_date}."
                )
            return depreciation + amortization

    def get_current_debt(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the current debt for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The current debt.
        """
        tags = [
            "LongTermDebtCurrent",
            "LongTermDebtAndCapitalLeaseObligationsCurrent",
            "DebtCurrent",
            "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
            "LinesOfCreditCurrent",
            "LineOfCredit",
            "OperatingLeaseLiabilityCurrent",
        ]
        return self.get_concept(
            "current debt", tags, "USD", query_date, quarterly, tolerance
        )

    def get_noncurrent_debt(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the noncurrent debt for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The noncurrent debt.
        """
        tags = [
            "LongTermDebtNoncurrent",
            "ConvertibleLongTermNotesPayable",
            "OperatingLeaseLiabilityNoncurrent",
            "UnsecuredLongTermDebt",
            "LongTermDebtAndCapitalLeaseObligations",
        ]
        return self.get_concept(
            "noncurrent debt", tags, "USD", query_date, quarterly, tolerance
        )

    def get_total_debt(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the total debt for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The total debt.
        """
        try:
            tags = ["LongTermDebt", "DebtAndCapitalLeaseObligations"]
            return self.get_concept(
                "total debt", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            try:
                current_debt = self.get_current_debt(query_date, quarterly, tolerance)
            except:
                current_debt = 0
            try:
                noncurrent_debt = self.get_noncurrent_debt(
                    query_date, quarterly, tolerance
                )
            except:
                noncurrent_debt = 0
            if current_debt == 0 and noncurrent_debt == 0:
                period = "quarterly" if quarterly else "annual"
                if query_date is None:
                    query_date = "today"
                raise ValueError(
                    f"Could not find {period} total debt for {self.ticker} within {tolerance} weeks of {query_date}."
                )
            return current_debt + noncurrent_debt

    def get_property_plant_equipment(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the property, plant, and equipment for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The property, plant, and equipment.
        """
        # TODO: investigate if we can use the "PropertyPlantAndEquipmentNet" tag (may require changes to depreciation and amortization below)
        tags = ["PropertyPlantAndEquipmentGross"]
        return self.get_concept(
            "property, plant, and equipment",
            tags,
            "USD",
            query_date,
            quarterly,
            tolerance,
        )

    def get_capex(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the capital expenditures for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The capital expenditures.
        """
        try:
            tags = [
                "CapitalExpenditures",
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
            ]
            return self.get_concept(
                "capital expenditures", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            # TODO: check if use of depreciation and amortization is correct
            if query_date is None:
                query_date = datetime.today().strftime("%Y-%m-%d")
            one_year_ago = datetime.strptime(
                query_date, "%Y-%m-%d"
            ) - relativedelta.relativedelta(years=1)
            current_ppe = self.get_property_plant_equipment(
                query_date, quarterly, tolerance
            )
            previous_ppe = self.get_property_plant_equipment(
                one_year_ago.strftime("%Y-%m-%d"), quarterly, tolerance
            )
            d_and_a = self.get_depreciation_and_amortization(
                query_date, quarterly, tolerance
            )
            return current_ppe - previous_ppe + d_and_a

    def get_cash(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the cash for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The cash.
        """
        tags = [
            "Cash",
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ]
        return self.get_concept("cash", tags, "USD", query_date, quarterly, tolerance)

    def get_marketable_securities(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the marketable securities for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The marketable securities.
        """
        tags = ["MarketableSecurities", "MarketableSecuritiesCurrent"]
        return self.get_concept(
            "marketable securities", tags, "USD", query_date, quarterly, tolerance
        )

    def get_accounts_receivable(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the accounts receivable for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The accounts receivable.
        """
        tags = ["AccountsReceivableNetCurrent"]
        return self.get_concept(
            "accounts receivable", tags, "USD", query_date, quarterly, tolerance
        )

    def get_inventory(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the inventory for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The inventory.
        """
        tags = ["InventoryNet", "InventoryNetCurrent"]
        return self.get_concept(
            "inventory", tags, "USD", query_date, quarterly, tolerance
        )

    def get_other_current_assets(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the other current assets for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The other current assets.
        """
        tags = ["OtherAssetsCurrent", "PrepaidExpenseAndOtherAssetsCurrent"]
        return self.get_concept(
            "other current assets", tags, "USD", query_date, quarterly, tolerance
        )

    def get_current_assets(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the current assets for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The current assets.
        """
        try:
            tags = ["AssetsCurrent"]
            return self.get_concept(
                "current assets", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            try:
                cash = self.get_cash(query_date, quarterly, tolerance)
            except:
                cash = 0
            try:
                marketable_securities = self.get_marketable_securities(
                    query_date, quarterly, tolerance
                )
            except:
                marketable_securities = 0
            try:
                accounts_receivable = self.get_accounts_receivable(
                    query_date, quarterly, tolerance
                )
            except:
                accounts_receivable = 0
            try:
                inventory = self.get_inventory(query_date, quarterly, tolerance)
            except:
                inventory = 0
            try:
                other_current_assets = self.get_other_current_assets(
                    query_date, quarterly, tolerance
                )
            except:
                other_current_assets = 0
            current_assets = (
                cash
                + marketable_securities
                + accounts_receivable
                + inventory
                + other_current_assets
            )
            if current_assets == 0:
                period = "quarterly" if quarterly else "annual"
                if query_date is None:
                    query_date = "today"
                raise ValueError(
                    f"Could not find {period} current assets for {self.ticker} within {tolerance} weeks of {query_date}."
                )
            return current_assets

    def get_total_assets(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the total assets for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The total assets.
        """
        tags = ["Assets"]
        return self.get_concept(
            "total assets", tags, "USD", query_date, quarterly, tolerance
        )

    def get_accounts_payable(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the accounts payable for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The accounts payable.
        """
        tags = [
            "AccountsPayableCurrent",
            "OtherAccountsPayableAndAccruedLiabilities",
            "AccountsPayableTradeCurrent",
            "AccountsPayableTradeCurrentAndNoncurrent",
        ]
        return self.get_concept(
            "accounts payable", tags, "USD", query_date, quarterly, tolerance
        )

    def get_taxes_payable(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the taxes payable for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The taxes payable.
        """
        tags = [
            "TaxesPayableCurrent",
            "TaxesPayableCurrentAndNoncurrent",
            "AccruedIncomeTaxesCurrent",
            "AccruedIncomeTaxes",
            "AccrualForTaxesOtherThanIncomeTaxesCurrent",
        ]
        return self.get_concept(
            "taxes payable", tags, "USD", query_date, quarterly, tolerance
        )

    def get_accrued_salaries(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the accrued salaries for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The accrued salaries.
        """
        tags = ["AccruedSalariesAndWagesCurrent", "AccruedSalariesCurrent"]
        return self.get_concept(
            "accrued salaries", tags, "USD", query_date, quarterly, tolerance
        )

    def get_interest_payable(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the interest payable for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The interest payable.
        """
        tags = ["InterestPayableCurrent", "InterestPayableCurrentAndNoncurrent"]
        return self.get_concept(
            "interest payable", tags, "USD", query_date, quarterly, tolerance
        )

    def get_deferred_revenues(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the deferred revenues for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The deferred revenues.
        """
        tags = [
            "DeferredRevenueCurrent",
            "ContractWithCustomerLiability",
            "ContractWithCustomerLiabilityCurrent",
        ]
        return self.get_concept(
            "deferred revenues", tags, "USD", query_date, quarterly, tolerance
        )

    def get_accrued_liabilities(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the accrued liabilities for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The accrued liabilities.
        """
        tags = [
            "AccruedLiabilitiesCurrent",
            "AccruedInsuranceCurrent",
            "AccruedLiabilitiesCurrentAndNoncurrent",
        ]
        return self.get_concept(
            "accrued liabilities", tags, "USD", query_date, quarterly, tolerance
        )

    def get_other_current_liabilities(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the other current liabilities for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The other current liabilities.
        """
        tags = [
            "OtherLiabilitiesCurrent",
            "OtherAccruedLiabilitiesCurrent",
            "LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationCurrent",
            "DerivativeLiabilitiesCurrent",
            "LiabilitiesOfDisposalGroupIncludingDiscontinuedOperation",
        ]
        return self.get_concept(
            "other current liabilities", tags, "USD", query_date, quarterly, tolerance
        )

    def get_current_liabilities(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the current liabilities for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The current liabilities.
        """
        try:
            tags = ["LiabilitiesCurrent"]
            return self.get_concept(
                "current liabilities", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            try:
                current_debt = self.get_current_debt(query_date, quarterly, tolerance)
            except:
                current_debt = 0
            try:
                accounts_payable = self.get_accounts_payable(
                    query_date, quarterly, tolerance
                )
            except:
                accounts_payable = 0
            try:
                taxes_payable = self.get_taxes_payable(query_date, quarterly, tolerance)
            except:
                taxes_payable = 0
            try:
                accrued_salaries = self.get_accrued_salaries(
                    query_date, quarterly, tolerance
                )
            except:
                accrued_salaries = 0
            try:
                interest_payable = self.get_interest_payable(
                    query_date, quarterly, tolerance
                )
            except:
                interest_payable = 0
            try:
                deferred_revenues = self.get_deferred_revenues(
                    query_date, quarterly, tolerance
                )
            except:
                deferred_revenues = 0
            try:
                accrued_liabilities = self.get_accrued_liabilities(
                    query_date, quarterly, tolerance
                )
            except:
                accrued_liabilities = 0
            try:
                other_liabilities = self.get_other_current_liabilities(
                    query_date, quarterly, tolerance
                )
            except:
                other_liabilities = 0
            current_liabilities = (
                current_debt
                + accounts_payable
                + taxes_payable
                + accrued_salaries
                + interest_payable
                + deferred_revenues
                + accrued_liabilities
                + other_liabilities
            )
            if current_liabilities == 0:
                period = "quarterly" if quarterly else "annual"
                if query_date is None:
                    query_date = "today"
                raise ValueError(
                    f"Could not find {period} current liabilities for {self.ticker} within {tolerance} weeks of {query_date}."
                )
            return current_liabilities

    def get_liabilities_and_equity(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the liabilities and equity for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The liabilities and equity.
        """
        tags = ["LiabilitiesAndStockholdersEquity"]
        return self.get_concept(
            "liabilities and equity", tags, "USD", query_date, quarterly, tolerance
        )

    def get_stockholders_equity(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the shareholders equity for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The shareholders equity.
        """
        tags = [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ]
        return self.get_concept(
            "shareholders equity", tags, "USD", query_date, quarterly, tolerance
        )

    def get_preferred_stock(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the preferred stock for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The preferred stock.
        """
        tags = [
            "PreferredStockValue",
            "PreferredStockValueIncludingPortionAttributableToNoncontrollingInterest",
        ]
        return self.get_concept(
            "preferred stock", tags, "USD", query_date, quarterly, tolerance
        )

    def get_preferred_dividends(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the preferred dividends for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The preferred dividends.
        """
        tags = ["DividendsPreferredStock"]
        return self.get_concept(
            "preferred dividends", tags, "USD", query_date, quarterly, tolerance
        )

    def get_total_liabilities(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the total liabilities for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The total liabilities.
        """
        try:
            tags = ["Liabilities"]
            return self.get_concept(
                "total liabilities", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            liabilities_and_equity = self.get_liabilities_and_equity(
                query_date, quarterly, tolerance
            )
            equity = self.get_stockholders_equity(query_date, quarterly, tolerance)
            return liabilities_and_equity - equity

    def get_book_value(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the book value for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The book value.
        """
        equity = self.get_stockholders_equity(query_date, quarterly, tolerance)
        try:
            preferred_stock = self.get_preferred_stock(query_date, quarterly, tolerance)
        except:
            preferred_stock = 0
        return equity - preferred_stock

    def get_book_value_per_share(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the book value per share for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The book value per share.
        """
        book_value = self.get_book_value(query_date, quarterly, tolerance)
        shares = self.get_shares_outstanding(query_date, quarterly, tolerance)
        return book_value / shares

    def get_earnings_per_share(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the earnings per share for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The earnings per share.
        """
        net_income = self.get_net_income(query_date, quarterly, tolerance)
        try:
            preferred_dividends = self.get_preferred_dividends(
                query_date, quarterly, tolerance
            )
        except:
            preferred_dividends = 0
        shares = self.get_shares_outstanding(query_date, quarterly, tolerance)
        return (net_income - preferred_dividends) / shares

    def get_sales_per_share(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the sales per share for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The sales per share.
        """
        sales = self.get_revenue(query_date, quarterly, tolerance)
        shares = self.get_shares_outstanding(query_date, quarterly, tolerance)
        return sales / shares

    def get_working_capital(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the working capital for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The working capital.
        """
        current_assets = self.get_current_assets(query_date, quarterly, tolerance)
        current_liabilities = self.get_current_liabilities(
            query_date, quarterly, tolerance
        )
        return current_assets - current_liabilities

    def get_change_in_working_capital(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the change in working capital for a company over a one year period.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The change in working capital.
        """
        if query_date is None:
            query_date = datetime.today().strftime("%Y-%m-%d")
        one_year_ago = datetime.strptime(
            query_date, "%Y-%m-%d"
        ) - relativedelta.relativedelta(years=1)
        current_wc = self.get_working_capital(query_date, quarterly, tolerance)
        previous_wc = self.get_working_capital(
            one_year_ago.strftime("%Y-%m-%d"), quarterly, tolerance
        )
        return current_wc - previous_wc

    def get_operating_cash_flow(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the operating cash flow for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The operating cash flow.
        """
        net_income = self.get_net_income(query_date, quarterly, tolerance)
        d_and_a = self.get_depreciation_and_amortization(
            query_date, quarterly, tolerance
        )
        change_in_wc = self.get_change_in_working_capital(
            query_date, quarterly, tolerance
        )
        return net_income + d_and_a - change_in_wc

    def get_ocf_per_share(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the operating cash flow per share for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The operating cash flow per share.
        """
        ocf = self.get_operating_cash_flow(query_date, quarterly, tolerance)
        shares = self.get_shares_outstanding(query_date, quarterly, tolerance)
        return ocf / shares

    def get_cash_dividends(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the cash dividends for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The cash dividends.
        """
        tags = [
            "DividendsCommonStockCash",
            "DividendsCash",
            "PaymentsOfDividends",
            "PaymentsOfDividendsCommonStock",
        ]
        return self.get_concept(
            "cash dividends", tags, "USD", query_date, quarterly, tolerance
        )

    def get_share_repurchases(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the USD value of share repurchases for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The share repurchases.
        """
        tags = [
            "PaymentsForRepurchaseOfCommonStock",
            "PaymentsForRepurchaseOfEquity",
            "StockRepurchasedDuringPeriodValue",
            "PaymentsForRepurchaseOfRedeemableNoncontrollingInterest",
        ]
        return self.get_concept(
            "share repurchases", tags, "USD", query_date, quarterly, tolerance
        )

    def get_share_issuances(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the USD value of share issuances for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The share issuances.
        """
        tags = [
            "ProceedsFromIssuanceOfCommonStock",
            "ProceedsFromIssuanceOrSaleOfEquity",
            "ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions",
        ]
        return self.get_concept(
            "share issuances", tags, "USD", query_date, quarterly, tolerance
        )

    # TODO: Improve coverage
    def get_debt_paydown(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the USD value of debt paydown for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The debt paydown.
        """
        tags = ["RepaymentsOfLongTermDebt"]
        return self.get_concept(
            "debt paydown", tags, "USD", query_date, quarterly, tolerance
        )

    # TODO: Improve coverage
    def get_debt_issuance(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the USD value of debt issuance for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The debt issuance.
        """
        tags = [
            "ProceedsFromIssuanceOfLongTermDebt",
            "ProceedsFromIssuanceOfSeniorLongTermDebt",
        ]
        return self.get_concept(
            "debt issuance", tags, "USD", query_date, quarterly, tolerance
        )

    def get_ebit(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the EBIT for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The EBIT.
        """
        try:
            tags = ["OperatingIncomeLoss"]
            return self.get_concept(
                "ebit", tags, "USD", query_date, quarterly, tolerance
            )
        except:
            try:
                net_income = self.get_net_income(query_date, quarterly, tolerance)
                interest_expense = self.get_interest_expense(
                    query_date, quarterly, tolerance
                )
                tax_expense = self.get_tax_expense(query_date, quarterly, tolerance)
                return net_income + interest_expense + tax_expense
            except:
                revenue = self.get_revenue(query_date, quarterly, tolerance)
                cost_of_revenue = self.get_cost_of_revenue(
                    query_date, quarterly, tolerance
                )
                operating_expenses = self.get_operating_expenses(
                    query_date, quarterly, tolerance
                )
                return revenue - cost_of_revenue - operating_expenses

    def get_ebitda(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the EBITDA for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The EBITDA.
        """
        ebit = self.get_ebit(query_date, quarterly, tolerance)
        d_and_a = self.get_depreciation_and_amortization(
            query_date, quarterly, tolerance
        )
        return ebit + d_and_a

    def get_ufcf(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the unlevered free cash flow for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The unlevered free cash flow.
        """
        ebit = self.get_ebit(query_date, quarterly, tolerance)
        tax_expense = self.get_tax_expense(query_date, quarterly, tolerance)
        d_and_a = self.get_depreciation_and_amortization(
            query_date, quarterly, tolerance
        )
        capex = self.get_capex(query_date, quarterly, tolerance)
        change_in_wc = self.get_change_in_working_capital(
            query_date, quarterly, tolerance
        )
        return ebit - tax_expense + d_and_a - capex - change_in_wc

    async def get_pb_ratio(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the price to book ratio for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The price to book ratio.
        """
        price = await self.get_price(query_date)
        bvps = self.get_book_value_per_share(query_date, quarterly, tolerance)
        return price / bvps

    async def get_pe_ratio(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the price to earnings ratio for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The price to earnings ratio.
        """
        price = await self.get_price(query_date)
        eps = self.get_earnings_per_share(query_date, quarterly, tolerance)
        return price / eps

    async def get_ps_ratio(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the price to sales ratio for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The price to sales ratio.
        """
        price = await self.get_price(query_date)
        sps = self.get_sales_per_share(query_date, quarterly, tolerance)
        return price / sps

    async def get_pcf_ratio(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the price to cash flow ratio for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The price to cash flow ratio.
        """
        price = await self.get_price(query_date)
        cfps = self.get_ocf_per_share(query_date, quarterly, tolerance)
        return price / cfps

    async def get_market_cap(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the market cap for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The market cap.
        """
        price = await self.get_price(query_date)
        shares = self.get_shares_outstanding(query_date, quarterly, tolerance)
        return price * shares

    async def get_enterprise_value(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the enterprise value for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The enterprise value.
        """
        market_cap = await self.get_market_cap(query_date, quarterly, tolerance)
        debt = self.get_total_debt(query_date, quarterly, tolerance)
        cash = self.get_cash(query_date, quarterly, tolerance)
        ev = market_cap + debt - cash
        return ev

    async def get_ev_to_ebitda(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the enterprise value to ebitda ratio for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The enterprise value to ebitda ratio.
        """
        ev = await self.get_enterprise_value(query_date, quarterly, tolerance)
        ebitda = self.get_ebitda(query_date, quarterly, tolerance)
        return ev / ebitda

    async def get_shareholder_yield(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> float:
        """
        Get the shareholder yield for a company.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            float: The shareholder yield.
        """
        market_cap = await self.get_market_cap(query_date, quarterly, tolerance)
        try:
            cash_dividends = self.get_cash_dividends(query_date, quarterly, tolerance)
        except:
            cash_dividends = 0
        try:
            share_repurchases = self.get_share_repurchases(
                query_date, quarterly, tolerance
            )
        except:
            share_repurchases = 0
        try:
            share_issuances = self.get_share_issuances(query_date, quarterly, tolerance)
        except:
            share_issuances = 0
        try:
            debt_paydown = self.get_debt_paydown(query_date, quarterly, tolerance)
        except:
            debt_paydown = 0
        try:
            debt_issuance = self.get_debt_issuance(query_date, quarterly, tolerance)
        except:
            debt_issuance = 0
        return (
            cash_dividends
            + share_repurchases
            - share_issuances
            + debt_paydown
            - debt_issuance
        ) / market_cap

    async def get_vc2_metrics(
        self, query_date: str = None, quarterly: bool = False, tolerance: int = 52
    ) -> dict:
        """
        Get the VC2 metrics for a company. More efficient than calling each one individually.

        Args:
            query_date (str, optional): Date in YYYY-MM-DD format. Defaults to None, which gets the latest metric.
            quarterly (bool, optional): Whether to consider quarterly values. Defaults to False, which only searches for annual values.
            tolerance (int, optional): The max number of weeks to look back for a filing date. Defaults to 52.

        Returns:
            dict: The VC2 metrics.
        """
        price = await self.get_price(query_date)
        shares = self.get_shares_outstanding(query_date, quarterly, tolerance)
        market_cap = price * shares
        data = {}

        # get price to book
        book_val = self.get_book_value(query_date, quarterly, tolerance)
        bvps = book_val / shares
        data["pb_ratio"] = price / bvps

        # get price to earnings
        net_income = self.get_net_income(query_date, quarterly, tolerance)
        try:
            preferred_dividends = self.get_preferred_dividends(
                query_date, quarterly, tolerance
            )
        except:
            preferred_dividends = 0
        eps = (net_income - preferred_dividends) / shares
        data["pe_ratio"] = price / eps

        # get price to sales
        sales = self.get_revenue(query_date, quarterly, tolerance)
        sps = sales / shares
        data["ps_ratio"] = price / sps

        # get price to cash flow
        ocf = self.get_operating_cash_flow(query_date, quarterly, tolerance)
        cfps = ocf / shares
        data["pcf_ratio"] = price / cfps

        # get ev to ebitda
        debt = self.get_total_debt(query_date, quarterly, tolerance)
        cash = self.get_cash(query_date, quarterly, tolerance)
        ev = market_cap + debt - cash
        ebitda = self.get_ebitda(query_date, quarterly, tolerance)
        data["ev_ebitda"] = ev / ebitda

        # get shareholder yield
        try:
            cash_dividends = self.get_cash_dividends(query_date, quarterly, tolerance)
        except:
            cash_dividends = 0
        try:
            share_repurchases = self.get_share_repurchases(
                query_date, quarterly, tolerance
            )
        except:
            share_repurchases = 0
        try:
            share_issuances = self.get_share_issuances(query_date, quarterly, tolerance)
        except:
            share_issuances = 0
        try:
            debt_paydown = self.get_debt_paydown(query_date, quarterly, tolerance)
        except:
            debt_paydown = 0
        try:
            debt_issuance = self.get_debt_issuance(query_date, quarterly, tolerance)
        except:
            debt_issuance = 0
        data["shareholder_yield"] = (
            cash_dividends
            + share_repurchases
            - share_issuances
            + debt_paydown
            - debt_issuance
        ) / market_cap

        return data
