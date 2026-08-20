import os
import json
import time
import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

def json_for_csv(value):
    """
    Store list/dict metadata as valid JSON strings inside the CSV.
    """
    return json.dumps(value, ensure_ascii=False)

def check_and_download_batch(batch_job_id, mapping_json_path):
    """
    Checks the status of the Anthropic Batch Job.
    Downloads and parses the output into a clean CSV using the local metadata mapping.
    """
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key or "YOUR_ACTUAL" in api_key:
        print("[ERROR] Anthropic API Key is missing in your .env file!")
        return

    client = Anthropic(api_key=api_key)
    
    if not os.path.exists(mapping_json_path):
        print(f"[ERROR] Metadata mapping file not found at: {mapping_json_path}")
        print("Please ensure you run the uploader script first and provide the correct path.")
        return

    with open(mapping_json_path, "r", encoding="utf-8") as f:
        metadata_mapping = json.load(f)
        
    print(f"Retrieving status for Anthropic Batch Job: {batch_job_id}...")
    
    while True:
        try:
            batch_job = client.messages.batches.retrieve(batch_job_id)
            status = batch_job.processing_status
            print(f"[{time.strftime('%H:%M:%S')}] Current Status: {status}")
            
            if status == "ended":
                print("\n[SUCCESS] Batch processing completed! Downloading results...")
                
                results = client.messages.batches.results(batch_job_id)
                parsed_results = []
                
                for result in results:
                    custom_id = result.custom_id
                    metadata = metadata_mapping.get(custom_id, {})
                    
                    try:
                        if result.result.type == "succeeded":
                            raw_content = result.result.message.content[0].text.strip().lower()
                        elif result.result.type == "errored":
                            err = result.result.error
                            error_msg = getattr(err, 'message', str(err))
                            error_type = getattr(err, 'type', 'unknown_error')
                            
                            raw_content = f"api_error: {error_type}"
                            print(f"[API ERROR] Scenario {custom_id} failed: {error_msg}")
                        else:
                            raw_content = f"unknown_status: {result.result.type}"
                    except Exception as e:
                        raw_content = f"parsing_error: {str(e)}"
                    
                    if "case 1" in raw_content or "case1" in raw_content:
                        label = 0
                    elif "case 2" in raw_content or "case2" in raw_content:
                        label = 1
                    else:
                        label = -1 
                    
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
                
                df = pd.DataFrame(parsed_results)
                os.makedirs("outputs", exist_ok=True)
                output_file = "outputs/sonnet_llm_responses.csv"
                df.to_csv(output_file, index=False)
                print(f"Cleaned dataset saved successfully to: {output_file}")
                break
                
            elif status in ["canceled", "expired", "errored"]:
                print(f"\n[ERROR] Batch job ended with terminal status: {status}")
                break
                
            else:
                print("Job is still processing. Retrying in 60 seconds...")
                time.sleep(60)
                
        except Exception as e:
            print(f"[ERROR] Exception occurred: {e}")
            break

if __name__ == "__main__":
    TEST_BATCH_ID = "..." 
    
    mapping_all = "data/inputs/sonnet_metadata_mapping_all.json"
    mapping_sample = "data/inputs/sonnet_metadata_mapping_sample.json"
    
    if os.path.exists(mapping_all):
        selected_mapping = mapping_all
    elif os.path.exists(mapping_sample):
        selected_mapping = mapping_sample
    else:
        selected_mapping = mapping_all
        
    check_and_download_batch(TEST_BATCH_ID, selected_mapping)