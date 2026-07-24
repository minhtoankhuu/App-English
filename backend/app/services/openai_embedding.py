"""Client embedding OpenAI dùng chung cho `app.embed_knowledge` (ingestion) và
`rag_search.hybrid_search`/Validation Engine (query-time) — implement đúng
`EmbeddingClient` Protocol trong `app/services/rag_search.py`.
"""

import openai


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str, model: str):
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def embed_one(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
