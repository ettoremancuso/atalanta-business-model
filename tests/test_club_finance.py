from pathlib import Path

import pandas as pd
import pytest

from src.club_finance import (bridge_from_pnl, book_value, cagr, disposal_gain,
                              retained_earnings_share, trading_share)

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def periods():
    return pd.read_csv(DATA / "financials_by_period.csv")


def test_totals_match_the_report(periods):
    # headline numbers quoted in the paper and in the report
    assert periods["net_profit_eur_m"].sum() == pytest.approx(230.5, abs=0.1)
    assert periods["player_trading_gains_eur_m"].sum() == pytest.approx(534, abs=0.5)
    assert (periods["net_profit_eur_m"] > 0).all()


def test_trading_share_is_about_a_quarter(periods):
    total = trading_share(periods["revenue_eur_m"].sum(), periods["player_trading_gains_eur_m"].sum())
    assert total == pytest.approx(0.275, abs=0.002)


def test_bridge_2024_25():
    pnl = pd.read_csv(DATA / "pnl_2024_25.csv")
    b = bridge_from_pnl(pnl, "fy_2024_25_eur_m")
    assert b.structural_revenue == pytest.approx(199.2, abs=0.05)
    assert b.ebitda == pytest.approx(135.8, abs=0.15)
    assert b.ebit == pytest.approx(59.1, abs=0.15)
    assert b.ebit_ex_trading < -60          # the core finding: negative without sales
    assert b.as_series()["Net profit"] == pytest.approx(37.8)


def test_koopmeiners_example():
    # bought from AZ for 14.0 in 2021, book value about 6.2 after the renewal, sold for 51.3.
    # Price minus book value gives about 45.1; the accounts show 44.5 because of
    # ancillary costs and the 10% sell-on clause owed to AZ.
    assert disposal_gain(51.3, 6.2) == pytest.approx(45.1)
    assert book_value(10, 5, 2) == pytest.approx(6.0)
    assert book_value(10, 5, 9) == 0.0


def test_cagr_and_equity():
    assert cagr(83.1, 320.8, 8.5) == pytest.approx(0.172, abs=0.002)
    assert retained_earnings_share(77.8, 248.2, 153.0) == pytest.approx(0.90, abs=0.01)
    with pytest.raises(ValueError):
        cagr(0, 1, 1)
