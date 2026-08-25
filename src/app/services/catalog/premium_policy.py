HIGH_QUALITY_GRADES = ("High Grade", "SS", "SSS")
HIGH_QUALITY_GRADE_FILTER = ",".join(HIGH_QUALITY_GRADES)
HIGH_QUALITY_CONTACT_MESSAGE = "Please contact us for high quality product."


def normalize_grade(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


HIGH_QUALITY_NORMALIZED_GRADES = {
    normalize_grade(grade) for grade in HIGH_QUALITY_GRADES
}


def is_high_quality_grade(value: str | None) -> bool:
    return normalize_grade(value) in HIGH_QUALITY_NORMALIZED_GRADES
