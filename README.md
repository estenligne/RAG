# LOCAL RAG SETUP GUIDE (UBUNTU + LLAMAINDEX + OPENAI + IMAGE SUPPORT + HTTP SERVER)

This guide explains how to build a production-ready Retrieval-Augmented Generation (RAG) system that supports:

- Markdown documents
- Image understanding via captioning
- Persistent vector indexing
- HTTP API (aiohttp) with /build-index and /query endpoints

By the end, you will have a multimodal RAG system that can answer questions using both text and images.

------------------------------------------------------------

## Step 1: Check Python Installation

python3 --version

You should have Python 3.9+.

------------------------------------------------------------

## Step 2: Create and Activate Virtual Environment

python3 -m venv rag-env
source rag-env/bin/activate

------------------------------------------------------------

## Step 3: Install Dependencies

pip install -r requirements.txt

Make sure your requirements include:

- llama-index
- openai
- aiohttp

------------------------------------------------------------

## Step 4: Configure OpenAI API Key

export OPENAI_API_KEY="your_api_key_here"

Optional (persistent):

echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

------------------------------------------------------------

## Step 5: Create Project Structure

mkdir -p data storage

Structure:

project/
│
├── data/        # Markdown + images
├── storage/     # Vector indexes
├── server.py
└── requirements.txt

------------------------------------------------------------

## Step 6: Add Markdown Files (WITH IMAGE SUPPORT)

Place your .md files in the data directory.

IMPORTANT: To enable image support, your Markdown must include valid image references:

Example:

nano data/notes.md

------------------------------------------------------------

### Correct Markdown Image Syntax

![Dashboard](dashboard.png)

Rules:

- Image must be in SAME folder as the .md file
- Use relative path only (no absolute paths)
- Supported formats: .png, .jpg, .jpeg

------------------------------------------------------------

### Example Data Folder

data/
  notes.md
  dashboard.png
  system.png

------------------------------------------------------------

## Step 7: How Image Support Works (IMPORTANT)

Your system performs:

1. Detect images in Markdown
2. Convert images to base64
3. Send them to OpenAI
4. Generate captions
5. Store captions as searchable text

Pipeline:

Markdown + Images → Captioning → Vector Index → Query

IMPORTANT REALITY:

- Images are NOT directly searched
- Only their captions are indexed
- Caption quality determines retrieval quality

------------------------------------------------------------

## Step 8: Use the HTTP Server (server.py)


This server provides:

GET  /build-index?group=...
POST /query?group=...

------------------------------------------------------------

### /build-index

Purpose:

- Reads Markdown files
- Extracts images
- Generates captions
- Builds vector index
- Saves to storage/<group>

------------------------------------------------------------

### /query

Purpose:

- Loads index
- Performs retrieval (top_k=10)
- Applies LLM reranking
- Returns:
  - Answer
  - Sources (text + image)
  - Image paths

------------------------------------------------------------

## Step 9: Start the Server

python server.py

Server runs at:

http://localhost:8000

------------------------------------------------------------

## Step 10: Build the Index

curl "http://localhost:8000/build-index?group=test"

Expected response:

{
  "status": "success",
  "documents_indexed": 5,
  "group": "test"
}

IMPORTANT:

- Each image = 1 additional document
- If you only see 1 document → images were not processed

------------------------------------------------------------

## Step 11: Query the System

curl -X POST "http://localhost:8000/query?group=test" \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the image(s) show?"}'

------------------------------------------------------------

## Example Response

{
  "result": "The dashboard shows...",
  "sources": [
    {
      "type": "image",
      "file_name": "dashboard.png",
      "image_path": "data/dashboard.png",
      "preview": "Alt: Dashboard..."
    }
  ],
  "images": [
    "data/dashboard.png"
  ]
}

------------------------------------------------------------

## Step 12: What the Response Contains

- result  → final answer
- sources → all retrieved chunks (text + image captions)
- images  → list of image paths for frontend display

------------------------------------------------------------

## Example Questions

- What does the dashboard show?
- Describe the system architecture
- What are the setup steps?
- What is shown in the image?

------------------------------------------------------------

## Debugging (CRITICAL)

If images are NOT indexed:

1. Check Markdown syntax:
   ![name](image.png)

2. Check image exists:
   ls data/

3. Check logs:
   [OK] Captioned: data/image.png

4. If missing:
   - Wrong path
   - Wrong filename
   - Missing file

------------------------------------------------------------

## Common Failures

### 1. "Total documents = 1"

→ No images processed

Cause:
- Bad Markdown syntax
- Missing files

------------------------------------------------------------

### 2. Captioning Error

Example:

Error code 400

Cause:
- Wrong API format
- Fixed in your current code

------------------------------------------------------------

### 3. Slow Performance

Cause:
- Each image = API call

Solution:
- Add caption caching (recommended)

------------------------------------------------------------

## Important Notes (No Sugar-Coating)

- This is NOT true multimodal AI
- It is TEXT retrieval using image captions
- Bad captions = bad answers
- Large image sets = expensive

------------------------------------------------------------

## Final Commands Summary

source rag-env/bin/activate
python server.py

# build index
curl "http://localhost:8000/build-index?group=test"

# query
curl -X POST "http://localhost:8000/query?group=test" \
  -H "Content-Type: application/json" \
  -d '{"query": "your question"}'

------------------------------------------------------------

## What You Have Built

You now have:

- Persistent RAG system
- Markdown + Image understanding
- API-based querying
- Source traceability
- Image retrieval support

This is a real hybrid RAG system.

------------------------------------------------------------

END
