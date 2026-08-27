import hashlib


def generate_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()