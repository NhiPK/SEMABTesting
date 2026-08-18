import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

def prepare_batch_requests(input_json_path, output_jsonl_path, mapping_json_path):
    print(f"Preparing Anthropic batch requests from '{input_json_path}'...")
    
    requests = []
    metadata_mapping = {}
    
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for idx, item in enumerate(data):
        # Anthropic custom_id constraint: max 64 characters and must match ^[a-zA-Z0-9_-]+$
        safe_scen_id = str(item.get("scenario_id", idx)).replace(" ", "_").replace(":", "")
        custom_id = f"req_{idx}_{safe_scen_id}"[:64]
        
        metadata = {
            "scenario_id": item.get("scenario_id"),
            "persona_group": item.get("persona_group", "none"),
            "is_interventionism": item.get("attr_intervention", 0),
            "is_in_car": item.get("attr_in_car", 0),
            "is_law": item.get("attr_law", 0),
            "scenario_dimension": item.get("attr_dimension", "unknown"),
            "scenario_dimension_group_type": item.get("attr_scenario_dimension_group_type", []),
            "count_dict_1": item.get("attr_count_dict_1", {}),
            "count_dict_2": item.get("attr_count_dict_2", {}),
            "traffic_light_pattern": item.get("attr_traffic_light_pattern", []),
        }
        
        # Save metadata to local dict
        metadata_mapping[custom_id] = metadata
        
        persona_prompt = item.get("persona_prompt", "")
        persona_prefix = f"{persona_prompt}\n" if persona_prompt else ""
        
        system_content = (
            f"{persona_prefix}"
            "CRITICAL: You must choose one case. Do not explain your reasoning. "
            "Respond strictly in this exact format: 'Case 1' or 'Case 2'."
        )
        
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 5,
                "temperature": 0.0,
                "system": system_content,
                "messages": [
                    {
                        "role": "user", 
                        "content": item.get('scenario_text', '')
                    }
                ]
            }
        })
        
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
            
    with open(mapping_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata_mapping, f, indent=2, ensure_ascii=False)
        
    print(f"Preparation complete! {len(requests)} requests ready.")
    print(f"Local metadata mapping saved to: '{mapping_json_path}'")
    return requests

def run_batch_pipeline(requests):
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key or "YOUR_ACTUAL" in api_key or api_key.strip() == "":
        print("\n[INFO] Anthropic API Key is missing or not set in the '.env' file.")
        print("[INFO] Batch configuration prepared successfully. Ready to run once the API key is provided!\n")
        return

    client = Anthropic(api_key=api_key)

    print(f"Uploading and creating Anthropic Message Batch with {len(requests)} requests...")
    try:
        # Submit requests list directly. Note: Anthropic allows max 10,000 requests per batch.
        batch_job = client.messages.batches.create(
            requests=requests
        )
        print("\n[SUCCESS] Batch Job successfully submitted!")
        print(f"Batch Job ID: {batch_job.id}")
        print("Save this Job ID to retrieve the dataset using the downloader script once completed.")
    except Exception as e:
        print(f"\n[ERROR] Failed to create Anthropic Batch: {e}")

if __name__ == "__main__":
    os.makedirs("data/inputs", exist_ok=True)
    
    input_all = "data/inputs/scenarios_all.json"
    input_sample = "data/inputs/scenarios_sample.json"
    
    if os.path.exists(input_all):
        chosen_input = input_all
        output_jsonl_path = "data/inputs/sonnet_batch_tasks_all.jsonl"
        mapping_json_path = "data/inputs/sonnet_metadata_mapping_all.json"
    elif os.path.exists(input_sample):
        chosen_input = input_sample
        output_jsonl_path = "data/inputs/sonnet_batch_tasks_sample.jsonl"
        mapping_json_path = "data/inputs/sonnet_metadata_mapping_sample.json"
    else:
        chosen_input = None
        print(f"[WAITING] Awaiting scenario file at: '{input_all}' or '{input_sample}'")

    if chosen_input:
        requests = prepare_batch_requests(chosen_input, output_jsonl_path, mapping_json_path)
        
        if len(requests) > 10000:
            print("[WARNING] Anthropic Message Batches support a maximum of 10,000 requests per batch.")
            print(f"[WARNING] Truncating from {len(requests)} down to 10,000.")
            requests = requests[:10000]
            
        run_batch_pipeline(requests)
