import os
import json
from openai import OpenAI
from dotenv import load_dotenv

def prepare_batch_file(input_json_path, output_jsonl_path):
    """
    Step 1: Converts JSON prompt file into JSONL format 
    as required by the OpenAI Batch API specification.
    """
    print(f"Converting '{input_json_path}' to Batch format ('{output_jsonl_path}')...")
    
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for item in data:
            # We compress metadata and attributes into custom_id so we never lose them on download
            metadata = {
                "scen_id": item["scenario_id"],
                "persona": item["persona_group"],
                "attr_int": item.get("attr_intervention", 0),
                "attr_gen": item.get("attr_gender", 0),
                "attr_age": item.get("attr_age", 0),
                "attr_law": item.get("attr_law", 0)
            }
            custom_id_string = json.dumps(metadata)

            batch_request = {
                "custom_id": custom_id_string,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.0,  # Deterministic output for academic research
                    "max_tokens": 5,     # Keep tokens low to save costs
                    "messages": [
                        {
                            "role": "system", 
                            "content": (
                                f"{item['persona_prompt']}\n"
                                "CRITICAL: You must choose one case. Do not explain your reasoning. "
                                "Respond strictly in this exact format: 'Case 1' or 'Case 2'."
                            )
                        },
                        {
                            "role": "user", 
                            "content": item['scenario_text']
                        }
                    ]
                }
            }
            f.write(json.dumps(batch_request) + "\n")
            
    print("Conversion complete!")


def run_batch_pipeline():
    """
    Step 2: Uploads the JSONL file to OpenAI servers and triggers background batch execution.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or "YOUR_ACTUAL" in api_key or api_key.strip() == "":
        print("\n[INFO] OpenAI API Key is missing or not set in the '.env' file.")
        print("[INFO] Local file format verification complete. Ready to run once the API key is provided!\n")
        return

    client = OpenAI(api_key=api_key)

    print("Uploading batch prompt file to OpenAI...")
    batch_input_file = client.files.create(
        file=open("data/inputs/batch_tasks.jsonl", "rb"),
        purpose="batch"
    )
    
    print(f"Creating batch job with File ID: {batch_input_file.id}")
    batch_job = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "Trolley Problem LLM Cultural Persona Experiment"
        }
    )
    
    print("\n[SUCCESS] Batch Job successfully submitted!")
    print(f"Batch Job ID: {batch_job.id}")
    print("Save this Job ID to retrieve the dataset using the downloader script once completed.")


if __name__ == "__main__":
    input_path = "data/inputs/prompts_input.json"
    output_jsonl_path = "data/inputs/batch_tasks.jsonl"
    
    os.makedirs("data/inputs", exist_ok=True)
    
    if os.path.exists(input_path):
        prepare_batch_file(input_path, output_jsonl_path)
        run_batch_pipeline()
    else:
        print(f"[WAITING] Awaiting prompt file at: '{input_path}'")
        print("[ACTION] You can create a temporary 2-line 'prompts_input.json' file to test locally.")