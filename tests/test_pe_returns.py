from datetime import date

import pytest

from src.pe_returns import (DealAssumptions, breakeven_club_value, exit_proceeds, holdco_debt,
                            returns, sources_and_uses, xirr)

A = DealAssumptions()


def test_sources_equal_uses():
    su = sources_and_uses(A)
    uses = su.loc[su["side"] == "Uses", "eur_m"].sum()
    sources = su.loc[su["side"] == "Sources", "eur_m"].sum()
    assert sources == pytest.approx(uses)
    assert A.entry_ltv == pytest.approx(0.83, abs=0.01)


def test_pik_accrues_at_8_75():
    one_year_later = date(2023, 4, 1)
    assert holdco_debt(A, one_year_later) - A.vendor_loan == pytest.approx(152.5 * 1.0875, rel=1e-3)


def test_xirr_simple_case():
    flows = [(date(2020, 1, 1), -100.0), (date(2022, 1, 1), 121.0)]
    assert xirr(flows) == pytest.approx(0.10, abs=1e-3)


def test_breakeven_and_limited_liability():
    maturity = date(2027, 4, 30)
    v = breakeven_club_value(A, maturity)
    assert returns(A, v, maturity)["moic"] == pytest.approx(1.0)
    assert exit_proceeds(A, 100.0, maturity) == 0.0      # equity cannot go below zero
