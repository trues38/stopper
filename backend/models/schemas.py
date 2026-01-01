"""Pydantic 스키마 정의"""

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ============== Food ==============

class FoodBase(BaseModel):
    name: str
    manufacturer: Optional[str] = None
    category_large: Optional[str] = None
    category_medium: Optional[str] = None
    category_small: Optional[str] = None
    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbohydrate: float = 0
    sugar: float = 0
    sodium: float = 0
    saturated_fat: float = 0
    serving_size: Optional[str] = None


class FoodResponse(FoodBase):
    id: int

    class Config:
        from_attributes = True


class FoodSearchResponse(BaseModel):
    total: int
    items: list[FoodResponse]


# ============== User Settings ==============

class UserSettings(BaseModel):
    goal_type: str = "maintain"  # diet, bulk, maintain, diabetes
    calorie_goal: int = 2000
    protein_goal: int = 60
    sugar_limit: int = 50


# ============== Daily Record ==============

class RecordCreate(BaseModel):
    food_id: int
    quantity: float = 1
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snack


class RecordResponse(BaseModel):
    id: int
    food_id: int
    food_name: str
    quantity: float
    meal_type: Optional[str]
    calories: float
    protein: float
    sugar: float
    sodium: float
    recorded_at: datetime


class DailyTotals(BaseModel):
    calories: float
    protein: float
    sugar: float
    sodium: float


class TodayResponse(BaseModel):
    date: date
    totals: DailyTotals
    records: list[RecordResponse]


# ============== Combination (Neo4j-ready JSON) ==============

class ComboItem(BaseModel):
    """조합 아이템 - food_id는 문자열 (Neo4j 대비)"""
    food_id: str  # "food_123" 형태
    name: str
    qty: int = 1
    calories: float = 0
    protein: float = 0
    sugar: float = 0
    sodium: float = 0


class ComboIntent(BaseModel):
    """조합 의도 - 왜 이 조합을 만들었는지"""
    goal: str = "maintain"  # diet, bulk, maintain, diabetes
    target_protein: Optional[int] = None
    target_calories: Optional[int] = None
    limit_sugar: Optional[int] = None
    limit_sodium: Optional[int] = None


class ComboResult(BaseModel):
    """조합 결과 - 실제 영양정보 합계"""
    calories: float
    protein: float
    sugar: float
    sodium: float = 0
    percent_of_daily: Optional[int] = None  # 일일 목표 대비 %


class ComboSignals(BaseModel):
    """전이 힌트 - Neo4j 엣지 후보"""
    worked: Optional[bool] = None  # 유저 피드백
    repeat_count: int = 0  # 재사용 횟수
    next_combo_hint: Optional[str] = None  # 다음 조합 ID (v2)


class CombinationCreate(BaseModel):
    """조합 생성 요청"""
    name: str
    description: Optional[str] = None
    items: list[ComboItem]
    intent: ComboIntent
    result: ComboResult
    signals: ComboSignals = ComboSignals()
    tags: list[str] = []


class CombinationResponse(BaseModel):
    """조합 응답 - combo_id는 문자열"""
    id: str  # "combo_20260101_001" 형태
    name: str
    description: Optional[str]
    author_id: str  # "user_anon_123" 형태
    items: list[ComboItem]
    intent: ComboIntent
    result: ComboResult
    signals: ComboSignals
    tags: list[str]
    likes_count: int
    is_official: bool
    created_at: datetime


class CombinationListResponse(BaseModel):
    total: int
    items: list[CombinationResponse]


# ============== Scan Result ==============

class ScanResult(BaseModel):
    food: FoodResponse
    percentages: dict  # {"calories": 25, "protein": 15, "sugar": 6}
    verdict: str  # 판정 문구
    status: dict  # {"calories": "safe", "protein": "low", "sugar": "safe"}
