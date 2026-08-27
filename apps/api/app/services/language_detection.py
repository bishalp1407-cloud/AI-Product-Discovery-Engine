from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0


def detect_language(text: str) -> str | None:
    cleaned = text.strip()

    if not cleaned:
        return None

    try:
        return detect(cleaned)
    except LangDetectException:
        return None