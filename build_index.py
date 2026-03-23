from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding

# Load documents WITH metadata
documents = SimpleDirectoryReader("data").load_data()

# Inspect (optional debug)
for doc in documents:
    print(doc.metadata)

splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

index = VectorStoreIndex.from_documents(
    documents,
    transformations=[splitter],
    embed_model=OpenAIEmbedding(model="text-embedding-3-small"),
)

# Persist
index.storage_context.persist(persist_dir="storage")

print("✅ Index built with metadata!")
