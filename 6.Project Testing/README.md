# FoodVerse AI — Functional Testing Report

## 1. Overview

This folder contains automated tests and validation records for the FoodVerse AI backend. The tests cover basic API availability, image preprocessing, database functionality, and nutrition scoring.

## 2. Testing Environment

- **Operating system:** Windows
- **Python:** 3.12.4
- **Testing framework:** pytest 9.2.0
- **API framework:** FastAPI
- **Test client:** FastAPI TestClient

## 3. Automated Test Results

**Latest confirmed run:** 11 tests passed in 2.50 seconds.

| Test file | Coverage | Result |
|---|---|---|
| `test_api.py` | Root, health, OpenAPI, unknown route, image preprocessing and invalid uploads | 7 passed |
| `test_database.py` | Database test | 1 passed |
| `test_nutrition_scoring.py` | Normal meal, zero nutrients and invalid portion | 3 passed |
| **Total** | | **11 passed** |

## 4. Functional Testing

The following API modules have been manually exercised through Swagger UI (`/docs`):

- Food recognition
- Nutrition scoring and estimation
- Food freshness assessment
- Hygiene monitoring
- Recipe generation
- Personalized meal planning
- Image preprocessing
- Database operations

Manual endpoint checks and automated pytest results are recorded separately because they verify different aspects of the application.

## 5. Edge Cases

Automated tests currently cover:

- Unknown API endpoint
- Non-image content type
- Empty image upload
- Zero portion weight
- Zero-valued nutrients

Additional validation should cover unrealistic meal-planner measurements, missing fields, malformed requests, and invalid inputs for other endpoints.

## 6. Known Limitations

- Food recognition and nutrition estimates can be inaccurate, especially when portion sizes are uncertain.
- Visual freshness assessment cannot detect all pathogens or invisible spoilage.
- Image-based hygiene monitoring is not a certified food-safety inspection.
- Recipe and meal-plan outputs should be treated as educational suggestions, not medical advice.
- A passing automated test suite does not guarantee that every feature works correctly in all conditions.

## 7. Run the Tests

Activate the backend virtual environment, navigate to the backend folder, and execute:

```powershell
python -m pytest "..\..\6.Project Testing" -v
```

## 8. Final Status

The latest confirmed automated test run passed all 11 tests. Complete the remaining edge-case tests and verify their results before declaring functional and edge-case validation fully complete.

