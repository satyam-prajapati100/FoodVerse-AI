
import base64
import json
import logging
import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from groq import Groq
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models import MealAnalysis
from routers.nutrition_scoring import calculate_health_score

router = APIRouter(prefix="/nutrition", tags=["Nutrition Estimation"])
logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000

load_dotenv(
    dotenv_path=Path(__file__).resolve().parents[1] / ".env"
)

GROQ_MODEL_NAME = "qwen/qwen3.8-27b"


def get_groq_client():
    """Create a Groq client using the key stored in backend/.env."""
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing from the backend .env file.",
        )

    return Groq(api_key=api_key)


def validate_and_encode_image(image_bytes: bytes) -> str:
    """Validate the uploaded image and return a base64 JPEG string."""
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image must be 10 MB or smaller.",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = image.format

            if image_format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(
                    status_code=415,
                    detail="Upload a JPEG, PNG, or WEBP image.",
                )

            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail="Image dimensions are too large.",
                )

            image.load()
            image = image.convert("RGB")

            output = BytesIO()
            image.save(output, format="JPEG", quality=90)

            return base64.b64encode(output.getvalue()).decode("utf-8")

    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        )


def parse_model_json(content: str) -> dict:
    """Parse JSON returned by the vision model."""
    content = content.strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3].strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="The nutrition model returned invalid JSON. Please try again.",
        )

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail="The nutrition model returned an unexpected response.",
        )

    return result


@router.post("/estimate")
async def estimate_nutrition(
    image: UploadFile = File(...),
    portion_weight_g: float | None = Form(default=None, gt=0, le=5000),
    prompt_context: str = Form(default=""),
):
    """
    Estimate nutrition from a food image.

    Portion weight and context are optional. Without a reliable portion size,
    nutrition values may be particularly uncertain.
    """
    image_bytes = await image.read()
    image_base64 = validate_and_encode_image(image_bytes)

    context = prompt_context.strip()[:1000]
    portion_text = (
        f"User-provided serving weight: {portion_weight_g} grams."
        if portion_weight_g is not None
        else "Serving weight was not provided. Do not pretend it is known."
    )

    system_prompt = """
You are a food-image analysis assistant for the FoodVerse AI student project.

Return exactly one valid JSON object, without Markdown or extra text.

First determine whether the image shows food or a drink.
If it does not, return exactly:
{"error":"NOT_FOOD"}

For food or drinks, return this structure:
{
  "dish_name": "identified food or meal",
  "calories": 0,
  "protein": 0,
  "carbs": 0,
  "fats": 0,
  "fiber": 0,
  "sugar": 0,
  "health_score": 0,
  "health_label": "Moderate",
  "reasoning": "brief explanation",
  "alternatives": ["alternative suggestion"],
  "estimation_notes": ["uncertainty or assumption"]
}

Rules:
- Nutrient values are estimates for the stated serving, in kcal and grams.
- If serving size or ingredients are uncertain, say so in estimation_notes.
- Use the supplied serving weight if present; otherwise estimate a plausible
  serving cautiously and explicitly state that the portion is assumed.
- Nutrition values must be non-negative numbers.
- health_score must be an integer from 0 to 100.
- health_label must be Healthy, Moderate, or Unhealthy.
- Base the score on visible nutritional balance, not medical diagnosis.
- Do not claim an image proves food is safe, fresh, or spoiled.
- Do not invent exact ingredients that cannot be identified visually.
- If uncertain, lower certainty in the reasoning and explain limitations.
- If the image is not food or drink, return only {"error":"NOT_FOOD"}.
"""

    user_prompt = (
        f"{portion_text}\n"
        f"Additional user context: {context or 'None provided.'}\n"
        "Analyze this image and return the required JSON."
    )

    try:
        response = get_groq_client().chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    "data:image/jpeg;base64,"
                                    f"{image_base64}"
                                )
                            },
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_completion_tokens=1200,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Groq nutrition estimation request failed.")
        raise HTTPException(
            status_code=502,
            detail="Nutrition estimation failed. Check the server log and try again.",
        )

    content = response.choices[0].message.content or ""
    result = parse_model_json(content)

    if result.get("error") == "NOT_FOOD":
        raise HTTPException(
            status_code=422,
            detail="The image does not appear to contain food or a drink.",
        )

    required_fields = [
        "dish_name",
        "calories",
        "protein",
        "carbs",
        "fats",
        "fiber",
        "sugar",
        "health_score",
        "health_label",
        "reasoning",
        "alternatives",
        "estimation_notes",
    ]

    missing_fields = [
        field for field in required_fields if field not in result
    ]

    if missing_fields:
        raise HTTPException(
            status_code=502,
            detail="The model response is missing required nutrition fields.",
        )

    numeric_fields = [
        "calories",
        "protein",
        "carbs",
        "fats",
        "fiber",
        "sugar",
        "health_score",
    ]

    for field in numeric_fields:
        value = result[field]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
        ):
            raise HTTPException(
                status_code=502,
                detail=f"The model returned an invalid value for {field}.",
            )

    if result["health_score"] > 100:
        raise HTTPException(
            status_code=502,
            detail="The model returned a health score outside 0–100.",
        )

    if result["health_label"] not in {"Healthy", "Moderate", "Unhealthy"}:
        raise HTTPException(
            status_code=502,
            detail="The model returned an invalid health label.",
        )

    for field in ["alternatives", "estimation_notes"]:
        if not isinstance(result[field], list):
            raise HTTPException(
                status_code=502,
                detail=f"The model returned an invalid {field} field.",
            )

    
    # Calculate the score using our Python rules.
    # If the user didn't provide a portion weight, the result is only
    # a rough estimate because the model's assumed serving size is unknown.
    scoring_weight = portion_weight_g

    if scoring_weight is None:
        notes = result["estimation_notes"]
        notes.append(
            "No serving weight was provided. The health score uses an "
            "assumed 250 g portion and may be misleading."
        )
        scoring_weight = 250.0

    scoring = calculate_health_score(
        calories_kcal=result["calories"],
        protein_g=result["protein"],
        fiber_g=result["fiber"],
        portion_weight_g=scoring_weight,
    )

    return {
        "success": True,
        "model": GROQ_MODEL_NAME,
        "portion_weight_g": portion_weight_g,
        "nutrition": {
            "dish_name": result["dish_name"],
            "calories_kcal": result["calories"],
            "protein_g": result["protein"],
            "carbs_g": result["carbs"],
            "fats_g": result["fats"],
            "fiber_g": result["fiber"],
            "sugar_g": result["sugar"],
        },
        "health_score": scoring["health_score"],
        "health_label": scoring["health_label"],
        "scoring_components": scoring["components"],
        "reasoning": scoring["reasoning"],
        "alternatives": result["alternatives"],
        "estimation_notes": result["estimation_notes"],
        "message": (
            "AI-generated nutrition estimates only. The score is a "
            "simplified project heuristic, not a clinical assessment."
        ),
    }


@router.post("/estimate-and-save")
async def estimate_nutrition_and_save(
    image: UploadFile = File(...),
    portion_weight_g: float | None = Form(default=None, gt=0, le=5000),
    prompt_context: str = Form(default=""),
):
    """Estimate nutrition from an image and save the result in MySQL."""

    # Reuse the existing estimator; do not call the AI model a second time.
    try:
        result = await estimate_nutrition(
            image=image,
            portion_weight_g=portion_weight_g,
            prompt_context=prompt_context,
        )

        nutrition = result["nutrition"]

        # If the user omitted the weight, 250 g is only an assumption.
        saved_weight = (
            portion_weight_g if portion_weight_g is not None else 250.0
        )

        db = SessionLocal()

        try:
            record = MealAnalysis(
                dish_name=nutrition["dish_name"],
                portion_weight_g=saved_weight,
                calories_kcal=nutrition["calories_kcal"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fats_g"],
                fiber_g=nutrition["fiber_g"],
                health_score=result["health_score"],
                health_label=result["health_label"],
            )

            db.add(record)
            db.commit()
            db.refresh(record)

            return {
                "success": True,
                "message": "Nutrition analysis saved to MySQL.",
                "saved_record": {
                    "id": record.id,
                    "dish_name": record.dish_name,
                    "portion_weight_g": record.portion_weight_g,
                    "calories_kcal": record.calories_kcal,
                    "protein_g": record.protein_g,
                    "carbs_g": record.carbs_g,
                    "fat_g": record.fat_g,
                    "fiber_g": record.fiber_g,
                    "health_score": record.health_score,
                    "health_label": record.health_label,
                    "created_at": (
                        record.created_at.isoformat()
                        if record.created_at
                        else None
                    ),
                },
                "estimation_notes": result["estimation_notes"],
                "model": result["model"],
            }

        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Failed to save nutrition analysis to MySQL.")
            raise HTTPException(
                status_code=500,
                detail="Nutrition was estimated, but saving to MySQL failed.",
            ) from exc

        finally:
            db.close()

    finally:
        await image.close()

