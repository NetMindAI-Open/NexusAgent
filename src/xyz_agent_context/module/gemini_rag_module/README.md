## Requirements

### Introduction

Implement an independent module (following the pattern of other modules) that uses the Gemini API for file-search. The trigger includes static methods for uploading documents.

1. Create a store for each agent-user pair, with display_name formatted as `agent_{id}_user_{id}`. Store the corresponding `store.name` in a local `./data/gemini_file_search_map.json` file. When needed, check this map first - use the existing store if found, otherwise create a new one.
2. When this module's MCP server starts, it provides three MCP tools to the agent:
    2.1 MCP-1 Query: Query the passed-in query using the store's display_name.
    2.2 MCP-2 Upload file: Upload a file given the file path and the store's display_name.
    2.3 MCP-3 Upload text: Given the store's display_name and a string, first write a local temporary file (named as date+time+random_code.md), then upload this file to the file-search store, and finally delete the temporary file.
3. This module also has its own instructions. Following the style of other modules' instructions, write them concisely and to the point, guiding the Agent to use its RAG system to search for information at the right time.
4. Hooks can be left unimplemented.

### Reference Code

```
from google import genai
from google.genai import types
import time
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))  # Reads GOOGLE_API_KEY from environment

def create_store(display_name: str = "binliang_test_store"):
    store = client.file_search_stores.create(
        config={"display_name": display_name}
    )
    print("Created FileSearchStore:", store.name)
    return store

store = create_store("binliang_test_store")
# store.name example: "fileSearchStores/ABCxyz..."

def upload_file_to_store(store, local_file_path: str, chunking_config: dict | None = None):
    # chunking_config is optional, for controlling chunking (token size / overlap)
    kwargs = {"file_search_store_name": store.name,
              "file": local_file_path}
    if chunking_config:
        kwargs["config"] = {"chunking_config": chunking_config}
    operation = client.file_search_stores.upload_to_file_search_store(**kwargs)
    print("Upload operation started:", operation)
    # Upload + indexing is generally async - you may need to wait (depends on file size / backend processing)
    # Simple wait (not elegant, but for demo purposes)
    time.sleep(5)
    print("Uploaded & indexed.")
    return operation

upload_file_to_store(store, "./deepseek_v2.pdf")
# Or specify chunk parameters, e.g.:
# upload_file_to_store(store, "my_doc.txt", chunking_config={"white_space_config": {"max_tokens_per_chunk": 400, "overlap_tokens": 50}})

store = client.file_search_stores.get(name="fileSearchStores/binliangteststore-c866m4drjbov")

def search_store(store, query: str, top_k: int = 5):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store.name],
                        top_k=top_k
                    )
                )
            ],
        )
    )

    if response.usage_metadata:
        usage = response.usage_metadata
        print("=" * 50)
        print("Token Usage:")
        print(f"  - Input tokens (prompt): {usage.prompt_token_count}")
        print(f"  - Output tokens (completion): {usage.candidates_token_count}")
        print(f"  - Total tokens: {usage.total_token_count}")

        # Gemini 2.5 Flash price estimate (as of late 2024)
        # Input: $0.075 / 1M tokens, Output: $0.30 / 1M tokens
        input_cost = (usage.prompt_token_count / 1_000_000) * 0.075
        output_cost = (usage.candidates_token_count / 1_000_000) * 0.30
        total_cost = input_cost + output_cost
        print(f"  - Estimated cost: ${total_cost:.6f} USD")
        print("=" * 50)

    chunks = []
    for cand in response.candidates:
        if cand.grounding_metadata and cand.grounding_metadata.grounding_chunks:
            for chunk in cand.grounding_metadata.grounding_chunks:
                chunks.append({
                    "text": chunk.retrieved_context.text,
                    "title": chunk.retrieved_context.title,
                })
    return chunks

# Usage
results = search_store(store, "What is DeepSeek-v2 math?", top_k=5)
for i, r in enumerate(results):
    print(f"=== Chunk {i+1} ===")
    print(f"Source: {r['title']}")
    print(f"Text: {r['text']}...")  # Print only first 500 characters
    print()
```
