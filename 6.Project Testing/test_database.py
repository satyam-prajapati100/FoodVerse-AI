import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "5. Project Development Phase" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal
from models import MealAnalysis


def test_database():
    db = SessionLocal()
    meal_id = None

    try:
        meal = MealAnalysis(
            dish_name="Test roasted chicken meal",
            portion_weight_g=250,
            calories_kcal=480,
            protein_g=42,
            carbs_g=35,
            fat_g=18,
            fiber_g=6,
            health_score=79,
            health_label="Healthy",
        )

        db.add(meal)
        db.commit()
        db.refresh(meal)
        meal_id = meal.id

        print("Record saved successfully!")
        print("Generated ID:", meal.id)

        saved_meal = db.get(MealAnalysis, meal_id)

        print("\nRetrieved record:")
        print("Dish:", saved_meal.dish_name)
        print("Calories:", saved_meal.calories_kcal)
        print("Protein:", saved_meal.protein_g)
        print("Health score:", saved_meal.health_score)
        print("Health label:", saved_meal.health_label)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    test_database()
