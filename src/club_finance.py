"""
Small toolkit for reading a football club's accounts.

The question behind the project is how much of Atalanta's profit comes from
selling players. In Italian GAAP (OIC) a gain on a player's registration
("plusvalenza") sits inside the value of production, so it inflates EBITDA and
EBIT exactly like ticket or TV revenue. The functions below take it out again.

    gain on disposal = sale price - net book value of the registration
    net book value   = purchase cost - accumulated amortisation

All amounts in EUR millions.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def trading_share(revenue: pd.Series, gains: pd.Series) -> pd.Series:
    """Share of total revenue that comes from gains on player disposals."""
    return gains / revenue


def cagr(first: float, last: float, years: float) -> float:
    """Compound annual growth rate between two values `years` apart."""
    if first <= 0 or years <= 0:
        raise ValueError("first value and number of years must be positive")
    return (last / first) ** (1 / years) - 1


def book_value(cost: float, contract_years: int, years_held: float) -> float:
    """Net book value of a registration amortised on a straight line over the contract.

    Contract renewals reset the schedule in practice; here the caller can pass
    the residual cost and the new contract length to model that.
    """
    if contract_years <= 0:
        raise ValueError("contract_years must be positive")
    used = min(max(years_held, 0.0), contract_years)
    return cost * (1 - used / contract_years)


def disposal_gain(price: float, net_book_value: float) -> float:
    """Plusvalenza: what the buyer pays above the carrying amount."""
    return price - net_book_value


@dataclass(frozen=True)
class Bridge:
    structural_revenue: float
    player_trading: float
    operating_costs: float          # cash costs: personnel, services, other
    depreciation_amortisation: float
    net_profit: float

    @property
    def ebitda_ex_trading(self) -> float:
        return self.structural_revenue - self.operating_costs

    @property
    def ebitda(self) -> float:
        return self.ebitda_ex_trading + self.player_trading

    @property
    def ebit(self) -> float:
        return self.ebitda - self.depreciation_amortisation

    @property
    def ebit_ex_trading(self) -> float:
        """Operating result if the club had sold nobody: D&A stays, the gains go."""
        return self.ebitda_ex_trading - self.depreciation_amortisation

    @property
    def financial_items_and_tax(self) -> float:
        return self.net_profit - self.ebit

    def as_series(self) -> pd.Series:
        return pd.Series({
            "Structural revenue": self.structural_revenue,
            "Operating costs": -self.operating_costs,
            "EBITDA ex trading": self.ebitda_ex_trading,
            "Player trading": self.player_trading,
            "EBITDA": self.ebitda,
            "D&A": -self.depreciation_amortisation,
            "EBIT": self.ebit,
            "Financial items and tax": self.financial_items_and_tax,
            "Net profit": self.net_profit,
        })


def bridge_from_pnl(pnl: pd.DataFrame, column: str) -> Bridge:
    """Build the profit bridge from the P&L table in data/pnl_2024_25.csv.

    Operating costs are taken as reported total costs minus D&A, so the
    rounding of the single cost lines does not leak into the result.
    """
    v = pnl.set_index("item")[column]
    revenue = pnl.loc[pnl["section"] == "revenue", column].sum()
    trading = v["Player trading (gains on disposals and loan fees)"]
    da = v["Depreciation and amortisation"]
    return Bridge(
        structural_revenue=revenue - trading,
        player_trading=trading,
        operating_costs=v["Total costs (as reported; items above are rounded)"] - da,
        depreciation_amortisation=da,
        net_profit=v["Net profit"],
    )


def retained_earnings_share(equity_start: float, equity_end: float, profits: float) -> float:
    """How much of the growth in equity is explained by profits kept in the club."""
    growth = equity_end - equity_start
    if growth == 0:
        raise ValueError("equity did not change")
    return profits / growth
