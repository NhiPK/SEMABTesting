import os
import json
import glob
import pandas as pd

def json_for_csv(value):
    return json.dumps(value, ensure_ascii=False)

def parse_and_merge_results(input_directory="outputs", final_csv_path="outputs/openai5_llm_responses.csv"):
    print(f"[INFO] Scanning '{input_directory}' for downloaded batch result files...")
    
    # Locate all JSONL files ending with '_results.jsonl'
    search_pattern = os.path.join(input_directory, "*_results.jsonl")
    result_files = glob.glob(search_pattern)
    
    if not result_files:
        print(f"[WARNING] No result files found matching the pattern: {search_pattern}")
        print("[INFO] Ensure the uploader pipeline has completely finished processing.")
        return
        
    parsed_results = []
    
    for file_path in result_files:
        print(f"[INFO] Parsing data from: {os.path.basename(file_path)}")
        
        with open(file_path, "r", encoding="utf-8") as raw_file:
            for line in raw_file:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # Unpack the compressed metadata from custom_id
                metadata = json.loads(data.get("custom_id", "{}"))
                
                try:
                    raw_content = data["response"]["body"]["choices"][0]["message"]["content"].strip().lower()
                except (KeyError, TypeError):
                    raw_content = "error"
                
                # Determine binary classification labels
                if "case 1" in raw_content or "case1" in raw_content:
                    label = 0
                elif "case 2" in raw_content or "case2" in raw_content:
                    label = 1
                else:
                    label = -1  # Exclude invalid formats
                
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
                
    # Transform list of dictionaries into a structured DataFrame
    df = pd.DataFrame(parsed_results)
    
    # Sort the dataset logically by scenario ID for cleaner analysis
    if "scenario_id" in df.columns:
        df = df.sort_values(by="scenario_id")
        
    os.makedirs(os.path.dirname(final_csv_path), exist_ok=True)
    df.to_csv(final_csv_path, index=False)
    
    print("-" * 50)
    print(f"[SUCCESS] Successfully combined {len(parsed_results)} scenario records.")
    print(f"[SUCCESS] Final dataset saved to: {final_csv_path}")
    print("-" * 50)

if __name__ == "__main__":
    parse_and_merge_results()