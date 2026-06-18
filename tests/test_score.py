from atlas.intelligence.score import compute_atlas_score


def test_atlas_score_range():
    score = compute_atlas_score(
        max_drawdown_pct=0.10,
        profit_factor=1.8,
        expectancy_pct=0.012,
        sharpe=1.2,
        net_profit_pct=0.25,
        total_trades=80,
    )
    assert 0 <= score <= 100


def test_atlas_score_rejects_bad_metrics():
    score = compute_atlas_score(
        max_drawdown_pct=0.40,
        profit_factor=0.5,
        expectancy_pct=-0.005,
        sharpe=-0.5,
        net_profit_pct=-0.20,
        total_trades=5,
    )
    assert score < 50
