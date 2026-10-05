import os

import httpx
from langchain_core.tools import ToolException

# This plugin picks its own embedding model, so it can change without touching the main agent or other plugins.
EMBEDDING_URL = "https://integrate.api.nvidia.com/v1/embeddings"
EMBEDDING_MODEL = "nvidia/nemotron-3-embed-1b"
BATCH_SIZE = 32


async def embed(texts: list[str], input_type: str) -> list[list[float]]:
    """Returns one vector per text. input_type is "passage" for documents and "query" for questions."""
    headers = {"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"}
    vectors = []
    async with httpx.AsyncClient(timeout=60) as client:
        for start in range(0, len(texts), BATCH_SIZE):
            body = {
                "model": EMBEDDING_MODEL,
                "input": texts[start : start + BATCH_SIZE],
                "input_type": input_type,
                "encoding_format": "float",
            }
            try:
                response = await client.post(EMBEDDING_URL, headers=headers, json=body)
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise ToolException(f"The embedding service failed: {error}") from error
            vectors += [item["embedding"] for item in response.json()["data"]]
    return vectors

