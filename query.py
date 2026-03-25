from llama_index.core import load_index_from_storage, StorageContext
from llama_index.llms.openai import OpenAI
from llama_index.core.postprocessor import LLMRerank
import os

# ---------------------------
# CONFIG
# ---------------------------
GROUP = os.environ.get("GROUP", "default_group")
PERSIST_DIR = f"storage/{GROUP}"


# ---------------------------
# 1. Load persisted index
# ---------------------------
if not os.path.exists(PERSIST_DIR):
    raise ValueError(f"Index not found for group: {GROUP}")

storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
index = load_index_from_storage(storage_context)


# ---------------------------
# 2. Configure reranker
# ---------------------------
reranker = LLMRerank(top_n=3)


# ---------------------------
# 3. Create query engine
# ---------------------------
query_engine = index.as_query_engine(
    similarity_top_k=10,  # higher recall for mixed text + image
    node_postprocessors=[reranker],
    llm=OpenAI(model="gpt-4o-mini"),
)


# ---------------------------
# 4. Query loop
# ---------------------------
print(f"RAG system ready (group={GROUP}). Type your question:\n")

while True:
    query = input("Your question: ").strip()
    if not query:
        continue

    # Execute query
    response = query_engine.query(query)

    # ---------------------------
    # PRINT ANSWER
    # ---------------------------
    print("\nAnswer:\n", response, "\n")

    # ---------------------------
    # PRINT SOURCES (TEXT + IMAGE)
    # ---------------------------
    print("Sources:")

    images = []

    for node in response.source_nodes:
        metadata = node.metadata or {}
        source_type = metadata.get("type", "text")

        if source_type == "image":
            image_path = metadata.get("image_path", "unknown")
            images.append(image_path)

            print(f"[IMAGE] {image_path}")
            print(f"         {node.text[:200].replace('\n', ' ')}...\n")

        else:
            file_name = metadata.get("file_name", "unknown")
            preview = node.text[:200].replace("\n", " ")

            print(f"[TEXT] {file_name}")
            print(f"       {preview}...\n")

    # ---------------------------
    # SUMMARY OF IMAGES
    # ---------------------------
    if images:
        print("Retrieved Images:")
        for img in images:
            print(f" - {img}")

    print("\n" + "=" * 60 + "\n")
