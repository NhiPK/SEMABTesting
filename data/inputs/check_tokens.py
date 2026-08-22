import json
import tiktoken
import os

def calculate_batch_tokens(file_path, model_name="gpt-4o-mini"):
    """
    Calculates the exact number of tokens OpenAI will count for a batch file.
    Formula: Input Tokens (Messages) + Output Tokens (max_tokens parameter)
    """
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return

    # Initialize the tokenizer for the specific model
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        print(f"[WARNING] Model {model_name} not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    total_input_tokens = 0
    total_max_tokens_reserved = 0
    total_requests = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                body = data.get("body", {})
                
                # 1. Count input tokens from messages
                messages = body.get("messages", [])
                for msg in messages:
                    content = msg.get("content", "")
                    # Add 4 tokens per message for formatting overhead
                    total_input_tokens += len(encoding.encode(content)) + 4 
                    
                # 2. Count reserved output tokens
                max_tokens = body.get("max_tokens", 0)
                total_max_tokens_reserved += max_tokens
                
                total_requests += 1
                
            except json.JSONDecodeError:
                print("[ERROR] Invalid JSON line found. Skipping.")
                continue

    grand_total = total_input_tokens + total_max_tokens_reserved

    print("\n--- Token Usage Report ---")
    print(f"Target File         : {os.path.basename(file_path)}")
    print(f"Total Requests      : {total_requests}")
    print(f"Input Tokens        : {total_input_tokens:,}")
    print(f"Reserved Max Tokens : {total_max_tokens_reserved:,}")
    print("-" * 26)
    print(f"GRAND TOTAL ENQUEUED: {grand_total:,} tokens")
    print("-" * 26)
    
    if grand_total > 2000000:
        print("\n[CRITICAL WARNING] This file exceeds the 2,000,000 enqueued token limit!")
    else:
        print("\n[SAFE] This file is ready to be uploaded.")

if __name__ == "__main__":
    # Update this path to point to one of your chunked files
    TARGET_FILE = r"data\inputs\openai5_batch_tasks_all_part_1.jsonl"
    calculate_batch_tokens(TARGET_FILE)