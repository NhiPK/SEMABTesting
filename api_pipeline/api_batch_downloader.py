import os
import json
import time
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

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
                    choice = 1
                elif "case 2" in raw_content or "case2" in raw_content:
                    choice = 0
                else:
                    choice = -1  # Excluded invalid answers
                
                # Build the row with both metadata attributes AND the LLM choice
                parsed_results.append({
                    "scenario_id": metadata["scen_id"],
                    "persona_group": metadata["persona"],
                    "attr_intervention": metadata["attr_int"],
                    "attr_gender": metadata["attr_gen"],
                    "attr_age": metadata["attr_age"],
                    "attr_law": metadata["attr_law"],
                    "llm_response_text": raw_content,
                    "llm_choice": choice
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