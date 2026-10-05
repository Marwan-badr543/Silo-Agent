from chromadb.errors import NotFoundError
from langchain_core.tools import ToolException, tool
from pydantic import BaseModel, Field

from plugins.company_knowledge.embeddings import embed
from plugins.company_knowledge.store import COLLECTION_NAME, get_client

TOP_K = 4
# Passages less similar than this are not about the question. Better to find nothing than to show an unrelated passage.
MIN_SIMILARITY = 0.2


class SearchInput(BaseModel):
    question: str = Field(
        description="What to look up, written as a clear question that makes sense on its own, e.g. 'How long is the refund window?'."
    )


def _open_collection():
    try:
        return get_client().get_collection(COLLECTION_NAME, embedding_function=None)
    except NotFoundError as error:
        raise ToolException("The company knowledge base has not been built yet, so it cannot be searched now.") from error


@tool(args_schema=SearchInput)
async def company_knowledge_search(question: str) -> str:
    """Search the company's own documents (policies, products, services, prices, FAQs) for the answer to a question.

    Use it for any question about the company, its products, or its rules, before answering. Do NOT use it for
    chat, or to look up a customer's own tickets or orders. Returns the most relevant passages with their source
    file and page. Answer only from them. If it finds nothing relevant, the company documents do not cover it."""
    collection = _open_collection()
    [query_vector] = await embed([question], input_type="query")
    found = collection.query(query_embeddings=[query_vector], n_results=TOP_K, include=["documents", "metadatas", "distances"])
    passages = [
        f"[{metadata['source']}, page {metadata['page']}]\n{document}"
        for document, metadata, distance in zip(found["documents"][0], found["metadatas"][0], found["distances"][0])
        if 1 - distance >= MIN_SIMILARITY
    ]
    return "\n\n".join(passages) or "Nothing relevant was found in the company documents."
