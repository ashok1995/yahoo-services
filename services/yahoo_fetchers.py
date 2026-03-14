"""
Yahoo Finance Data Extractors
==============================

Pure extraction functions that pull structured data from yfinance Ticker objects.
No caching, no rate limiting — those concerns live in YahooFinanceService.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)


COMMON_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE"},
]


async def extract_quote(ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
    """Extract quote data from a yfinance Ticker."""
    try:
        info = ticker.info
        if not info or len(info) < 5:
            return None

        return {
            "symbol": symbol,
            "price": info.get("regularMarketPrice"),
            "change": info.get("regularMarketChange"),
            "change_percent": info.get("regularMarketChangePercent"),
            "volume": info.get("volume"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "high_52_week": info.get("fiftyTwoWeekHigh"),
            "low_52_week": info.get("fiftyTwoWeekLow"),
            "open": info.get("regularMarketOpen"),
            "previous_close": info.get("regularMarketPreviousClose"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error extracting quote for {symbol}: {e}")
        return None


async def extract_historical(
    ticker: yf.Ticker, symbol: str, **kwargs
) -> Optional[Dict[str, Any]]:
    """Extract historical OHLCV data from a yfinance Ticker."""
    try:
        period = kwargs.get("period", "1y")
        interval = kwargs.get("interval", "1d")
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return None

        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })

        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": data,
            "total_points": len(data),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error extracting historical data for {symbol}: {e}")
        return None


async def extract_company_info(
    ticker: yf.Ticker, symbol: str
) -> Optional[Dict[str, Any]]:
    """Extract company information from a yfinance Ticker."""
    try:
        info = ticker.info
        if not info:
            return None

        return {
            "symbol": symbol,
            "name": info.get("longName"),
            "short_name": info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "currency": info.get("currency"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "description": info.get("longBusinessSummary"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error extracting company info for {symbol}: {e}")
        return None


async def extract_fundamentals(
    ticker: yf.Ticker, symbol: str
) -> Optional[Dict[str, Any]]:
    """Extract fundamental metrics from a yfinance Ticker."""
    try:
        info = ticker.info
        if not info:
            return None

        return {
            "symbol": symbol,
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "peg_ratio": info.get("pegRatio"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "gross_margin": info.get("grossMargins"),
            "book_value": info.get("bookValue"),
            "cash_per_share": info.get("totalCashPerShare"),
            "beta": info.get("beta"),
            "forward_pe": info.get("forwardPE"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error extracting fundamentals for {symbol}: {e}")
        return None


async def extract_financial_statements(
    ticker: yf.Ticker, symbol: str, **kwargs
) -> Optional[Dict[str, Any]]:
    """Extract financial statements from a yfinance Ticker."""
    try:
        statement_type = kwargs.get("statement_type", "income")

        if statement_type == "income":
            statements = ticker.income_stmt
        elif statement_type == "balance":
            statements = ticker.balance_sheet
        elif statement_type == "cashflow":
            statements = ticker.cashflow
        else:
            raise ValueError(f"Invalid statement type: {statement_type}")

        if statements is None or statements.empty:
            return None

        return {
            "symbol": symbol,
            "statement_type": statement_type,
            "data": statements.to_dict("index"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error extracting {kwargs.get('statement_type', 'income')} statement for {symbol}: {e}")
        return None


async def extract_market_statistics(
    ticker: yf.Ticker, symbol: str
) -> Optional[Dict[str, Any]]:
    """Extract market statistics from a yfinance Ticker."""
    try:
        info = ticker.info
        if not info:
            return None

        return {
            "symbol": symbol,
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "two_hundred_day_average": info.get("twoHundredDayAverage"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error extracting market statistics for {symbol}: {e}")
        return None


def search_common_stocks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search hardcoded common stocks by symbol or name."""
    results = []
    query_upper = query.upper()
    for stock in COMMON_STOCKS:
        if query_upper in stock["symbol"].upper() or query_upper in stock["name"].upper():
            results.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "exchange": stock["exchange"],
            })
            if len(results) >= limit:
                break
    return results
