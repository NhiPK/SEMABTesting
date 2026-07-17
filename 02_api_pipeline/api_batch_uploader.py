import os
import json
from openai import OpenAI
from dotenv import load_dotenv

def prepare_batch_file(input_json_path, output_jsonl_path):
    """
    Converts JSON prompt file into JSONL format 
    as required by the OpenAI Batch API specification.
    """
    print(f"Converting '{input_json_path}' to Batch format ('{output_jsonl_path}')...")
    
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for item in data:
            # Safely get persona metadata or fall back to "none"
            metadata = {
                "scen_id": item["scenario_id"],
                "persona": item.get("persona_group", "none"),
                "attr_int": item.get("attr_intervention", 0),
                "attr_gen": item.get("attr_gender", 0),
                "attr_age": item.get("attr_age", 0),
                "attr_law": item.get("attr_law", 0)
            }
            custom_id_string = json.dumps(metadata)

            # Check if there is a persona prompt, otherwise leave it empty
            persona_prompt = item.get("persona_prompt", "")
            persona_prefix = f"{persona_prompt}\n" if persona_prompt else ""

            system_content = (
                f"{persona_prefix}"
                "CRITICAL: You must choose one case. Do not explain your reasoning. "
                "Respond strictly in this exact format: 'Case 1' or 'Case 2'."
            )

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
                            "content": system_content
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


def run_batch_pipeline(batch_file_path):
    """
    Uploads the specified JSONL file to OpenAI servers and triggers background batch execution.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or "YOUR_ACTUAL" in api_key or api_key.strip() == "":
        print(f"\n[INFO] OpenAI API Key is missing or not set in the '.env' file.")
        print(f"[INFO] Generated '{batch_file_path}' successfully. Ready to run once the API key is provided!\n")
        return

    client = OpenAI(api_key=api_key)

    print(f"Uploading batch prompt file '{batch_file_path}' to OpenAI...")
    batch_input_file = client.files.create(
        file=open(batch_file_path, "rb"),
        purpose="batch"
    )
    
    print(f"Creating batch job with File ID: {batch_input_file.id}")
    batch_job = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": f"Trolley Problem Experiment - {os.path.basename(batch_file_path)}"
        }
    )
    
    print("\n[SUCCESS] Batch Job successfully submitted!")
    print(f"Batch Job ID: {batch_job.id}")
    print("Save this Job ID to retrieve the dataset using the downloader script once completed.")


if __name__ == "__main__":
    os.makedirs("data/inputs", exist_ok=True)
    
    # Define potential input paths
    input_all = "data/inputs/scenarios_all.json"
    input_sample = "data/inputs/scenarios_sample.json"
    
    # Check which input file is available and set the matching output name
    if os.path.exists(input_all):
        chosen_input = input_all
        output_jsonl_path = "data/inputs/batch_tasks_all.jsonl"
    elif os.path.exists(input_sample):
        chosen_input = input_sample
        output_jsonl_path = "data/inputs/batch_tasks_sample.jsonl"
    else:
        chosen_input = None
        output_jsonl_path = None

    if chosen_input:
        prepare_batch_file(chosen_input, output_jsonl_path)
        run_batch_pipeline(output_jsonl_path)
    else:
        print(f"[WAITING] Awaiting scenario file at: '{input_all}' or '{input_sample}'")