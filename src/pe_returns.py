"""
A simple returns model for the 2022 Pagliuca deal, seen from the American investors' side.

The structure is a holding-company buyout: the investors' vehicle (Athena S.p.A.)
borrowed most of the price with a PIK toggle bond and a vendor loan, and owns a
stake in La Dea H, the Percassi holding that controls the club. The club itself
carries no acquisition debt, so the equity of the vehicle is

    value of the look-through stake in the club - PIK bond (with accrued interest) - vendor loan

Every input below is a public figure or an explicit assumption; see the
`DealAssumptions` defaults and the paper (section 9) for sources. This is an
illustration of how leverage and PIK interest shape the returns, not a
valuation of the club.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def year_fraction(start: date, end: date) -> float:
    return (end - start).days / 365.25


def xirr(cash_flows: list[tuple[date, float]]) -> float:
    """Annual IRR for dated cash flows (negative = money in, positive = money out)."""
    t0 = cash_flows[0][0]

    def npv(rate: float) -> float:
        return sum(cf / (1 + rate) ** year_fraction(t0, d) for d, cf in cash_flows)

    return brentq(npv, -0.9999, 100.0)


@dataclass(frozen=True)
class DealAssumptions:
    entry_date: date = date(2022, 4, 1)          # closing and bond issue, spring 2022
    club_value_entry: float = 450.0              # EUR m for 100% of the club (press range 400-500)
    stake_entry: float = 0.47                    # 55% of La Dea H = about 47% of the club
    stake_after_follow_on: float = 0.47 * 62 / 55   # 62% of La Dea H after January 2025
    bond: float = 152.5                          # Athena S.p.A. PIK toggle bond
    pik_rate: float = 0.0875                     # assume interest is always paid in kind
    vendor_loan: float = 23.0                    # from the Percassi family; assumed bullet, no interest
    follow_on_date: date = date(2025, 1, 15)
    follow_on_equity: float = 67.0               # US share of the EUR 72m capital increase
    sources: dict = field(default_factory=lambda: {
        "bond": "BeBeez (2022); InvestireOggi",
        "vendor_loan": "Calcio e Finanza (2023)",
        "club_value_entry": "Il Foglio (2022); press range EUR 400-500m",
        "follow_on_equity": "Calcio e Finanza (2025)",
    })

    @property
    def entry_price(self) -> float:
        return self.stake_entry * self.club_value_entry

    @property
    def entry_equity(self) -> float:
        """Equity cheque at entry = price - acquisition debt (includes Arctos's minority ticket)."""
        return self.entry_price - self.bond - self.vendor_loan

    @property
    def entry_ltv(self) -> float:
        return (self.bond + self.vendor_loan) / self.entry_price


def sources_and_uses(a: DealAssumptions) -> pd.DataFrame:
    rows = [
        ("Uses", f"{a.stake_entry:.0%} look-through stake in the club", a.entry_price),
        ("Sources", "PIK toggle bond (Athena S.p.A.)", a.bond),
        ("Sources", "Vendor loan (Percassi family)", a.vendor_loan),
        ("Sources", "Equity (US investors and Arctos)", a.entry_equity),
    ]
    df = pd.DataFrame(rows, columns=["side", "item", "eur_m"])
    df["share_of_price"] = df["eur_m"] / a.entry_price
    return df


def holdco_debt(a: DealAssumptions, when: date) -> float:
    """PIK bond with interest added to principal (annual compounding, pro rata for part years) plus vendor loan."""
    return a.bond * (1 + a.pik_rate) ** year_fraction(a.entry_date, when) + a.vendor_loan


def exit_proceeds(a: DealAssumptions, club_value: float, when: date) -> float:
    """What the vehicle's equity gets at exit. Limited liability: never below zero."""
    return max(a.stake_after_follow_on * club_value - holdco_debt(a, when), 0.0)


def returns(a: DealAssumptions, club_value: float, when: date) -> dict[str, float]:
    invested = a.entry_equity + a.follow_on_equity
    proceeds = exit_proceeds(a, club_value, when)
    flows = [(a.entry_date, -a.entry_equity), (a.follow_on_date, -a.follow_on_equity), (when, proceeds)]
    irr = xirr(flows) if proceeds > 0 else -1.0
    return {"moic": proceeds / invested, "irr": irr, "ltv": holdco_debt(a, when) / (a.stake_after_follow_on * club_value)}


def breakeven_club_value(a: DealAssumptions, when: date, moic: float = 1.0) -> float:
    """Club value at which the vehicle's equity gets back `moic` times what it put in."""
    invested = a.entry_equity + a.follow_on_equity
    return (holdco_debt(a, when) + moic * invested) / a.stake_after_follow_on


def sensitivity(a: DealAssumptions, revenue: float, multiples, exit_dates) -> pd.DataFrame:
    """MOIC and IRR for exit at EV/revenue multiples (rows: exit dates, columns: multiples)."""
    out = []
    for d in exit_dates:
        for m in multiples:
            r = returns(a, m * revenue, d)
            out.append({"exit": d, "multiple": m, "club_value": m * revenue, **r})
    return pd.DataFrame(out)
