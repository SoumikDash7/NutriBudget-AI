from enum import Enum


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Goal(str, Enum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    VERY_ACTIVE = "very_active"
    ATHLETE = "athlete"


class PreferredUnit(str, Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"