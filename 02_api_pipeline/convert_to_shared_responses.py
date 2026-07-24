import argparse
import json

import pandas as pd


CROSSING_SIGNAL = {
    "NA": 0,
    "green": 1,
    "red": 2,
}

SCENARIO_TYPE = {
    "species": "Species",
    "social_value": "Social Value",
    "gender": "Gender",
    "age": "Age",
    "fitness": "Fitness",
    "utilitarianism": "Utilitarian",
    "random": "Random",
}

ATTRIBUTE_LEVEL = {
    "species": {
        "human": "Hoomans",
        "pet": "Pets",
    },
    "social_value": {
        "lower": "Low",
        "higher": "High",
    },
    "gender": {
        "female": "Female",
        "male": "Male",
    },
    "age": {
        "younger": "Young",
        "older": "Old",
    },
    "fitness": {
        "lower": "Fat",
        "higher": "Fit",
    },
    "utilitarianism": {
        "less": "Less",
        "more": "More",
    },
    "random": {
        "random": "Rand",
    },
}

PERSONA_COUNTRY3 = {
    "Neutral": "",
    "West_American": "USA",
    "West_Brazilian": "BRA",
    "West_German": "DEU",
    "West_British": "GBR",
    "West_Russian": "RUS",
    "West_Canadian": "CAN",
    "West_Italian": "ITA",
    "West_Australian": "AUS",
    "West_Polish": "POL",
    "West_Spanish": "ESP",
    "East_Japanese": "JPN",
    "East_Korean": "KOR",
    "East_Indian": "IND",
    "East_Chinese": "CHN",
    "East_HongKonger": "HKG",
    "East_Taiwanese": "TWN",
    "East_Indonesian": "IDN",
    "East_Malaysian": "MYS",
    "East_SaudiArabian": "SAU",
    "East_Emirati": "ARE",
}

CHARACTERS = [
    "man", "woman", "pregnant woman", "baby", "elderly man", "elderly woman",
    "boy", "girl", "homeless person", "large woman", "large man", "criminal",
    "male executive", "female executive", "female athlete", "male athlete",
    "female doctor", "male doctor", "dog", "cat",
]

CHARACTER_COLUMNS = {
    "man": "Man",
    "woman": "Woman",
    "pregnant woman": "Pregnant",
    "baby": "Stroller",
    "elderly man": "OldMan",
    "elderly woman": "OldWoman",
    "boy": "Boy",
    "girl": "Girl",
    "homeless person": "Homeless",
    "large woman": "LargeWoman",
    "large man": "LargeMan",
    "criminal": "Criminal",
    "male executive": "MaleExecutive",
    "female executive": "FemaleExecutive",
    "female athlete": "FemaleAthlete",
    "male athlete": "MaleAthlete",
    "female doctor": "FemaleDoctor",
    "male doctor": "MaleDoctor",
    "dog": "Dog",
    "cat": "Cat",
}

OUTPUT_COLUMNS = [
    "ResponseID", "ExtendedSessionID", "UserID", "ScenarioOrder", "Intervention",
    "PedPed", "Barrier", "CrossingSignal", "AttributeLevel", "ScenarioTypeStrict",
    "ScenarioType", "DefaultChoice", "NonDefaultChoice", "DefaultChoiceIsOmission",
    "NumberOfCharacters", "DiffNumberOFCharacters", "Saved", "Template",
    "DescriptionShown", "LeftHand", "UserCountry3", "PersonaGroup", "PersonaCluster",
    "PersonaNationality", "Man", "Woman", "Pregnant", "Stroller", "OldMan",
    "OldWoman", "Boy", "Girl", "Homeless", "LargeWoman", "LargeMan", "Criminal",
    "MaleExecutive", "FemaleExecutive", "FemaleAthlete", "MaleAthlete", "FemaleDoctor",
    "MaleDoctor", "Dog", "Cat",
]


def parse_json_cell(value):
    if isinstance(value, (dict, list)):
        return value
    if pd.isna(value):
        return {} if value == "" else []
    return json.loads(value)


def character_counts(count_dict):
    return {CHARACTER_COLUMNS[key]: count_dict.get(key, 0) for key in CHARACTERS}


def persona_metadata(persona_group):
    if persona_group == "Neutral":
        return "", "Neutral", "Neutral"

    if "_" not in persona_group:
        return PERSONA_COUNTRY3.get(persona_group, ""), "Unknown", persona_group

    cluster, nationality = persona_group.split("_", 1)
    return PERSONA_COUNTRY3.get(persona_group, ""), cluster, nationality


def build_profile(row, index, group_number):
    group_types = parse_json_cell(row["scenario_dimension_group_type"])
    traffic_light_pattern = parse_json_cell(row["traffic_light_pattern"])
    count_dict_1 = parse_json_cell(row["count_dict_1"])
    count_dict_2 = parse_json_cell(row["count_dict_2"])

    scenario_dimension = row["scenario_dimension"]
    ped_ped = int(not bool(row["is_in_car"]))
    persona_group = row.get("persona_group", "none")
    country3, persona_cluster, persona_nationality = persona_metadata(persona_group)

    if group_number == 1:
        count_dict = count_dict_1
        intervention = int(row["is_interventionism"])
        barrier = 0 if ped_ped else 1
        crossing_signal = CROSSING_SIGNAL[traffic_light_pattern[0]] if ped_ped else 0
        saved = int(row["label"] != 0)
        left_hand = 1
        attribute_group = group_types[0]
    else:
        count_dict = count_dict_2
        intervention = int(not bool(row["is_interventionism"]))
        barrier = 0
        crossing_signal = CROSSING_SIGNAL[traffic_light_pattern[1]]
        saved = int(row["label"] != 1)
        left_hand = 0
        attribute_group = group_types[1]

    profile = {
        "ResponseID": f"res_{index:08}_{group_number}",
        "ExtendedSessionID": "chatbot_extended",
        "UserID": "chatbot",
        "ScenarioOrder": 0,
        "Intervention": intervention,
        "PedPed": ped_ped,
        "Barrier": barrier,
        "CrossingSignal": crossing_signal,
        "Saved": saved,
        "NumberOfCharacters": sum(count_dict.values()),
        "DiffNumberOFCharacters": abs(sum(count_dict_1.values()) - sum(count_dict_2.values())),
        "Template": "desktop",
        "DescriptionShown": 1,
        "LeftHand": left_hand,
        "UserCountry3": country3,
        "PersonaGroup": persona_group,
        "PersonaCluster": persona_cluster,
        "PersonaNationality": persona_nationality,
        "ScenarioType": SCENARIO_TYPE[scenario_dimension],
        "ScenarioTypeStrict": SCENARIO_TYPE[scenario_dimension],
        "AttributeLevel": ATTRIBUTE_LEVEL[scenario_dimension][attribute_group],
        "DefaultChoice": None,
        "NonDefaultChoice": None,
        "DefaultChoiceIsOmission": None,
    }
    profile.update(character_counts(count_dict))
    return profile


def convert(input_path, output_path):
    df = pd.read_csv(input_path)
    df = df[df["label"] >= 0].reset_index(drop=True)

    shared_responses = []
    for index, row in df.iterrows():
        shared_responses.append(build_profile(row, index, 1))
        shared_responses.append(build_profile(row, index, 2))

    output = pd.DataFrame(shared_responses)
    output = output[OUTPUT_COLUMNS]
    output.to_csv(output_path, index=False)
    print(f"Saved {len(output)} profile rows to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/llm_responses.csv")
    parser.add_argument("--output", default="outputs/shared_responses_llm.csv")
    args = parser.parse_args()
    convert(args.input, args.output)


if __name__ == "__main__":
    main()