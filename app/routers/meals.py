import logging
from fastapi import APIRouter, HTTPException
from app.models.nutrition_models import NutritionRecord, Ingredient
from app.models.user_models import User, WeixinUser
from ..dependencies import get_db, get_current_user
from sqlalchemy.orm import Session
from typing import Union
from datetime import datetime, timezone
import traceback
from fastapi import Depends, Security
import random
from app.models.meal_models import TIPS, Meal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meals", tags=["meals"])

@router.get("/history")
async def get_meals_history(
    start_time: datetime = None,  # Optional UTC timestamp
    end_time: datetime = None,  # Optional UTC timestamp
    current_user: Union[User, WeixinUser] = Security(get_current_user),
    db: Session = Depends(get_db),
):
    # forward to /history
    return await get_meals(start_time, end_time, current_user, db)

@router.get("")
async def get_meals(
    start_time: datetime = None,  # Optional UTC timestamp
    end_time: datetime = None,  # Optional UTC timestamp
    current_user: Union[User, WeixinUser] = Security(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's nutrition analysis history.
    
    Args:
        start_time: Optional start of the time range in UTC
        end_time: Optional end of the time range in UTC
        current_user: The authenticated user
        db: Database session
    """
    try:
        # Get records with ingredients in a single query using join
        if isinstance(current_user, WeixinUser):
            query = (
                db.query(NutritionRecord, Ingredient)
                .outerjoin(Ingredient)
                .filter(NutritionRecord.weixin_user_id == current_user.id)
            )
        else:
            query = (
                db.query(NutritionRecord, Ingredient)
                .outerjoin(Ingredient)
                .filter(NutritionRecord.user_id == current_user.id)
            )
            
        # Apply time filters if provided
        if start_time:
            start_time = start_time.astimezone(timezone.utc)
            query = query.filter(NutritionRecord.meal_time >= start_time)
            
        if end_time:
            end_time = end_time.astimezone(timezone.utc)
            query = query.filter(NutritionRecord.meal_time <= end_time)
            
        # Apply ordering
        query = query.order_by(NutritionRecord.meal_time.desc())

        # Execute query once
        results = query.all()

        # Group results by record
        records_map = {}
        for record, ingredient in results:
            if record.id not in records_map:
                records_map[record.id] = {
                    "id": record.id,
                    "meal_time": record.meal_time.isoformat(),
                    "image_url": record.image_url,
                    "total_gl": round(record.total_gl, 1) if record.total_gl else None,
                    "total_carbs": round(record.total_carbs, 1)
                    if record.total_carbs
                    else None,
                    "total_protein": round(record.total_protein, 1)
                    if record.total_protein
                    else None,
                    "total_fat": round(record.total_fat, 1)
                    if record.total_fat
                    else None,
                    "meal_gl_category": record.meal_gl_category,
                    "impact_level": record.impact_level,
                    "protein_level": record.protein_level,
                    "fat_level": record.fat_level,
                    "protein_explanation": record.protein_explanation,
                    "fat_explanation": record.fat_explanation,
                    "impact_explanation": random.choice(TIPS),
                    "best_time": record.best_time,
                    "notes": record.notes if record.notes else "",
                    "ingredients": [],
                }

            if ingredient is not None:
                records_map[record.id]["ingredients"].append(
                    {
                        "name": ingredient.name,
                        "portion": ingredient.portion,
                        "carbs_per_100g": round(ingredient.carbs_per_100g, 1)
                        if ingredient.carbs_per_100g is not None
                        else 0,
                        "protein_per_100g": round(ingredient.protein_per_100g, 1)
                        if ingredient.protein_per_100g is not None
                        else 0,
                        "fat_per_100g": round(ingredient.fat_per_100g, 1)
                        if ingredient.fat_per_100g is not None
                        else 0,
                        "gi": round(ingredient.gi) if ingredient.gi is not None else 0,
                        "gl": round(ingredient.gl, 1)
                        if ingredient.gl is not None
                        else 0,
                        "gi_category": ingredient.gi_category,
                    }
                )

        # Convert to list and return
        return list(records_map.values())

    except Exception as e:
        logger.error(f"Error fetching nutrition history: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch nutrition history")


@router.post("")
async def save_meal(
    meal_data: dict,
    current_user: Union[User, WeixinUser] = Security(get_current_user),
    db: Session = Depends(get_db),
):
    # workaround for datetime.fromisoformat error
    if "meal_time" in meal_data["analysis"] and meal_data["analysis"]["meal_time"]:
        meal_data["analysis"]["meal_time"] = datetime.fromisoformat(meal_data["analysis"]["meal_time"])

    """Save meal analysis results to database using upsert logic based on file_id"""
    try:
        # Check if record with this file_id already exists for this user
        existing_record = None
        if isinstance(current_user, WeixinUser):
            existing_record = (
                db.query(NutritionRecord)
                .filter(
                    NutritionRecord.weixin_user_id == current_user.id,
                    NutritionRecord.image_url == meal_data["file_id"],
                )
                .first()
            )
        else:
            existing_record = (
                db.query(NutritionRecord)
                .filter(
                    NutritionRecord.user_id == current_user.id,
                    NutritionRecord.image_url == meal_data["file_id"],
                )
                .first()
            )

        if existing_record:
            # Update existing record
            if "analysis" in meal_data:
                existing_record = NutritionRecord(
                    **existing_record.__dict__,
                    **meal_data["analysis"],
                    updated_at=datetime.now(timezone.utc),
                )

                # Delete existing ingredients
                db.query(Ingredient).filter(
                    Ingredient.nutrition_record_id == existing_record.id
                ).delete()

                # Create new ingredients
                new_ingredients = []
                for ing_data in meal_data["analysis"]["ingredients"]:
                    ingredient = Ingredient(
                        nutrition_record_id=existing_record.id,
                        **ing_data,
                        amount=ing_data["portion"],
                    )
                    new_ingredients.append(ingredient)

                db.add_all(new_ingredients)
            nutrition_record = existing_record

        else:
            # Create new record
            if "analysis" in meal_data:
                nutrition_record = NutritionRecord(
                    user_id=current_user.id if isinstance(current_user, User) else None,
                    weixin_user_id=current_user.id
                    if isinstance(current_user, WeixinUser)
                    else None,
                    image_url=meal_data["file_id"],
                    meal_time=meal_data["analysis"]["meal_time"]
                    if "meal_time" in meal_data["analysis"]
                    else datetime.now(timezone.utc),
                    total_carbs=meal_data["analysis"]["total_carbs"],
                    total_protein=meal_data["analysis"]["total_protein"],
                    total_fat=meal_data["analysis"]["total_fat"],
                    total_gl=meal_data["analysis"]["total_gl"],
                    meal_gl_category=meal_data["analysis"]["meal_gl_category"],
                    impact_level=meal_data["analysis"]["impact_level"],
                    protein_level=meal_data["analysis"]["protein_level"],
                    fat_level=meal_data["analysis"]["fat_level"],
                    protein_explanation=meal_data["analysis"].get(
                        "protein_explanation"
                    ),
                    fat_explanation=meal_data["analysis"].get("fat_explanation"),
                    impact_explanation=meal_data["analysis"]["impact_explanation"],
                    best_time=meal_data["analysis"]["best_time"],
                    notes=meal_data["analysis"].get("notes", ""),
                )

                # Create new ingredients
                ingredients = []
                for ing_data in meal_data["analysis"]["ingredients"]:
                    ingredient = Ingredient(
                        name=ing_data["name"],
                        carbs_per_100g=ing_data["carbs_per_100g"],
                        protein_per_100g=ing_data["protein_per_100g"],
                        fat_per_100g=ing_data["fat_per_100g"],
                        gi=ing_data["gi"],
                        gl=ing_data["gl"],
                        portion=ing_data["portion"],
                        gi_category=ing_data.get("gi_category"),
                    )
                    ingredients.append(ingredient)

                nutrition_record.ingredients = ingredients
            else:
                nutrition_record = NutritionRecord(
                    user_id=current_user.id if isinstance(current_user, User) else None,
                    weixin_user_id=current_user.id
                    if isinstance(current_user, WeixinUser)
                    else None,
                    image_url=meal_data["file_id"],
                )
            db.add(nutrition_record)

        db.commit()
        db.refresh(nutrition_record)

        return {
            "message": "Meal analysis saved successfully",
            "id": nutrition_record.id,
        }

    except Exception as e:
        logger.error(f"Error saving meal analysis: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to save meal analysis: {str(e)}"
        )
