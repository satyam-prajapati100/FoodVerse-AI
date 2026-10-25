
import os
import tempfile


from fastapi import FastAPI, File, HTTPException, UploadFile

from routers.food_recognition import router as food_router
from routers.nutrition import router as nutrition_router
from routers.nutrition_scoring import router as nutrition_scoring_router
from routers.database import router as database_router
from routers.freshness import router as freshness_router
from services.image_preprocessing import preprocess_food_image

app = FastAPI(
    title="FoodVerse AI API",
    description="Backend API for the FoodVerse AI food intelligence platform",
    version="0.1.0",
)

# Register existing API routers
app.include_router(food_router)
app.include_router(nutrition_router)
app.include_router(nutrition_scoring_router)
app.include_router(database_router)
app.include_router(freshness_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to FoodVerse AI!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": "FoodVerse AI",
    }


@app.post("/image/preprocess", tags=["Image Preprocessing"])
async def preprocess_uploaded_image(file: UploadFile = File(...)):
    """Preprocess an uploaded image and return its visual features."""

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload an image file.",
        )

    temp_path = None

    try:
        image_bytes = await file.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded image is empty.",
            )

        suffix = os.path.splitext(file.filename or "")[1]

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_file.write(image_bytes)
            temp_path = temp_file.name

        processed_image, features = preprocess_food_image(temp_path)

        return {
            "success": True,
            "filename": file.filename,
            "processed_image": {
                "width": int(processed_image.shape[1]),
                "height": int(processed_image.shape[0]),
                "channels": int(processed_image.shape[2]),
                "normalized_pixel_range": [
                    float(processed_image.min()),
                    float(processed_image.max()),
                ],
            },
            "features": features,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        await file.close()
