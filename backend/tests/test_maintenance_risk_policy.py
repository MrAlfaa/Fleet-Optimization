import pytest

from app.services.maintenance_risk_policy import (
    build_guarded_planning_window,
    classify_normalized_risk,
)


@pytest.mark.parametrize(
    ("p30", "p2000", "expected_level", "expected_ratio"),
    [
        (0.0, 0.0, "low", 0.0),
        (0.049, 0.0, "low", 0.49),
        (0.05, 0.0, "medium", 0.5),
        (0.099, 0.0, "medium", 0.99),
        (0.10, 0.0, "high", 1.0),
        (0.20, 0.0, "critical", 2.0),
        (0.01, 0.10, "critical", 2.0),
    ],
)
def test_classify_normalized_risk_uses_artifact_thresholds(
    p30: float,
    p2000: float,
    expected_level: str,
    expected_ratio: float,
) -> None:
    result = classify_normalized_risk(
        probability_30_days=p30,
        threshold_30_days=0.10,
        probability_2000_km=p2000,
        threshold_2000_km=0.05,
    )

    assert result["risk_level"] == expected_level
    assert result["normalized_risk"] == pytest.approx(expected_ratio)


def test_classify_normalized_risk_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="positive"):
        classify_normalized_risk(0.1, 0.0, 0.1, 0.05)


def test_low_risk_withholds_raw_aft_estimates() -> None:
    result = build_guarded_planning_window(
        risk_level="low",
        raw_days=300.0,
        raw_km=30_000.0,
        planning_intervals={
            "days": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
            "km": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
        },
    )

    assert result == {
        "planning_status": "no_near_term_failure_indicated",
        "planning_window": None,
    }


def test_high_risk_returns_capped_interval_without_raw_values() -> None:
    result = build_guarded_planning_window(
        risk_level="high",
        raw_days=2_000.0,
        raw_km=300_000.0,
        planning_intervals={
            "days": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
            "km": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
        },
    )

    assert result["planning_status"] == "planning_window_available"
    assert result["planning_window"] == {
        "days": {"lower": 1_000, "upper": 1_825},
        "km": {"lower": 150_000, "upper": 250_000},
    }


@pytest.mark.parametrize("raw_days,raw_km", [(float("nan"), 10), (10, -1), (None, 10)])
def test_invalid_aft_estimate_is_withheld(raw_days: float | None, raw_km: float | None) -> None:
    result = build_guarded_planning_window(
        risk_level="critical",
        raw_days=raw_days,
        raw_km=raw_km,
        planning_intervals={
            "days": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
            "km": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
        },
    )

    assert result == {"planning_status": "estimate_withheld", "planning_window": None}
