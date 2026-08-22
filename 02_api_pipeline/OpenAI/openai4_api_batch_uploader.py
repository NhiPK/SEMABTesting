import os
import json
import math
import time
from openai import OpenAI
from dotenv import load_dotenv

def prepare_batch_file(input_json_path, output_jsonl_path):
    print(f"[INFO] Converting '{input_json_path}' to Batch format ('{output_jsonl_path}')...")
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for item in data:
            metadata = {
                "scenario_id": item["scenario_id"],
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
            custom_id_string = json.dumps(metadata)

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
                    "temperature": 0.0,  
                    "max_tokens": 5,     
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": item['scenario_text']}
                    ]
                }
            }
            f.write(json.dumps(batch_request) + "\n")
    print("[INFO] Conversion complete!")

def split_jsonl_file(input_file_path, chunk_size=5000):
    print(f"\n[INFO] Splitting '{input_file_path}' into chunks of {chunk_size} lines...")
    output_directory = os.path.dirname(input_file_path)
    base_filename = os.path.basename(input_file_path).replace(".jsonl", "")

    with open(input_file_path, "r", encoding="utf-8") as source_file:
        all_lines = source_file.readlines()

    total_records = len(all_lines)
    total_batches = math.ceil(total_records / chunk_size)
    
    chunked_files = []
    for chunk_index in range(total_batches):
        start_index = chunk_index * chunk_size
        end_index = start_index + chunk_size
        batch_lines = all_lines[start_index:end_index]

        output_filepath = os.path.join(output_directory, f"{base_filename}_part_{chunk_index + 1}.jsonl")
        with open(output_filepath, "w", encoding="utf-8") as output_file:
            output_file.writelines(batch_lines)
            
        print(f"[INFO] Generated: {output_filepath} ({len(batch_lines)} records)")
        chunked_files.append(output_filepath)
        
    return chunked_files

def run_sequential_batches(chunked_files):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or "YOUR_ACTUAL" in api_key or api_key.strip() == "":
        print("\n[ERROR] OpenAI API Key is missing or not set in the '.env' file.")
        return

    client = OpenAI(api_key=api_key)

    for file_path in chunked_files:
        print(f"\n--- Starting Processing for {os.path.basename(file_path)} ---")
        
        print(f"[1/3] Uploading file to OpenAI servers...")
        with open(file_path, "rb") as f:
            batch_input_file = client.files.create(file=f, purpose="batch")
        
        print(f"[2/3] Creating batch job (File ID: {batch_input_file.id})...")
        batch_job = client.batches.create(
            input_file_id=batch_input_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"description": f"AMCE Trolley Problem - {os.path.basename(file_path)}"}
        )
        print(f"[INFO] Batch Job ID: {batch_job.id}")
        
        print(f"[3/3] Monitoring status. Do not close the terminal.")
        while True:
            current_batch = client.batches.retrieve(batch_job.id)
            status = current_batch.status
            print(f"[{time.strftime('%H:%M:%S')}] Status: {status}")

            if status == "completed":
                print(f"[SUCCESS] Batch {batch_job.id} completed successfully!")
                
                # Auto-download the results directly into the outputs folder
                result_file_id = current_batch.output_file_id
                if result_file_id:
                    result_content = client.files.content(result_file_id).text
                    output_name = file_path.replace("inputs", "outputs").replace(".jsonl", "_results.jsonl")
                    os.makedirs(os.path.dirname(output_name), exist_ok=True)
                    with open(output_name, "w", encoding="utf-8") as out_f:
                        out_f.write(result_content)
                    print(f"[INFO] Raw results saved to {output_name}")
                break
                
            elif status in ["failed", "expired", "cancelled"]:
                print(f"\n[ERROR] Batch terminated with status: {status}. Halting pipeline to prevent token waste.")
                return 
            
            # Pause for 60 seconds before pinging the API again
            time.sleep(60)

    print("\n[INFO] ALL FILES PROCESSED SUCCESSFULLY!")

if __name__ == "__main__":
    os.makedirs("data/inputs", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    input_all = "data/inputs/scenarios_all.json"
    input_sample = "data/inputs/scenarios_sample.json"
    
    if os.path.exists(input_all):
        chosen_input = input_all
        output_jsonl_path = "data/inputs/openai4_batch_tasks_all.jsonl"
    elif os.path.exists(input_sample):
        chosen_input = input_sample
        output_jsonl_path = "data/inputs/openai4_batch_tasks_sample.jsonl"
    else:
        chosen_input = None
        output_jsonl_path = None

    if chosen_input:
        prepare_batch_file(chosen_input, output_jsonl_path)
        
        # Split into safe chunks due to limited tokens from Ope
        chunk_files = split_jsonl_file(output_jsonl_path, chunk_size=3500)
        
        run_sequential_batches(chunk_files)
    else:
        print(f"[WAITING] Awaiting scenario file at: '{input_all}' or '{input_sample}'")