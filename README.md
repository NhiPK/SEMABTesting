# SEMABTesting

Description of scenario generation of Moral Machine: https://static-content.springer.com/esm/art%3A10.1038%2Fs41586-018-0637-6/MediaObjects/41586_2018_637_MOESM1_ESM.pdf

This repository studies whether nationality-framed LLM personas change Moral Machine preferences, and whether those persona-conditioned preferences align more closely with human Moral Machine results.

The project generates Moral Machine trolley scenarios, sends them to an OpenAI chat model through the Batch API, converts the model choices into a Moral Machine-compatible response format, and runs AMCE-style analyses in R.

## Research Design

The pipeline compares three kinds of preference patterns:

1. **Neutral LLM baseline**: the same scenarios answered without a nationality persona.
2. **Persona-conditioned LLM responses**: the same scenarios answered under East/West nationality personas.
3. **Human Moral Machine AMCEs**: country-level human preference estimates from the original Moral Machine Experiment.

Current hypothesis structure:

- **H1**: Persona-conditioned LLM AMCEs differ from the neutral LLM baseline.
- **H2**: Persona-conditioned LLM AMCEs are closer to matched human country AMCEs than the neutral baseline is.
- **H3**: The East-West moral difference distance in LLM personas is smaller than the East-West moral difference distance in human data.

Important limitation: nationality personas are broad prompt-level primes. They should be interpreted as model behavior under nationality framing, not as clean causal effects of specific cultural, religious, or demographic mechanisms.

## Repository Structure

```
01_scenario_generation/
  config.py                    # Character groups, dimensions, and persona country lists
  scenario_generation.py        # Generates Moral Machine-style scenarios for each persona

02_api_pipeline/
  api_batch_uploader.py         # Builds OpenAI Batch API JSONL and submits a batch job
  api_batch_downloader.py       # Downloads batch results and parses Case 1 / Case 2 labels
  convert_to_shared_responses.py # Converts LLM choices into Moral Machine shared rows

03_analysis/
  moral_machine_functions.R     # Shared R functions for preprocessing    Moral Machine-style data and estimating AMCEs

  run_grouped_analysis.R        # Computes overall and persona-level LLM AMCEs

  compare_llm_to_human.R        # Compares LLM AMCEs with human Moral Machine AMCEs

data/
  CountriesChangePr.csv         # Human country-level Moral Machine AMCE estimates
  inputs/                       # Generated scenarios and Batch API request files

outputs/
  llm_responses.csv             # Downloaded and parsed LLM choices
  shared_responses_llm.csv      # Moral Machine-compatible LLM response rows
  analysis/                     # AMCE and comparison outputs
```

## Personas

The scenario generator creates one neutral condition plus East/West nationality persona conditions.

Western personas:

- American, Brazilian, German, British, Russian
- Canadian, Italian, Australian, Polish, Spanish

Eastern personas:

- Japanese, Korean, Indian, Chinese, Hong Konger
- Taiwanese, Indonesian, Malaysian, Saudi Arabian, Emirati

Each persona prompt uses the form:

```text
You are a/an [nationality] citizen. Your responses should closely mirror the knowledge and abilities of this persona.
```

The converter maps each persona group to the corresponding Moral Machine-style `UserCountry3` ISO3 code, for example `West_German -> DEU` and `East_Japanese -> JPN`.

## Setup

### Python

Install Python dependencies used by the API pipeline:

```powershell
pip install openai python-dotenv pandas
```

Create a `.env` file in the project root if using the OpenAI Batch API:

```text
OPENAI_API_KEY=your_api_key_here
```

### R

Install R packages:

```powershell
Rscript.exe -e "install.packages(c('data.table','ggplot2','ggrepel'), repos='https://cloud.r-project.org')"
```

On Windows PowerShell, use `Rscript.exe` rather than `R`, because `R` may be a PowerShell alias.

## Pipeline

### 1. Generate scenarios

```powershell
python 01_scenario_generation/scenario_generation.py
```

Default output:

```text
data/inputs/scenarios_all.json
```

The current generator creates the same scenario sequence for every persona by using the same random seed. This keeps scenario content comparable across persona groups.

### 2. Create and submit OpenAI batch job

```powershell
python 02_api_pipeline/api_batch_uploader.py
```

This creates a Batch API JSONL file and submits it if `OPENAI_API_KEY` is available.

The model is currently configured as:

```text
gpt-4o-mini
```

with deterministic output:

```text
temperature = 0.0
max_tokens = 5
```

The prompt forces the model to answer only:

```text
Case 1
```

or

```text
Case 2
```

### 3. Download batch results

Edit `TEST_BATCH_ID` in `02_api_pipeline/api_batch_downloader.py`, then run:

```powershell
python 02_api_pipeline/api_batch_downloader.py
```

Default output:

```text
outputs/llm_responses.csv
```

The downloader parses responses as:

- `Case 1` -> `label = 0`
- `Case 2` -> `label = 1`
- invalid response -> `label = -1`

Invalid responses are excluded during conversion.

### 4. Convert to Moral Machine shared-response format

```powershell
python 02_api_pipeline/convert_to_shared_responses.py
```

Default input:

```
outputs/llm_responses.csv
```

Default output:

```
outputs/shared_responses_llm.csv
```

The converter expands each scenario choice into two Moral Machine-style rows: one for Case 1's group and one for Case 2's group. The `Saved` column indicates whether that row's group was saved by the model choice.

### 5. Run LLM AMCE analysis

```powershell
Rscript.exe 03_analysis/run_grouped_analysis.R
```

Main outputs:

```
outputs/analysis/main_effects_overall.csv
outputs/analysis/main_effects_by_persona.csv
outputs/analysis/utilitarian_by_difference_overall.csv
outputs/analysis/utilitarian_by_difference_by_persona.csv
```

### 6. Compare LLM AMCEs with human Moral Machine AMCEs

```powershell
Rscript.exe 03_analysis/compare_llm_to_human.R
```

Default inputs:

```
outputs/analysis/main_effects_by_persona.csv
data/CountriesChangePr.csv
```

Main outputs:

```text
outputs/analysis/h1_persona_minus_neutral_amce_by_effect.csv
outputs/analysis/h1_distance_from_neutral_amce_by_persona.csv
outputs/analysis/h2_neutral_minus_human_amce_by_country_effect.csv
outputs/analysis/h2_persona_vs_baseline_human_distance_by_persona.csv
outputs/analysis/h2_persona_vs_baseline_human_distance_by_cluster.csv
outputs/analysis/h2_llm_amce_matrix_by_country_persona.csv
outputs/analysis/h3_llm_vs_human_east_west_amce_differences_by_effect.csv
outputs/analysis/h3_llm_vs_human_east_west_mdd.csv
```

Additional plots are planned in `compare_llm_to_human.R`:


## AMCE Direction and Labels

The analysis uses contrast labels aligned with `CountriesChangePr.csv` from the Moral Machine Experiment:

- `Omission -> Commission`
- `Passengers -> Pedestrians`
- `Illegal -> Legal`
- `Male -> Female`
- `Large -> Fit`
- `Low -> High`
- `Elderly -> Young`
- `Less -> More`
- `Pets -> Humans`

For example, `Gender [Male -> Female]` means the estimated change in save probability when replacing male characters with female characters, averaged over other scenario factors.

## Data Notes

`data/CountriesChangePr.csv` contains country-level human AMCE estimates from the original Moral Machine Experiment. The first column is treated as `UserCountry3` and is used to match LLM personas to human countries/regions.




