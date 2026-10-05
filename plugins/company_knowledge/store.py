from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "company_knowledge"


def get_client(path: Path = CHROMA_PATH) -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(path))


def new_collection(client: chromadb.ClientAPI) -> Collection:
    """An empty collection. Ingest rebuilds it from scratch, so a PDF removed from docs/ disappears from the search."""
    if COLLECTION_NAME in [collection.name for collection in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    # embedding_function=None: we pass our own vectors, so Chroma must not download a model of its own.
    # Cosine distance, so similarity = 1 - distance.
    return client.create_collection(COLLECTION_NAME, embedding_function=None, metadata={"hnsw:space": "cosine"})
