from llama_index.core import load_index_from_storage, StorageContext
from llama_index.llms.openai import OpenAI
from llama_index.core.postprocessor import LLMRerank

# ---------------------------
# 1. Load persisted index
# ---------------------------
storage_context = StorageContext.from_defaults(persist_dir="storage")
index = load_index_from_storage(storage_context)

# ---------------------------
# 2. Configure reranker
# ---------------------------
reranker = LLMRerank(
    top_n=3  # keep the top 3 most relevant chunks after reranking
)

# ---------------------------
# 3. Create query engine
# ---------------------------
query_engine = index.as_query_engine(
    similarity_top_k=8,       # retrieve more candidates initially
    node_postprocessors=[reranker],
    llm=OpenAI(model="gpt-4o-mini")
)

# ---------------------------
# 4. Query loop
# ---------------------------
print("RAG system ready. Type your question:\n")

while True:
    query = input("Your question: ").strip()
    if not query:
        continue

    # Execute query
    response = query_engine.query(query)

    # Print answer
    print("\nAnswer:\n", response, "\n")

    # Print sources for traceability
    print("Sources:")
    for node in response.source_nodes:
        file_name = node.metadata.get("file_name", "unknown")
        text_preview = node.text[:200].replace("\n", " ")  # first 200 chars
        print(f"- {file_name}: {text_preview}...")
    
    print("\n" + "="*60 + "\n")
