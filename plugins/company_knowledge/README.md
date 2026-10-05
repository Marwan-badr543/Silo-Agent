# Company knowledge plugin (RAG)

Lets the agent answer questions about the company from your own PDF files.

1. Put your PDFs in `plugins/company_knowledge/docs/`. They must contain real text (scanned images are not supported).
2. Build the index: `python -m plugins.company_knowledge.ingest`. It stores the chunks and their vectors in a ChromaDB folder, `chroma_db/`, which stays on disk between runs. Run it again whenever the PDFs change (it rebuilds from scratch), then restart the server, because a running server does not see data written by another process.
3. The agent then uses the tool `company_knowledge_search`. It answers only from the passages the tool returns.

Settings are constants in the code: chunk size and the separators (blank line, then full stop, then comma) in `ingest.py`, the number of passages and the minimum similarity in `search.py`,
the embedding model in `embeddings.py`. It reads `NVIDIA_API_KEY` from the environment.

A demo PDF with made-up company data is in `docs/demo_company.pdf`. Delete it before indexing your real documents.
