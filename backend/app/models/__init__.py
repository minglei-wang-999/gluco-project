"""
Models package for the application.
"""

# Import all models in the correct order to avoid circular dependencies

# First, import base models without relationships
from app.models.user_models import User, WeixinUser
from app.models.meal_models import Meal, Ingredient as MealIngredient, GICategory, Level

# Then import models that depend on the base models
from app.models.nutrition_models import NutritionRecord, Ingredient
from app.models.task_models import Task, TaskStatus, TaskCreate, TaskResponse, TaskStatusResponse, ProcessImageAsyncRequest

# This ensures all models are imported and registered with SQLAlchemy
__all__ = [
    'User', 'WeixinUser',
    'Meal', 'MealIngredient', 'GICategory', 'Level',
    'NutritionRecord', 'Ingredient',
    'Task', 'TaskStatus', 'TaskCreate', 'TaskResponse', 'TaskStatusResponse', 'ProcessImageAsyncRequest'
]
