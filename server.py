import os
import asyncio
from aiohttp import web

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import LLMRerank
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding


# ---------------------------
# CONFIG
# ---------------------------
DATA_DIR = "data"
STORAGE_ROOT = "storage"


# ---------------------------
# BUILD INDEX FUNCTION
# ---------------------------
async def build_index(request):
    group = request.query.get("group")

    if not group:
        return web.json_response({"error": "Missing group parameter"}, status=400)

    persist_dir = os.path.join(STORAGE_ROOT, group)

    try:
        # Load documents
        documents = SimpleDirectoryReader(DATA_DIR).load_data()

        # Chunking
        splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

        # Build index
        index = VectorStoreIndex.from_documents(
            documents,
            transformations=[splitter],
            embed_model=OpenAIEmbedding(model="text-embedding-3-small"),
        )

        # Persist
        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)

        return web.json_response({
            "status": "success",
            "message": f"Index built for group '{group}'"
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------
# QUERY FUNCTION
# ---------------------------
async def query_index(request):
    group = request.query.get("group")

    if not group:
        return web.json_response({"error": "Missing group parameter"}, status=400)

    persist_dir = os.path.join(STORAGE_ROOT, group)

    if not os.path.exists(persist_dir):
        return web.json_response(
            {"error": f"Index for group '{group}' not found"},
            status=404
        )

    try:
        data = await request.json()
        query_text = data.get("query")

        if not query_text:
            return web.json_response({"error": "Missing query"}, status=400)

        # Load index
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)

        # Reranker
        reranker = LLMRerank(top_n=3)

        # Query engine
        query_engine = index.as_query_engine(
            similarity_top_k=8,
            node_postprocessors=[reranker],
            llm=OpenAI(model="gpt-4o-mini"),
        )

        response = query_engine.query(query_text)

        # Extract sources
        sources = []
        for node in response.source_nodes:
            sources.append({
                "file_name": node.metadata.get("file_name", "unknown"),
                "text": node.text[:200]
            })

        return web.json_response({
            "result": str(response),
            "sources": sources
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------
# APP SETUP
# ---------------------------
def create_app():
    app = web.Application()
    app.router.add_get("/build-index", build_index)
    app.router.add_post("/query", query_index)
    return app


# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8000)
