import os
import re
import base64
import mimetypes
from typing import List, Tuple

from openai import OpenAI

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Document,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding


# ---------------------------
# CONFIG
# ---------------------------
DATA_DIR = "data"
STORAGE_ROOT = "storage"
GROUP = os.environ.get("GROUP", "default_group")

client = OpenAI()


# ---------------------------
# FIND MARKDOWN FILES
# ---------------------------
def find_markdown_files(root: str) -> List[str]:
    paths = []
    for base, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".md"):
                paths.append(os.path.join(base, f))
    return paths


# ---------------------------
# EXTRACT IMAGES FROM MARKDOWN
# ---------------------------
IMAGE_MD_PATTERN = re.compile(r"!\[(.*?)\]\((.*?)\)")

def extract_images(md_text: str) -> List[Tuple[str, str]]:
    return IMAGE_MD_PATTERN.findall(md_text)


# ---------------------------
# IMAGE ENCODING (FIXED)
# ---------------------------
def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------
# IMAGE CAPTIONING (FIXED)
# ---------------------------
def caption_image(image_path: str) -> str:
    base64_image = encode_image_to_base64(image_path)

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
                        "Include objects, numbers, UI elements, labels, and context."
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
# BUILD DOCUMENTS
# ---------------------------
def build_documents() -> List[Document]:
    documents: List[Document] = []

    md_files = find_markdown_files(DATA_DIR)

    for md_path in md_files:
        print(f"\nProcessing: {md_path}")

        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()

        # TEXT DOCUMENT
        documents.append(
            Document(
                text=md_text,
                metadata={
                    "type": "text",
                    "file_name": os.path.basename(md_path),
                    "file_path": md_path,
                },
            )
        )

        # IMAGE EXTRACTION
        images = extract_images(md_text)
        print("IMAGES FOUND:", images)

        for alt_text, rel_img_path in images:
            abs_img_path = os.path.normpath(
                os.path.join(os.path.dirname(md_path), rel_img_path)
            )

            print("RESOLVED PATH:", abs_img_path)

            if not os.path.exists(abs_img_path):
                print(f"[WARN] Image not found: {abs_img_path}")
                continue

            try:
                caption = caption_image(abs_img_path)

                if alt_text:
                    caption = f"Alt: {alt_text}. {caption}"

                documents.append(
                    Document(
                        text=caption,
                        metadata={
                            "type": "image",
                            "file_name": os.path.basename(abs_img_path),
                            "image_path": abs_img_path,
                            "source_md": os.path.basename(md_path),
                        },
                    )
                )

                print(f"[OK] Captioned: {abs_img_path}")

            except Exception as e:
                print(f"[ERROR] Failed to caption {abs_img_path}: {e}")

    return documents


# ---------------------------
# MAIN INDEX BUILDER
# ---------------------------
def main():
    persist_dir = os.path.join(STORAGE_ROOT, GROUP)
    os.makedirs(persist_dir, exist_ok=True)

    documents = build_documents()

    print(f"\nTotal documents (text + images): {len(documents)}")

    splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

    index = VectorStoreIndex.from_documents(
        documents,
        transformations=[splitter],
        embed_model=OpenAIEmbedding(model="text-embedding-3-small"),
    )

    index.storage_context.persist(persist_dir=persist_dir)

    print(f"\n✅ Index built and saved to: {persist_dir}")


if __name__ == "__main__":
    main()
