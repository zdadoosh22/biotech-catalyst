"""Database manager for BioCatalyst SQLite instance.

Caches ClinicalTrials.gov API responses, yfinance balance sheets,
and stores AI Diligence reports and watchlist entries.
"""

import json
import sqlite3
import contextlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.config import DB_PATH
from core.models import (
    ClinicalTrial, Endpoint, Intervention, CompanyFinancials,
    DiligenceReport, MolecularAnalysis, BiostatAudit,
    FinancialCatalystAudit, DilutionRiskLevel, ConsensusVerdict
)


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._run_migrations()

    @contextlib.contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Clinical Trials Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clinical_trials (
                    nct_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    official_title TEXT,
                    sponsor_name TEXT NOT NULL,
                    matched_ticker TEXT,
                    phases TEXT,
                    status TEXT,
                    conditions TEXT,
                    interventions TEXT,
                    primary_endpoints TEXT,
                    secondary_endpoints TEXT,
                    enrollment INTEGER,
                    start_date TEXT,
                    start_date_type TEXT,
                    primary_completion_date TEXT,
                    primary_completion_date_type TEXT,
                    completion_date TEXT,
                    completion_date_type TEXT,
                    brief_summary TEXT,
                    detailed_description TEXT,
                    allocation TEXT,
                    masking TEXT,
                    estimated_catalyst_window TEXT,
                    last_updated TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Company Financials Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_financials (
                    ticker TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    market_cap REAL,
                    stock_price REAL,
                    total_liquid_cash REAL,
                    cash_and_equivalents REAL,
                    short_term_investments REAL,
                    quarterly_burn_rate REAL,
                    cash_runway_months REAL,
                    dilution_risk_level TEXT,
                    debt_to_equity REAL,
                    short_term_debt REAL,
                    fifty_two_week_high REAL,
                    fifty_two_week_low REAL,
                    currency TEXT,
                    data_freshness_warning TEXT,
                    fetched_at TEXT
                )
            """)

            # 3. Diligence Reports Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS diligence_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nct_id TEXT NOT NULL,
                    trial_title TEXT,
                    sponsor TEXT,
                    ticker TEXT,
                    molecular_analysis JSON,
                    biostat_audit JSON,
                    financial_audit JSON,
                    consensus_verdict TEXT,
                    overall_score REAL,
                    scoring_audit_trail JSON,
                    executive_summary TEXT,
                    key_catalysts JSON,
                    critical_risks JSON,
                    created_at TEXT
                )
            """)

            # 4. Watchlist Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS catalyst_watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT UNIQUE NOT NULL,
                    item_type TEXT NOT NULL,
                    alias TEXT,
                    notes TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _run_migrations(self):
        """Adds missing columns dynamically for backward compatibility."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Clinical trials
            cursor.execute("PRAGMA table_info(clinical_trials)")
            ct_columns = [info["name"] for info in cursor.fetchall()]
            ct_missing = {
                "start_date_type": "TEXT",
                "primary_completion_date_type": "TEXT",
                "completion_date_type": "TEXT",
                "data_integrity_warnings": "TEXT"
            }
            for col, dtype in ct_missing.items():
                if col not in ct_columns:
                    try: cursor.execute(f"ALTER TABLE clinical_trials ADD COLUMN {col} {dtype}")
                    except Exception: pass
            
            # Company financials
            cursor.execute("PRAGMA table_info(company_financials)")
            fin_columns = [info["name"] for info in cursor.fetchall()]
            fin_missing = {
                "short_term_debt": "REAL",
                "data_freshness_warning": "TEXT"
            }
            for col, dtype in fin_missing.items():
                if col not in fin_columns:
                    try: cursor.execute(f"ALTER TABLE company_financials ADD COLUMN {col} {dtype}")
                    except Exception: pass
            
            # Diligence reports
            cursor.execute("PRAGMA table_info(diligence_reports)")
            dr_columns = [info["name"] for info in cursor.fetchall()]
            dr_missing = {
                "scoring_audit_trail": "JSON"
            }
            for col, dtype in dr_missing.items():
                if col not in dr_columns:
                    try: cursor.execute(f"ALTER TABLE diligence_reports ADD COLUMN {col} {dtype}")
                    except Exception: pass

            conn.commit()

    # --- Trial Operations ---

    def upsert_trial(self, trial: ClinicalTrial) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clinical_trials (
                    nct_id, title, official_title, sponsor_name, matched_ticker,
                    phases, status, conditions, interventions, primary_endpoints,
                    secondary_endpoints, enrollment, start_date, start_date_type, primary_completion_date,
                    primary_completion_date_type, completion_date, completion_date_type, brief_summary, detailed_description, allocation,
                    masking, estimated_catalyst_window, last_updated, data_integrity_warnings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(nct_id) DO UPDATE SET
                    title=excluded.title,
                    official_title=excluded.official_title,
                    sponsor_name=excluded.sponsor_name,
                    matched_ticker=COALESCE(excluded.matched_ticker, clinical_trials.matched_ticker),
                    phases=excluded.phases,
                    status=excluded.status,
                    conditions=excluded.conditions,
                    interventions=excluded.interventions,
                    primary_endpoints=excluded.primary_endpoints,
                    secondary_endpoints=excluded.secondary_endpoints,
                    enrollment=excluded.enrollment,
                    start_date=excluded.start_date,
                    start_date_type=excluded.start_date_type,
                    primary_completion_date=excluded.primary_completion_date,
                    primary_completion_date_type=excluded.primary_completion_date_type,
                    completion_date=excluded.completion_date,
                    completion_date_type=excluded.completion_date_type,
                    brief_summary=excluded.brief_summary,
                    detailed_description=excluded.detailed_description,
                    allocation=excluded.allocation,
                    masking=excluded.masking,
                    estimated_catalyst_window=excluded.estimated_catalyst_window,
                    last_updated=excluded.last_updated,
                    data_integrity_warnings=excluded.data_integrity_warnings
            """, (
                trial.nct_id,
                trial.title,
                trial.official_title,
                trial.sponsor_name,
                trial.matched_ticker,
                json.dumps(trial.phases),
                trial.status,
                json.dumps(trial.conditions),
                json.dumps([i.model_dump() for i in trial.interventions]),
                json.dumps([e.model_dump() for e in trial.primary_endpoints]),
                json.dumps([e.model_dump() for e in trial.secondary_endpoints]),
                trial.enrollment,
                trial.start_date,
                trial.start_date_type,
                trial.primary_completion_date,
                trial.primary_completion_date_type,
                trial.completion_date,
                trial.completion_date_type,
                trial.brief_summary,
                trial.detailed_description,
                trial.allocation,
                trial.masking,
                trial.estimated_catalyst_window,
                trial.last_updated,
                json.dumps(trial.data_integrity_warnings)
            ))
            conn.commit()

    def get_trial(self, nct_id: str) -> Optional[ClinicalTrial]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clinical_trials WHERE nct_id = ?", (nct_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_trial(row)

    def list_trials(self, limit: int = 100) -> List[ClinicalTrial]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clinical_trials ORDER BY indexed_at DESC LIMIT ?", (limit,))
            return [self._row_to_trial(row) for row in cursor.fetchall()]

    def count_trials(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clinical_trials")
            return cursor.fetchone()[0]

    def _row_to_trial(self, row: sqlite3.Row) -> ClinicalTrial:
        row_dict = dict(row)
        return ClinicalTrial(
            nct_id=row_dict["nct_id"],
            title=row_dict["title"],
            official_title=row_dict["official_title"],
            sponsor_name=row_dict["sponsor_name"],
            matched_ticker=row_dict["matched_ticker"],
            phases=json.loads(row_dict["phases"]) if row_dict["phases"] else [],
            status=row_dict["status"],
            conditions=json.loads(row_dict["conditions"]) if row_dict["conditions"] else [],
            interventions=[Intervention(**i) for i in (json.loads(row_dict["interventions"]) if row_dict["interventions"] else [])],
            primary_endpoints=[Endpoint(**e) for e in (json.loads(row_dict["primary_endpoints"]) if row_dict["primary_endpoints"] else [])],
            secondary_endpoints=[Endpoint(**e) for e in (json.loads(row_dict["secondary_endpoints"]) if row_dict["secondary_endpoints"] else [])],
            enrollment=row_dict["enrollment"],
            start_date=row_dict["start_date"],
            start_date_type=row_dict.get("start_date_type"),
            primary_completion_date=row_dict["primary_completion_date"],
            primary_completion_date_type=row_dict.get("primary_completion_date_type"),
            completion_date=row_dict["completion_date"],
            completion_date_type=row_dict.get("completion_date_type"),
            study_type=row_dict.get("study_type", "INTERVENTIONAL"),
            allocation=row_dict["allocation"],
            intervention_model=row_dict.get("intervention_model"),
            masking=row_dict["masking"],
            estimated_catalyst_window=row_dict["estimated_catalyst_window"],
            last_updated=row_dict["last_updated"],
            data_integrity_warnings=json.loads(row_dict["data_integrity_warnings"]) if row_dict.get("data_integrity_warnings") else []
        )

    # --- Financial Operations ---

    def upsert_financials(self, fin: CompanyFinancials) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO company_financials (
                    ticker, company_name, market_cap, stock_price, total_liquid_cash,
                    cash_and_equivalents, short_term_investments, quarterly_burn_rate,
                    cash_runway_months, dilution_risk_level, debt_to_equity, short_term_debt,
                    fifty_two_week_high, fifty_two_week_low, currency, data_freshness_warning, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    company_name=excluded.company_name,
                    market_cap=excluded.market_cap,
                    stock_price=excluded.stock_price,
                    total_liquid_cash=excluded.total_liquid_cash,
                    cash_and_equivalents=excluded.cash_and_equivalents,
                    short_term_investments=excluded.short_term_investments,
                    quarterly_burn_rate=excluded.quarterly_burn_rate,
                    cash_runway_months=excluded.cash_runway_months,
                    dilution_risk_level=excluded.dilution_risk_level,
                    debt_to_equity=excluded.debt_to_equity,
                    short_term_debt=excluded.short_term_debt,
                    fifty_two_week_high=excluded.fifty_two_week_high,
                    fifty_two_week_low=excluded.fifty_two_week_low,
                    fetched_at=excluded.fetched_at,
                    data_freshness_warning=excluded.data_freshness_warning,
                    currency=excluded.currency
            """, (
                fin.ticker, fin.company_name, fin.market_cap, fin.stock_price,
                fin.total_liquid_cash, fin.cash_and_equivalents, fin.short_term_investments,
                fin.quarterly_burn_rate, fin.cash_runway_months, fin.dilution_risk_level.value,
                fin.debt_to_equity, fin.short_term_debt, fin.fifty_two_week_high, fin.fifty_two_week_low,
                fin.currency, fin.data_freshness_warning, fin.fetched_at
            ))
            conn.commit()

    def get_financials(self, ticker: str, ttl_hours: Optional[int] = 24) -> Optional[CompanyFinancials]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM company_financials WHERE ticker = ?", (ticker,))
            row = cursor.fetchone()
            if not row:
                return None
            
            row_dict = dict(row)
            if ttl_hours is not None:
                fetched_at = datetime.fromisoformat(row_dict["fetched_at"].replace("Z", "+00:00"))
                from datetime import timezone
                age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
                if age_hours > ttl_hours:
                    return None
            
            return CompanyFinancials(
                ticker=row_dict["ticker"],
                company_name=row_dict["company_name"],
                market_cap=row_dict["market_cap"],
                stock_price=row_dict["stock_price"],
                total_liquid_cash=row_dict["total_liquid_cash"],
                cash_and_equivalents=row_dict["cash_and_equivalents"],
                short_term_investments=row_dict["short_term_investments"],
                quarterly_burn_rate=row_dict["quarterly_burn_rate"],
                cash_runway_months=row_dict["cash_runway_months"],
                dilution_risk_level=DilutionRiskLevel(row_dict["dilution_risk_level"]),
                debt_to_equity=row_dict["debt_to_equity"],
                short_term_debt=row_dict.get("short_term_debt"),
                fifty_two_week_high=row_dict["fifty_two_week_high"],
                fifty_two_week_low=row_dict["fifty_two_week_low"],
                currency=row_dict["currency"],
                data_freshness_warning=row_dict.get("data_freshness_warning"),
                fetched_at=row_dict["fetched_at"]
            )

    def list_all_financials(self) -> List[CompanyFinancials]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM company_financials ORDER BY market_cap DESC")
            records = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                records.append(CompanyFinancials(
                    ticker=row_dict["ticker"],
                    company_name=row_dict["company_name"],
                    market_cap=row_dict["market_cap"],
                    stock_price=row_dict["stock_price"],
                    total_liquid_cash=row_dict["total_liquid_cash"],
                    cash_and_equivalents=row_dict["cash_and_equivalents"],
                    short_term_investments=row_dict["short_term_investments"],
                    quarterly_burn_rate=row_dict["quarterly_burn_rate"],
                    cash_runway_months=row_dict["cash_runway_months"],
                    dilution_risk_level=DilutionRiskLevel(row_dict["dilution_risk_level"]),
                    debt_to_equity=row_dict["debt_to_equity"],
                    short_term_debt=row_dict.get("short_term_debt"),
                    fifty_two_week_high=row_dict["fifty_two_week_high"],
                    fifty_two_week_low=row_dict["fifty_two_week_low"],
                    currency=row_dict["currency"],
                    data_freshness_warning=row_dict.get("data_freshness_warning"),
                    fetched_at=row_dict["fetched_at"]
                ))
            return records

    # --- Reports Operations ---

    def save_report(self, report: DiligenceReport) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO diligence_reports (
                    nct_id, trial_title, sponsor, ticker, molecular_analysis,
                    biostat_audit, financial_audit, consensus_verdict, overall_score,
                    scoring_audit_trail, executive_summary, key_catalysts, critical_risks, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.nct_id, report.trial_title, report.sponsor, report.ticker,
                report.molecular_analysis.model_dump_json(),
                report.biostat_audit.model_dump_json(),
                report.financial_audit.model_dump_json(),
                report.consensus_verdict.value,
                report.overall_score,
                json.dumps(report.scoring_audit_trail),
                report.executive_summary,
                json.dumps(report.key_catalysts),
                json.dumps(report.critical_risks),
                report.created_at
            ))
            conn.commit()
            return cursor.lastrowid

    def get_latest_report_for_trial(self, nct_id: str) -> Optional[DiligenceReport]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM diligence_reports
                WHERE nct_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (nct_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_report(row)

    def _row_to_report(self, row: sqlite3.Row) -> DiligenceReport:
        row_dict = dict(row)
        return DiligenceReport(
            id=row_dict["id"],
            nct_id=row_dict["nct_id"],
            trial_title=row_dict["trial_title"],
            sponsor=row_dict["sponsor"],
            ticker=row_dict["ticker"],
            molecular_analysis=MolecularAnalysis.model_validate_json(row_dict["molecular_analysis"]),
            biostat_audit=BiostatAudit.model_validate_json(row_dict["biostat_audit"]),
            financial_audit=FinancialCatalystAudit.model_validate_json(row_dict["financial_audit"]),
            consensus_verdict=ConsensusVerdict(row_dict["consensus_verdict"]),
            overall_score=row_dict["overall_score"],
            scoring_audit_trail=json.loads(row_dict.get("scoring_audit_trail", "[]")) if row_dict.get("scoring_audit_trail") else [],
            executive_summary=row_dict["executive_summary"],
            key_catalysts=json.loads(row_dict["key_catalysts"]),
            critical_risks=json.loads(row_dict["critical_risks"]),
            created_at=row_dict["created_at"]
        )

    # --- Watchlist Operations ---

    def add_to_watchlist(self, identifier: str, item_type: str, alias: Optional[str] = None, notes: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO catalyst_watchlist (identifier, item_type, alias, notes)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(identifier) DO UPDATE SET
                        alias=excluded.alias,
                        notes=excluded.notes
                """, (identifier, item_type, alias, notes))
                conn.commit()
                return True
            except Exception:
                return False

    def get_watchlist(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM catalyst_watchlist ORDER BY added_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def remove_from_watchlist(self, identifier: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM catalyst_watchlist WHERE identifier = ?", (identifier,))
            rows = cursor.rowcount
            conn.commit()
            return rows > 0
