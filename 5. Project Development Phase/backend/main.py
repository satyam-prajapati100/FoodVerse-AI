
import os
import tempfile
from contextlib import asynccontextmanager
from database import Base, engine
import models  # Registers SQLAlchemy models with Base.metadata


from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from routers.food_recognition import router as food_router
from routers.nutrition import router as nutrition_router
from routers.nutrition_scoring import router as nutrition_scoring_router
from routers.database import router as database_router
from routers.freshness import router as freshness_router
from routers.hygiene_monitor import router as hygiene_router
from routers.kitchen_assistant import router as kitchen_router
from routers.meal_planner import router as meal_planner_router
from services.image_preprocessing import preprocess_food_image

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create missing tables; existing tables and their data are preserved.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="FoodVerse AI API",
    description="Backend API for the FoodVerse AI food intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
# Allow React frontend to communicate with FastAPI backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register existing API routers
app.include_router(food_router)
app.include_router(nutrition_router)
app.include_router(nutrition_scoring_router)
app.include_router(database_router)
app.include_router(freshness_router)
app.include_router(hygiene_router)
app.include_router(kitchen_router)
app.include_router(meal_planner_router)
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
