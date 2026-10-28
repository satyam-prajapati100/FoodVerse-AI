import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "5. Project Development Phase" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from routers.nutrition_scoring import calculate_health_score


def test_normal_meal():
    result = calculate_health_score(
        calories_kcal=480,
        protein_g=42,
        fiber_g=6,
        portion_weight_g=250,
    )
    assert result["health_score"] == 79
    assert result["health_label"] == "Healthy"


def test_zero_nutrients():
    result = calculate_health_score(
        calories_kcal=0,
        protein_g=0,
        fiber_g=0,
        portion_weight_g=250,
    )
    assert result["health_score"] == 30


def test_invalid_portion():
    try:
        calculate_health_score(
            calories_kcal=100,
            protein_g=5,
            fiber_g=2,
            portion_weight_g=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Zero portion weight should be rejected.")
