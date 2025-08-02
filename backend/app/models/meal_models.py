from enum import Enum
from pydantic import BaseModel, Field, computed_field
from typing import List
import random


def _read_tips():
    with open("app/data/tips.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# Cache tips at module level
TIPS = _read_tips()


class GICategory(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Level(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    GOOD = "good"
    MEDIUM = "medium"


class Ingredient(BaseModel):
    name: str
    portion: float
    gi: float
    carbs_per_100g: float
    protein_per_100g: float
    fat_per_100g: float

    @computed_field
    @property
    def gi_category(self) -> GICategory:
        if self.gi >= 70:
            return GICategory.HIGH
        elif self.gi >= 56:
            return GICategory.MEDIUM
        return GICategory.LOW

    @computed_field
    @property
    def gl(self) -> float:
        return round((self.gi * self.carbs_per_100g * self.portion / 100) / 100, 1)

    @computed_field
    @property
    def gl_category(self) -> GICategory:
        if self.gl >= 20:
            return GICategory.HIGH
        elif self.gl >= 11:
            return GICategory.MEDIUM
        return GICategory.LOW


class Meal(BaseModel):
    ingredients: List[Ingredient]
    notes: str

    @computed_field
    @property
    def total_carbs(self) -> float:
        return round(sum(ing.carbs_per_100g * ing.portion / 100 for ing in self.ingredients), 1)

    @computed_field
    @property
    def total_protein(self) -> float:
        return round(sum(ing.protein_per_100g * ing.portion / 100 for ing in self.ingredients), 1)

    @computed_field
    @property
    def total_fat(self) -> float:
        return round(sum(ing.fat_per_100g * ing.portion / 100 for ing in self.ingredients), 1)

    @computed_field
    @property
    def total_gl(self) -> float:
        return round(sum(ing.gl for ing in self.ingredients), 1)

    @computed_field
    @property
    def meal_gl_category(self) -> GICategory:
        if self.total_gl >= 20:
            return GICategory.HIGH
        elif self.total_gl >= 11:
            return GICategory.MEDIUM
        return GICategory.LOW

    @computed_field
    @property
    def impact_level(self) -> Level:
        if self.meal_gl_category == GICategory.HIGH:
            return Level.HIGH
        elif self.meal_gl_category == GICategory.MEDIUM:
            return Level.MODERATE
        return Level.LOW

    @computed_field
    @property
    def protein_level(self) -> Level:
        if self.total_protein >= 20:
            return Level.GOOD
        elif self.total_protein >= 10:
            return Level.MEDIUM
        return Level.LOW

    @computed_field
    @property
    def fat_level(self) -> Level:
        if self.total_fat >= 15:
            return Level.GOOD
        elif self.total_fat >= 7:
            return Level.MEDIUM
        return Level.LOW

    def _get_impact_explanation(self) -> str:
        return random.choice(TIPS)

    def _get_meal_timing_advice(self) -> str:
        if self.total_gl >= 20:
            return "Best consumed after exercise or early in the day when insulin sensitivity is higher"
        elif self.total_gl >= 11:
            return "Can be consumed at most times of day, but better earlier"
        return "Can be consumed at any time of day"

    def _generate_tips(self) -> List[str]:
        tips = []

        # GL-based tips
        if self.total_gl >= 20:
            tips.append("Consider reducing portion sizes of high-GI foods")
            tips.append("Try to pair with protein or fiber-rich foods")
        elif self.total_gl >= 11:
            tips.append("Good balance, but watch portion sizes")

        # Protein-based tips
        if self.total_protein < 10:
            tips.append(
                "Consider adding protein sources like eggs, lean meat, or legumes"
            )
        elif self.total_protein < 20:
            tips.append("Good protein content, could be increased slightly")

        # Fat-based tips
        if self.total_fat < 7:
            tips.append("Consider adding healthy fats like avocado, nuts, or olive oil")
        elif self.total_fat < 15:
            tips.append("Good fat content, could be increased slightly")

        # Ingredient-specific tips
        high_gi_ingredients = [ing for ing in self.ingredients if ing.gi >= 70]
        if high_gi_ingredients:
            tips.append(
                f"Consider alternatives for high-GI items: {', '.join(ing.name for ing in high_gi_ingredients)}"
            )

        return tips

    @computed_field
    @property
    def impact_explanation(self) -> str:
        return self._get_impact_explanation()

    @computed_field
    @property
    def best_time(self) -> str:
        return self._get_meal_timing_advice()

    @computed_field
    @property
    def tips(self) -> List[str]:
        return self._generate_tips()
