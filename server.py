import os
import re
import base64
import mimetypes
from typing import List, Tuple

from aiohttp import web
from openai import OpenAI

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Document,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import LLMRerank
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding


# ---------------------------
# CONFIG
# ---------------------------
DATA_DIR = "data"
STORAGE_ROOT = "storage"

client = OpenAI()


# ---------------------------
# MARKDOWN IMAGE PARSER
# ---------------------------
IMAGE_MD_PATTERN = re.compile(r"!\[(.*?)\]\((.*?)\)")

def extract_images(md_text: str) -> List[Tuple[str, str]]:
    return IMAGE_MD_PATTERN.findall(md_text)


# ---------------------------
# IMAGE ENCODING
# ---------------------------
def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------
# IMAGE CAPTIONING
# ---------------------------
def caption_image(image_path: str) -> str:
    base64_image = encode_image(image_path)

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    data_url = f"data:{mime_type};base64,{base64_image}"

    response = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Describe this image in detail for retrieval. "
                        "Include UI elements, numbers, labels, and context."
                    ),
                },
                {
                    "type": "input_image",
                    "image_url": data_url,
                },
            ],
        }],
    )

    return response.output_text.strip()


# ---------------------------
# BUILD DOCUMENTS (TEXT + IMAGES)
# ---------------------------
def build_documents() -> List[Document]:
    documents: List[Document] = []

    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if not file.endswith(".md"):
                continue

            md_path = os.path.join(root, file)

            with open(md_path, "r", encoding="utf-8") as f:
                md_text = f.read()

            # TEXT
            documents.append(
                Document(
                    text=md_text,
                    metadata={
                        "type": "text",
                        "file_name": file,
                        "file_path": md_path,
                    },
                )
            )

            # IMAGES
            images = extract_images(md_text)

            for alt_text, rel_path in images:
                abs_path = os.path.normpath(
                    os.path.join(os.path.dirname(md_path), rel_path)
                )

                if not os.path.exists(abs_path):
                    print(f"[WARN] Missing image: {abs_path}")
                    continue

                try:
                    caption = caption_image(abs_path)

                    if alt_text:
                        caption = f"Alt: {alt_text}. {caption}"

                    documents.append(
                        Document(
                            text=caption,
                            metadata={
                                "type": "image",
                                "file_name": os.path.basename(abs_path),
                                "image_path": abs_path,
                                "source_md": file,
                            },
                        )
                    )

                    print(f"[OK] Captioned: {abs_path}")

                except Exception as e:
                    print(f"[ERROR] {abs_path}: {e}")

    return documents


# ---------------------------
# BUILD INDEX ENDPOINT
# ---------------------------
async def build_index(request):
    group = request.query.get("group")

    if not group:
        return web.json_response({"error": "Missing group parameter"}, status=400)

    persist_dir = os.path.join(STORAGE_ROOT, group)

    try:
        documents = build_documents()

        splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

        index = VectorStoreIndex.from_documents(
            documents,
            transformations=[splitter],
            embed_model=OpenAIEmbedding(model="text-embedding-3-small"),
        )

        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)

        return web.json_response({
            "status": "success",
            "documents_indexed": len(documents),
            "group": group
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------
# QUERY ENDPOINT (WITH IMAGE SUPPORT)
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

        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)

        reranker = LLMRerank(top_n=3)

        query_engine = index.as_query_engine(
            similarity_top_k=10,
            node_postprocessors=[reranker],
            llm=LlamaOpenAI(model="gpt-4o-mini"),
        )

        response = query_engine.query(query_text)

        # Separate text and image sources
        sources = []
        images = []

        for node in response.source_nodes:
            meta = node.metadata or {}

            source_item = {
                "type": meta.get("type", "text"),
                "file_name": meta.get("file_name"),
                "preview": node.text[:200],
            }

            if meta.get("type") == "image":
                source_item["image_path"] = meta.get("image_path")
                images.append(meta.get("image_path"))

            sources.append(source_item)

        return web.json_response({
            "result": str(response),
            "sources": sources,
            "images": images  # direct image list for frontend
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
