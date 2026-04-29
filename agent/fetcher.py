"""
fetcher.py
----------
Loads mock data from Bullhorn ATS and Business Central JSON files,
cross-references them to detect anomalies (billing gaps, AR issues, etc.),
and returns a single unified context dict for the synthesizer.
"""

import json
import os
from pathlib import Path

BASE = Path(__file__).parent.parent / "mock_data"

def _load(path: str) -> dict | list:
    with open(BASE / path, encoding="utf-8") as f:
        return json.load(f)


def fetch_bullhorn_data() -> dict:
    return {
        "clients":     _load("bullhorn/clients.json"),
        "placements":  _load("bullhorn/placements.json"),
        "job_orders":  _load("bullhorn/job_orders.json"),
        "submissions": _load("bullhorn/submissions.json"),
        "candidates":  _load("bullhorn/candidates.json"),
    }


def fetch_bc_data() -> dict:
    return {
        "invoices":  _load("business_central/invoices.json"),
        "customers": _load("business_central/customers.json"),
        "payments":  _load("business_central/payments.json"),
    }


def _detect_billing_gaps(bh: dict, bc: dict) -> list:
    """Cross-reference Bullhorn placements vs BC invoices to find unbilled work."""
    return bh["placements"].get("billingGaps", [])


def _flag_job_orders(job_orders: list) -> dict:
    aged_critical   = [j for j in job_orders if j.get("flag") == "AGED_CRITICAL"]
    aged_watch      = [j for j in job_orders if j.get("flag") == "AGED_WATCH"]
    no_activity     = [j for j in job_orders if j.get("flag") == "NO_ACTIVITY"]
    return {
        "aged_critical": aged_critical,
        "aged_watch":    aged_watch,
        "no_activity":   no_activity,
    }


def _flag_recruiters(week1: list, week2: list) -> list:
    flagged = []
    w1_map = {r["recruiter"]: r for r in week1}
    for r in week2:
        name = r["recruiter"]
        flag = r.get("flag")
        if flag in ("UNDERPERFORMING", "STALLED"):
            w1 = w1_map.get(name, {})
            flagged.append({
                "recruiter":      name,
                "flag":           flag,
                "week2Placements": r["placements"],
                "week1Placements": w1.get("placements", 0),
                "note":           r.get("note", ""),
            })
    return flagged


def build_context() -> dict:
    """
    Master function: loads all data, computes derived KPIs,
    and returns a single context dict consumed by synthesizer.
    """
    bh = fetch_bullhorn_data()
    bc = fetch_bc_data()

    jobs_list = bh["job_orders"]["orders"]
    job_flags = _flag_job_orders(jobs_list)

    w1_recruiters = bh["submissions"]["week1"]["byRecruiter"]
    w2_recruiters = bh["submissions"]["week2"]["byRecruiter"]
    recruiter_flags = _flag_recruiters(w1_recruiters, w2_recruiters)

    billing_gaps = _detect_billing_gaps(bh, bc)
    total_unbilled = sum(g["estimatedUnbilled"] for g in billing_gaps)

    flagged_invoices = bc["invoices"]["flaggedInvoices"]
    ar_aging         = bc["invoices"]["arAging"]

    placements_summary = bh["placements"]["summary"]
    upcoming_ends      = bh["placements"]["upcomingEnds"]

    submissions_w1  = bh["submissions"]["week1"]
    submissions_w2  = bh["submissions"]["week2"]
    wow             = bh["submissions"]["weekOverWeekSummary"]
    dallas_trend    = bh["submissions"]["dallasTeamFillRate"]

    fin_summary     = bc["invoices"]["summary"]
    fin_kpis        = bc["invoices"]["monthToDateKPIs"]
    weekly_trend    = bc["invoices"]["weeklyRevenueTrend"]

    context = {
        # ── OPERATIONAL ──────────────────────────────────────────
        "activePlacements":           placements_summary["totalActivePlacements"],
        "weeklyBillableHours":        placements_summary["weeklyBillableHours"],
        "projectedWeeklyRevenue":     placements_summary["projectedWeeklyRevenue"],
        "avgBillRate":                placements_summary["avgBillRate"],
        "avgMarginPct":               placements_summary["avgMarginPct"],

        # ── SUBMISSIONS & PIPELINE ───────────────────────────────
        "week1": {
            "submissions":  submissions_w1["totalSubmissions"],
            "interviews":   submissions_w1["totalInterviews"],
            "offers":       submissions_w1["totalOffers"],
            "placements":   submissions_w1["totalPlacements"],
            "fillRate":     submissions_w1["fillRate"],
            "timeToFill":   submissions_w1["avgTimeToFillDays"],
        },
        "week2": {
            "submissions":  submissions_w2["totalSubmissions"],
            "interviews":   submissions_w2["totalInterviews"],
            "offers":       submissions_w2["totalOffers"],
            "placements":   submissions_w2["totalPlacements"],
            "fillRate":     submissions_w2["fillRate"],
            "timeToFill":   submissions_w2["avgTimeToFillDays"],
        },
        "wowTrend":     wow["trend"],
        "wowNote":      wow["note"],

        # ── JOB ORDERS ───────────────────────────────────────────
        "totalOpenJobOrders":         bh["job_orders"]["summary"]["totalOpen"],
        "agedCriticalOrders":         job_flags["aged_critical"],
        "agedWatchOrders":            job_flags["aged_watch"],
        "stalledOrders":              job_flags["no_activity"],

        # ── RECRUITERS ───────────────────────────────────────────
        "flaggedRecruiters":          recruiter_flags,
        "topRecruiters":              sorted(w2_recruiters, key=lambda r: r["placements"], reverse=True)[:3],
        "dallasTeamFillRateWk1":      dallas_trend["week1"]["fillRate"],
        "dallasTeamFillRateWk2":      dallas_trend["week2"]["fillRate"],
        "dallasWoWChange":            dallas_trend["changeWoW"],

        # ── BILLING GAPS ─────────────────────────────────────────
        "billingGaps":                billing_gaps,
        "totalUnbilledEstimate":      total_unbilled,

        # ── FINANCIAL ────────────────────────────────────────────
        "monthlyRevenue":             fin_summary["totalValueRaised"],
        "monthlyTarget":              fin_summary["monthlyRevenueTarget"],
        "monthlyAttainmentPct":       fin_summary["monthlyRevenueAttainmentPct"],
        "weeklyRunRate":              fin_summary["weeklyRunRate"],
        "weeklyRunRateTarget":        fin_summary["weeklyRunRateTarget"],
        "grossMarginPct":             fin_kpis["grossMarginPct"],
        "grossMarginTarget":          fin_kpis["grossMarginTarget"],
        "dsoDays":                    fin_kpis["dso"],
        "dsoTarget":                  fin_kpis["dsoTarget"],
        "totalAR":                    ar_aging["total"]["amount"],
        "ar_61_90":                   ar_aging["overdue_61_90"]["amount"],
        "ar_90plus":                  ar_aging["overdue_90plus"]["amount"],
        "flaggedInvoices":            flagged_invoices,

        # ── UPCOMING PLACEMENT ENDS ──────────────────────────────
        "upcomingEnds":               upcoming_ends,

        # ── WEEKLY REVENUE TREND ─────────────────────────────────
        "weeklyRevenueTrend":         weekly_trend,
    }

    return context
