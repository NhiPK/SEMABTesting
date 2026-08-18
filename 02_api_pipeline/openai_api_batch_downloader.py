import os
import json
import time
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

def json_for_csv(value):
    """
    Store list/dict metadata as valid JSON strings inside the CSV.
    """
    return json.dumps(value, ensure_ascii=False)

def check_and_download_batch(batch_job_id):
    """
    Checks the status of the OpenAI Batch Job.
    Downloads and parses the output into a clean CSV once completed.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or "YOUR_ACTUAL" in api_key:
        print("[ERROR] OpenAI API Key is missing in your .env file!")
        return

    client = OpenAI(api_key=api_key)
    
    print(f"Retrieving status for Batch Job: {batch_job_id}...")
    
    while True:
        batch_job = client.batches.retrieve(batch_job_id)
        status = batch_job.status
        print(f"[{time.strftime('%H:%M:%S')}] Current Status: {status}")
        
        if status == "completed":
            print("\n[SUCCESS] Batch processing completed! Downloading results...")
            output_file_id = batch_job.output_file_id
            
            file_response = client.files.content(output_file_id)
            raw_responses = file_response.text.strip().split("\n")
            
            parsed_results = []
            
            for line in raw_responses:
                if not line:
                    continue
                data = json.loads(line)
                
                # Unpack the compressed metadata from custom_id
                metadata = json.loads(data["custom_id"])
                
                try:
                    raw_content = data["response"]["body"]["choices"][0]["message"]["content"].strip().lower()
                except (KeyError, TypeError):
                    raw_content = "error"
                
                if "case 1" in raw_content or "case1" in raw_content:
                    label = 0
                elif "case 2" in raw_content or "case2" in raw_content:
                    label = 1
                else:
                    label = -1  # Excluded invalid answers
                
                # Build a converter-compatible row with both metadata and the LLM choice.
                parsed_results.append({
                    "scenario_id": metadata.get("scenario_id", metadata.get("scen_id")),
                    "persona_group": metadata.get("persona_group", metadata.get("persona")),
                    "label": label,
                    "is_interventionism": metadata.get("is_interventionism", metadata.get("attr_int", 0)),
                    "is_in_car": metadata.get("is_in_car", metadata.get("attr_in_car", 0)),
                    "is_law": metadata.get("is_law", metadata.get("attr_law", 0)),
                    "scenario_dimension": metadata.get("scenario_dimension", metadata.get("attr_dimension", "unknown")),
                    "scenario_dimension_group_type": json_for_csv(
                        metadata.get("scenario_dimension_group_type", metadata.get("attr_group_type", []))
                    ),
                    "count_dict_1": json_for_csv(
                        metadata.get("count_dict_1", metadata.get("attr_count_dict_1", {}))
                    ),
                    "count_dict_2": json_for_csv(
                        metadata.get("count_dict_2", metadata.get("attr_count_dict_2", {}))
                    ),
                    "traffic_light_pattern": json_for_csv(
                        metadata.get("traffic_light_pattern", metadata.get("attr_traffic_light_pattern", []))
                    ),
                    "llm_response_text": raw_content
                })
            
            # Save directly to root 'outputs' folder for GitHub syncing
            df = pd.DataFrame(parsed_results)
            os.makedirs("outputs", exist_ok=True)
            df.to_csv("outputs/llm_responses.csv", index=False)
            print(f"Cleaned dataset saved successfully to: outputs/llm_responses.csv")
            break
            
        elif status in ["failed", "expired", "cancelled"]:
            print(f"\n[ERROR] Batch job ended with terminal status: {status}")
            if batch_job.errors:
                print(f"Error Details: {batch_job.errors}")
            break
            
        else:
            print("Job is still processing. Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    # Replace with the real Job ID returned by api_batch_uploader.py
    TEST_BATCH_ID = "batch_replace_this_with_real_id" 
    check_and_download_batch(TEST_BATCH_ID)