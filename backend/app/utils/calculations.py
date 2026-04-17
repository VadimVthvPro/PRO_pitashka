from datetime import date


def calculate_age(date_of_birth: date) -> int:
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def calculate_bmi(weight: float, height_cm: float) -> float:
    height_m = height_cm / 100.0
    if height_m <= 0:
        return 0.0
    return round(weight / (height_m ** 2), 1)


def classify_bmi(bmi: float) -> str:
    if bmi < 15:
        return "severely_underweight"
    elif bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        return "normal"
    elif bmi < 30:
        return "overweight"
    else:
        return "obese"


def calculate_daily_calories(
    weight: float, height_cm: float, age: int, sex: str, aim: str
) -> float:
    """Mifflin-St Jeor formula"""
    if sex == "M":
        bmr = (10 * weight) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height_cm) - (5 * age) - 161

    activity_factor = 1.375

    tdee = bmr * activity_factor

    if aim == "weight_loss":
        return round(tdee - 500)
    elif aim == "weight_gain":
        return round(tdee + 300)
    else:
        return round(tdee)
