import os
import re
import pandas as pd

def parse_choice_regex(text):
    """
    Parses LLM text output into binary choices using strict Regex boundaries:
    - Case 1 -> 1
    - Case 2 -> 0
    - Refusal/Ambiguous/Invalid -> -1
    """
    if not isinstance(text, str):
        return -1
    
    clean_text = text.strip().lower()
    
    # Matches 'case 1', 'case1', 'option 1', or standalone '1'
    pattern_case_1 = re.compile(r'\bcase\s*1\b|\boption\s*1\b')
    pattern_case_2 = re.compile(r'\bcase\s*2\b|\boption\s*2\b')
    
    match_1 = bool(pattern_case_1.search(clean_text))
    match_2 = bool(pattern_case_2.search(clean_text))
    
    # Disambiguation logic
    if match_1 and not match_2:
        return 1
    elif match_2 and not match_1:
        return 0
    else:
        return -1  # Ambiguous, missing, or refusal output

def process_llm_responses(input_path="outputs/llm_responses.csv", output_path="outputs/llm_responses_parsed.csv"):
    """
    Loads raw LLM responses from the outputs folder, parses the choices,
    and exports a sanitized dataset ready for AMCE calculation.
    """
    if not os.path.exists(input_path):
        print(f"[ERROR] Target file not found at: '{input_path}'")
        print("[ACTION] Please run the downloader script first to fetch raw responses.")
        return

    print(f"Loading raw dataset from: '{input_path}'...")
    df = pd.read_csv(input_path)
    
    if "llm_response_text" not in df.columns:
        print("[ERROR] Column 'llm_response_text' is missing from the dataset.")
        return

    # Apply Regex parser
    print("Parsing text responses into binary choices (1 / 0)...")
    df["llm_choice"] = df["llm_response_text"].apply(parse_choice_regex)
    
    # Calculate dataset metrics
    total_rows = len(df)
    valid_rows = (df["llm_choice"] != -1).sum()
    invalid_rows = total_rows - valid_rows
    valid_rate = (valid_rows / total_rows * 100) if total_rows > 0 else 0

    print("\nParsing Summary")
    print(f"Total Rows Processed : {total_rows}")
    print(f"Valid Choices (1/0)  : {valid_rows} ({valid_rate:.2f}%)")
    print(f"Invalid / Refusals   : {invalid_rows}")

    # Export clean output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Clean parsed dataset saved to: '{output_path}'\n")

if __name__ == "__main__":
    # Runs post-processing on the default outputs directory
    process_llm_responses()