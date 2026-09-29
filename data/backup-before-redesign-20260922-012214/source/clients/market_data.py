"""Market data & financial solvency engine powered by yfinance.

Fetches balance sheet cash, quarterly burn rates, calculates cash runway,
and assigns dilution risk levels.
"""

import structlog
import yfinance as yf
from typing import Optional
from datetime import datetime, timezone
import statistics

from core.models import CompanyFinancials, DilutionRiskLevel, utc_now_iso
from core.http_client import get_retry_session

logger = structlog.get_logger()


class MarketDataClient:
    def __init__(self):
        self.session = get_retry_session()

    def get_financials(self, ticker: str) -> Optional[CompanyFinancials]:
        """Fetches market cap, cash reserves, and computes cash runway for a ticker."""
        if not ticker:
            return None

        clean_ticker = ticker.strip().upper()
        try:
            yt = yf.Ticker(clean_ticker, session=self.session)
            info = yt.info or {}

            # yfinance often returns an empty dict for invalid/delisted tickers
            if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info):
                logger.warning(f"Ticker {clean_ticker} returned no valid pricing data. May be delisted or private.")
                return None

            company_name = info.get("shortName") or info.get("longName") or clean_ticker
            stock_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("navPrice")
            
            market_cap = info.get("marketCap")
            if not market_cap and stock_price and info.get("sharesOutstanding"):
                market_cap = stock_price * info.get("sharesOutstanding")

            # Cash and equivalents from info
            total_cash = info.get("totalCash")
            debt_to_equity = info.get("debtToEquity")
            fifty_two_high = info.get("fiftyTwoWeekHigh")
            fifty_two_low = info.get("fiftyTwoWeekLow")
            currency = info.get("currency", "USD")
            
            # Extract detailed balance sheet metrics if available
            short_term_debt = None
            cash_and_equiv = None
            short_term_inv = None
            try:
                bs = yt.balance_sheet
                if bs is not None and not bs.empty:
                    # Current Debt
                    for debt_label in ["Current Debt", "Current Debt And Capital Lease Obligation", "Short Term Debt"]:
                        if debt_label in bs.index:
                            recent_debt = bs.loc[debt_label].dropna()
                            if not recent_debt.empty:
                                short_term_debt = float(recent_debt.iloc[0])
                                break

                    # Cash & Short-Term Investments (Treasury bills, marketable securities)
                    for cash_label in ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]:
                        if cash_label in bs.index:
                            recent_cash = bs.loc[cash_label].dropna()
                            if not recent_cash.empty:
                                cash_and_equiv = float(recent_cash.iloc[0])
                                break

                    for inv_label in ["Other Short Term Investments", "Short Term Investments"]:
                        if inv_label in bs.index:
                            recent_inv = bs.loc[inv_label].dropna()
                            if not recent_inv.empty:
                                short_term_inv = float(recent_inv.iloc[0])
                                break

                    # If totalCash from info is missing, reconstruct from balance sheet
                    bs_liquid_total = 0.0
                    if cash_and_equiv:
                        bs_liquid_total += cash_and_equiv
                    if short_term_inv:
                        bs_liquid_total += short_term_inv

                    if (total_cash is None or total_cash == 0) and bs_liquid_total > 0:
                        total_cash = bs_liquid_total
                    elif total_cash is not None and bs_liquid_total > total_cash:
                        # Balance sheet captures marketable securities/Treasuries omitted from info.totalCash
                        total_cash = bs_liquid_total
            except Exception:
                pass

            # Determine burn rate, runway, and data freshness (accounting for debt obligations)
            quarterly_burn, runway_months, risk_level, freshness_warning = self._compute_runway_and_burn(
                yt, info, total_cash, short_term_debt
            )

            return CompanyFinancials(
                ticker=clean_ticker,
                company_name=company_name,
                market_cap=float(market_cap) if market_cap else None,
                stock_price=float(stock_price) if stock_price else None,
                total_liquid_cash=float(total_cash) if total_cash else None,
                cash_and_equivalents=float(cash_and_equiv) if cash_and_equiv else (float(total_cash) if total_cash else None),
                short_term_investments=float(short_term_inv) if short_term_inv else None,
                quarterly_burn_rate=float(quarterly_burn) if quarterly_burn is not None else None,
                cash_runway_months=float(runway_months) if runway_months is not None else None,
                dilution_risk_level=risk_level,
                debt_to_equity=float(debt_to_equity) if debt_to_equity else None,
                short_term_debt=short_term_debt,
                fifty_two_week_high=float(fifty_two_high) if fifty_two_high else None,
                fifty_two_week_low=float(fifty_two_low) if fifty_two_low else None,
                currency=currency,
                data_freshness_warning=freshness_warning,
                fetched_at=utc_now_iso()
            )
        except Exception as e:
            logger.error(f"Error fetching financial data for {clean_ticker}: {e}")
            return None

    def _compute_runway_and_burn(
        self,
        yt: yf.Ticker,
        info: dict,
        total_cash: Optional[float],
        short_term_debt: Optional[float] = None
    ):
        quarterly_burn = None
        runway_months = None
        risk_level = DilutionRiskLevel.MODERATE
        freshness_warning = None

        try:
            # 1. Try quarterly cash flow statement for recent Operating Cash Flow
            # Take the median of up to the last 4 quarters to avoid single-quarter milestone spikes
            q_cf = yt.quarterly_cashflow
            if q_cf is not None and not q_cf.empty and "Operating Cash Flow" in q_cf.index:
                # Check data freshness
                most_recent_date = q_cf.columns[0]
                if hasattr(most_recent_date, "tzinfo"):
                    days_old = (datetime.now(most_recent_date.tzinfo or timezone.utc) - most_recent_date).days
                    if days_old > 105:  # Standard 90 days + 15 days filing grace period
                        freshness_warning = f"Financial data is stale ({days_old} days old). Quarter has ended; imminent 10-Q filing may drastically alter cash runway."
                
                recent_op_cfs = q_cf.loc["Operating Cash Flow"].dropna().tolist()[:4]
                if recent_op_cfs:
                    median_ocf = statistics.median(recent_op_cfs)
                    if median_ocf < 0:
                        quarterly_burn = abs(float(median_ocf))
                    else:
                        quarterly_burn = 0.0  # Cash flow positive
        except Exception as e:
            logger.debug(f"Could not compute quarterly burn from cashflow: {e}")

        # 2. Fallback to annual operating cashflow from info
        if quarterly_burn is None:
            op_cash = info.get("operatingCashflow")
            if op_cash is not None:
                if op_cash < 0:
                    quarterly_burn = abs(float(op_cash)) / 4.0
                else:
                    quarterly_burn = 0.0

        # 3. Calculate runway if cash is available
        if total_cash is not None and total_cash > 0:
            if quarterly_burn is not None:
                if quarterly_burn <= 0:
                    runway_months = 999.0
                    risk_level = DilutionRiskLevel.LOW
                else:
                    runway_months = round((total_cash / quarterly_burn) * 3.0, 1)

                    if runway_months < 6.0:
                        risk_level = DilutionRiskLevel.CRITICAL
                    elif runway_months < 12.0:
                        risk_level = DilutionRiskLevel.HIGH
                    elif runway_months < 24.0:
                        risk_level = DilutionRiskLevel.MODERATE
                    else:
                        risk_level = DilutionRiskLevel.LOW
            else:
                runway_months = None
                risk_level = DilutionRiskLevel.MODERATE

            # 4. Short-term debt burden adjustment
            # If short-term debt due within 12 months exceeds or approaches cash reserves,
            # it represents an acute debt maturity cliff regardless of operational burn.
            if short_term_debt is not None and short_term_debt > 0:
                if short_term_debt >= total_cash:
                    risk_level = DilutionRiskLevel.CRITICAL
                elif short_term_debt >= 0.50 * total_cash:
                    if risk_level == DilutionRiskLevel.LOW:
                        risk_level = DilutionRiskLevel.MODERATE
        elif total_cash is not None and total_cash <= 0:
            runway_months = 0.0
            risk_level = DilutionRiskLevel.CRITICAL

        return quarterly_burn, runway_months, risk_level, freshness_warning
