
import json
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from routers.food_recognition import (
    GROQ_MODEL_NAME,
    _call_groq_vision,
    _read_uploaded_image,
)

router = APIRouter(
    prefix="/freshness",
    tags=["Food Freshness Assessment"],
)

logger = logging.getLogger(__name__)

FRESHNESS_PROMPT = """
You assess the apparent freshness of food from a photograph
for a student food-intelligence project.

Return exactly one valid JSON object, without Markdown fences:
{
  "food_name": "identified food or unknown",
  "apparent_freshness": "Fresh",
  "visible_evidence": ["visible observation"],
  "concerns": [],
  "recommendations": ["practical recommendation"],
  "limitations": ["uncertainty or limitation"]
}

Rules:
- apparent_freshness must be exactly one of:
  "Fresh", "Moderately Fresh", "Possibly Spoiled", "Inconclusive".
- Describe only visible evidence, such as discoloration,
  visible mold, wilting, bruising, or unusual surface changes.
- Do not claim that invisible microorganisms are detected.
- Do not claim that food is safe to eat based on an image.
- Do not infer storage temperature, age, smell, or handling history.
- If evidence is insufficient, use "Inconclusive".
- If visible mold or serious spoilage signs appear, advise not to
  taste the food and recommend discarding it.
- For uncertain cases, recommend checking storage history and
  reliable food-safety guidance.
- Every list field must be a list of strings.
- Return JSON only.
"""


@router.post("/assess")
async def assess_freshness(
    file: UploadFile = File(..., description="Upload a food image"),
):
    """Assess apparent visual freshness; this cannot prove food safety."""

    try:
        encoded_image = await _read_uploaded_image(file)

        response_text = _call_groq_vision(
            encoded_image=encoded_image,
            system_prompt=FRESHNESS_PROMPT,
            user_prompt=(
                "Assess only the visible condition of the food in this "
                "image. Follow the JSON schema exactly."
            ),
        )

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="The AI returned invalid JSON. Please try again.",
            ) from exc

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=502,
                detail="The AI returned an unexpected response.",
            )

        required = [
            "food_name",
            "apparent_freshness",
            "visible_evidence",
            "concerns",
            "recommendations",
            "limitations",
        ]

        if any(field not in result for field in required):
            raise HTTPException(
                status_code=502,
                detail="The AI response is missing required fields.",
            )

        allowed_labels = {
            "Fresh",
            "Moderately Fresh",
            "Possibly Spoiled",
            "Inconclusive",
        }

        if result["apparent_freshness"] not in allowed_labels:
            raise HTTPException(
                status_code=502,
                detail="The AI returned an invalid freshness category.",
            )

        for field in [
            "visible_evidence",
            "concerns",
            "recommendations",
            "limitations",
        ]:
            if (
                not isinstance(result[field], list)
                or not all(isinstance(item, str) for item in result[field])
            ):
                raise HTTPException(
                    status_code=502,
                    detail=f"The AI returned an invalid {field} field.",
                )

        if not isinstance(result["food_name"], str):
            raise HTTPException(
                status_code=502,
                detail="The AI returned an invalid food name.",
            )

        return {
            "success": True,
            "model": GROQ_MODEL_NAME,
            "assessment": result,
            "safety_notice": (
                "A photograph cannot establish whether food is safe to eat. "
                "Do not taste food to test freshness. Follow appropriate "
                "food-safety guidance when in doubt."
            ),
        }

    except HTTPException:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unsafe image. Upload a valid image.",
        ) from None
    except OSError:
        raise HTTPException(
            status_code=400,
            detail="The image could not be decoded.",
        ) from None
    except Exception:
        logger.exception("Freshness assessment failed.")
        raise HTTPException(
            status_code=503,
            detail="Freshness assessment failed. Check server logs.",
        ) from None
    finally:
        await file.close()
