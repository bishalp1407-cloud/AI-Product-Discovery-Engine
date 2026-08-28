from dataclasses import dataclass

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class EmbeddingResult:
    text: str
    embedding: list[float]


_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(
            MODEL_NAME
        )

    return _model


def generate_embeddings(
    texts: list[str],
) -> list[EmbeddingResult]:
    if not texts:
        return []

    model = get_embedding_model()

    vectors = model.encode(
        texts,
        normalize_embeddings=True,
    )

    return [
        EmbeddingResult(
            text=text,
            embedding=vector.tolist(),
        )
        for text, vector in zip(
            texts,
            vectors,
        )
    ]