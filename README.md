# LOCAL RAG SETUP GUIDE (UBUNTU + LLAMAINDEX + OPENAI)

This guide explains how to build a simple Retrieval-Augmented Generation (RAG) system using Markdown files, LlamaIndex, and the OpenAI API. By the end, you will be able to ask questions and get answers based on your own documents.

---

## Step 1: Check Python Installation

Open your terminal and verify that Python is installed:

python3 --version

You should have Python 3.9 or higher. If not, install it before continuing.

---

## Step 2: Create and Activate a Virtual Environment

Create a virtual environment to isolate dependencies:

python3 -m venv rag-env

Activate it:

source rag-env/bin/activate

---

## Step 3: Install Required Packages

Install all necessary libraries:

pip install -r requirements.txt

---

## Step 4: Configure OpenAI API Key

Set your API key in the terminal:

export OPENAI_API_KEY="your_api_key_here"

If you want to make this permanent:

echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

---

## Step 5: Create Project Structure

Inside your project folder, create the required directories:

mkdir -p data storage

- data/ will contain your Markdown files
- storage/ will store the generated index

---

## Step 6: Add Markdown Files

Place your .md files inside the data directory.

Example:

nano data/notes.md

---

## Step 7: Create the Index Builder Script

Create a file named build_index.py:

nano build_index.py

Purpose:
- Loads Markdown files with metadata
- Chunks text for retrieval
- Creates embeddings
- Persists the index for repeated use


---

## Step 8: Build the Index

Run:

python build_index.py

---

## Step 9: Create the Query Script

Create query.py:

nano query.py

Purpose:
- Loads the persisted index
- Performs improved retrieval (more candidates)
- Uses LLM-based reranking to keep only the most relevant chunks
- Outputs answers with source file traceability

---

## Step 10: Run the System

python query.py


You can now type questions interactively. Each answer will show:

- The generated answer
- The source Markdown file(s) and a snippet of the relevant chunk
---

## Example Questions

- What is this document about?
- Summarize my notes
- Explain the key ideas

---

## Important Notes

- Run build_index.py only needs to be run when documents are added, removed, or modified.
- query.py can be used anytime 
- Metadata ensures answers are traceable to the original files.
- Using similarity_top=8 + LLMRerank(top_n=3) ensures better accuracy and relevance

---

## Final Commands Summary

source rag-env/bin/activate
python build_index.py
python query.py 

