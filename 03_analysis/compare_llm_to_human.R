library(data.table)
ggplot2_available <- requireNamespace("ggplot2", quietly = TRUE)
ggrepel_available <- requireNamespace("ggrepel", quietly = TRUE)

args <- commandArgs(trailingOnly = TRUE)
llm_path <- ifelse(length(args) >= 1, args[[1]], "outputs/analysis/main_effects_by_persona.csv")
human_path <- ifelse(length(args) >= 2, args[[2]], "data/CountriesChangePr.csv")
output_dir <- ifelse(length(args) >= 3, args[[3]], "outputs/analysis")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

EFFECT_TO_HUMAN_COLUMNS <- list(
  "Intervention" = c(
    estimate = "[Omission -> Commission]: Estimates",
    se = "[Omission -> Commission]: se"
  ),
  "Relation to AV" = c(
    estimate = "[Passengers -> Pedestrians]: Estimates",
    se = "[Passengers -> Pedestrians]: se"
  ),
  "Law" = c(
    estimate = "Law [Illegal -> Legal]: Estimates",
    se = "Law [Illegal -> Legal]: se"
  ),
  "Gender" = c(
    estimate = "Gender [Male -> Female]: Estimates",
    se = "Gender [Male -> Female]: se"
  ),
  "Fitness" = c(
    estimate = "Fitness [Large -> Fit]: Estimates",
    se = "Fitness [Large -> Fit]: se"
  ),
  "Social Status" = c(
    estimate = "Social Status [Low -> High]: Estimates",
    se = "Social Status [Low -> High]: se"
  ),
  "Age" = c(
    estimate = "Age [Elderly -> Young]: Estimates",
    se = "Age [Elderly -> Young]: se"
  ),
  "No. Characters" = c(
    estimate = "No. Characters [Less -> More]: Estimates",
    se = "No. Characters [Less -> More]: se"
  ),
  "Species" = c(
    estimate = "Species [Pets -> Humans]: Estimates",
    se = "Species [Pets -> Humans]: se"
  )
)



## Reshape the human data to match the LLM data structure for comparison
human_raw <- fread(human_path, check.names = FALSE)
setnames(human_raw, old = names(human_raw)[1], new = "UserCountry3")

human_effects <- rbindlist(lapply(names(EFFECT_TO_HUMAN_COLUMNS), function(effect) {
  columns <- EFFECT_TO_HUMAN_COLUMNS[[effect]]
  data.table(
    UserCountry3 = human_raw$UserCountry3,
    Effect = effect,
    HumanEstimate = human_raw[[columns[["estimate"]]]],
    HumanSE = human_raw[[columns[["se"]]]]
  )
}))

llm_effects <- fread(llm_path)
comparison <- merge(
  llm_effects,
  human_effects,
  by = c("UserCountry3", "Effect"),
  all.x = TRUE
)
comparison[, DifferenceFromHuman := Estimate - HumanEstimate]
comparison[, AbsDifferenceFromHuman := abs(DifferenceFromHuman)]
comparison[, SquaredDifferenceFromHuman := DifferenceFromHuman^2]

## Hypothesis 1: Personas will differ from the baseline (Neutral) persona in their moral preferences

neutral_effects <- llm_effects[PersonaGroup == "Neutral", .(
  Effect,
  NeutralEstimate = Estimate,
  NeutralSE = SE,
  NeutralN = N
)]

persona_vs_neutral <- merge(
  llm_effects[PersonaGroup != "Neutral"],
  neutral_effects,
  by = "Effect",
  all.x = TRUE
)
persona_vs_neutral[, DifferenceFromNeutral := Estimate - NeutralEstimate]
persona_vs_neutral[, AbsDifferenceFromNeutral := abs(DifferenceFromNeutral)]
fwrite(persona_vs_neutral, file.path(output_dir, "h1_persona_minus_neutral_amce_by_effect.csv"))

h1_distance_from_baseline <- persona_vs_neutral[
  !is.na(NeutralEstimate),
  .(
    EuclideanDistanceFromNeutral = sqrt(sum((Estimate - NeutralEstimate)^2)),
    RMSEFromNeutral = sqrt(mean((Estimate - NeutralEstimate)^2)),
    MeanAbsoluteDifferenceFromNeutral = mean(abs(Estimate - NeutralEstimate)),
    ComparedEffects = .N
  ),
  by = .(PersonaGroup, UserCountry3, PersonaCluster, PersonaNationality)
]
setorder(h1_distance_from_baseline, EuclideanDistanceFromNeutral)
fwrite(h1_distance_from_baseline, file.path(output_dir, "h1_distance_from_neutral_amce_by_persona.csv"))

## Hypothesis 2: Persona prompts reduce distance to matched human country AMCEs compared with the neutral baseline

## H2-1: By country/region and each Moral Machine dimension
h2_persona_distance_to_human <- comparison[
  PersonaGroup != "Neutral" & !is.na(HumanEstimate),
  .(
    PersonaEuclideanDistanceToHuman = sqrt(sum(SquaredDifferenceFromHuman)),
    PersonaRMSEToHuman = sqrt(mean(SquaredDifferenceFromHuman)),
    PersonaMeanAbsoluteDifferenceToHuman = mean(AbsDifferenceFromHuman),
    ComparedEffects = .N
  ),
  by = .(PersonaGroup, UserCountry3, PersonaCluster, PersonaNationality)
]

persona_country_map <- unique(llm_effects[
  PersonaGroup != "Neutral",
  .(PersonaGroup, UserCountry3, PersonaCluster, PersonaNationality)
])

h2_baseline_effect_comparison <- merge(
  persona_country_map,
  human_effects,
  by = "UserCountry3",
  allow.cartesian = TRUE
)
h2_baseline_effect_comparison <- merge(
  h2_baseline_effect_comparison,
  neutral_effects,
  by = "Effect",
  all.x = TRUE
)
h2_baseline_effect_comparison[, BaselineDifferenceFromHuman := NeutralEstimate - HumanEstimate]
h2_baseline_effect_comparison[, BaselineAbsDifferenceFromHuman := abs(BaselineDifferenceFromHuman)]
h2_baseline_effect_comparison[, BaselineSquaredDifferenceFromHuman := BaselineDifferenceFromHuman^2]
fwrite(h2_baseline_effect_comparison, file.path(output_dir, "h2_neutral_minus_human_amce_by_country_effect.csv"))

## H2-2: Overall distance by country/region across all dimensions
h2_baseline_distance_to_human <- h2_baseline_effect_comparison[
  !is.na(NeutralEstimate) & !is.na(HumanEstimate),
  .(
    BaselineEuclideanDistanceToHuman = sqrt(sum(BaselineSquaredDifferenceFromHuman)),
    BaselineRMSEToHuman = sqrt(mean(BaselineSquaredDifferenceFromHuman)),
    BaselineMeanAbsoluteDifferenceToHuman = mean(BaselineAbsDifferenceFromHuman),
    ComparedEffects = .N
  ),
  by = .(PersonaGroup, UserCountry3, PersonaCluster, PersonaNationality)
]

h2_persona_vs_baseline_distance <- merge(
  h2_persona_distance_to_human,
  h2_baseline_distance_to_human,
  by = c("PersonaGroup", "UserCountry3", "PersonaCluster", "PersonaNationality"),
  suffixes = c("Persona", "Baseline")
)
h2_persona_vs_baseline_distance[, EuclideanDistanceImprovement := BaselineEuclideanDistanceToHuman - PersonaEuclideanDistanceToHuman]
h2_persona_vs_baseline_distance[, RMSEImprovement := BaselineRMSEToHuman - PersonaRMSEToHuman]
h2_persona_vs_baseline_distance[, MeanAbsoluteDifferenceImprovement := BaselineMeanAbsoluteDifferenceToHuman - PersonaMeanAbsoluteDifferenceToHuman]
h2_persona_vs_baseline_distance[, H2SupportedByEuclidean := PersonaEuclideanDistanceToHuman < BaselineEuclideanDistanceToHuman]
h2_persona_vs_baseline_distance[, H2SupportedByRMSE := PersonaRMSEToHuman < BaselineRMSEToHuman]
setorder(h2_persona_vs_baseline_distance, PersonaCluster, -EuclideanDistanceImprovement)
fwrite(h2_persona_vs_baseline_distance, file.path(output_dir, "h2_persona_vs_baseline_human_distance_by_persona.csv"))

h2_cluster_summary <- h2_persona_vs_baseline_distance[
  PersonaCluster %in% c("East", "West"),
  .(
    MeanPersonaEuclideanDistanceToHuman = mean(PersonaEuclideanDistanceToHuman, na.rm = TRUE),
    MeanBaselineEuclideanDistanceToHuman = mean(BaselineEuclideanDistanceToHuman, na.rm = TRUE),
    MeanEuclideanDistanceImprovement = mean(EuclideanDistanceImprovement, na.rm = TRUE),
    SharePersonasImproved = mean(H2SupportedByEuclidean, na.rm = TRUE),
    PersonasCompared = .N
  ),
  by = PersonaCluster
]
h2_cluster_summary[, H2SupportedAtClusterLevel := MeanPersonaEuclideanDistanceToHuman < MeanBaselineEuclideanDistanceToHuman]
fwrite(h2_cluster_summary, file.path(output_dir, "h2_persona_vs_baseline_human_distance_by_cluster.csv"))

## Prepare wide LLM AMCE matrix for PCA and proposal-style descriptive analysis:
## rows = country-personas, columns = Moral Machine AMCE dimensions
preference_matrix <- dcast(
  comparison[PersonaGroup != "Neutral" & !is.na(HumanEstimate)],
  PersonaGroup + UserCountry3 + PersonaCluster + PersonaNationality ~ Effect,
  value.var = "Estimate"
)
fwrite(preference_matrix, file.path(output_dir, "h2_llm_amce_matrix_by_country_persona.csv"))

## Hypothesis 3: LLM East-West moral difference distance is smaller than human East-West distance 
## Prepare LLM East and West mean AMCEs for the H3 MDD calculation
cluster_effects <- llm_effects[PersonaCluster %in% c("East", "West"), .(
  ClusterEstimate = mean(Estimate, na.rm = TRUE),
  Personas = uniqueN(PersonaGroup),
  EffectRows = .N
), by = .(PersonaCluster, Effect, ReferenceLevel, ComparedLevel, Contrast)]
fwrite(cluster_effects, file.path(output_dir, "h3_llm_main_effects_by_persona_cluster.csv"))

## Prepare LLM East-West AMCE differences for the H3 MDD calculation
cluster_wide <- dcast(
  cluster_effects,
  Effect + ReferenceLevel + ComparedLevel + Contrast ~ PersonaCluster,
  value.var = "ClusterEstimate"
)
if (all(c("East", "West") %in% names(cluster_wide))) {
  cluster_wide[, EastMinusWest := East - West]
  cluster_wide[, AbsEastMinusWest := abs(EastMinusWest)]
}

fwrite(cluster_wide, file.path(output_dir, "h3_llm_east_west_amce_differences_by_effect.csv"))

## H3: Compute human East-West AMCE differences using the same persona-country set
## This keeps the human comparison aligned with the countries/regions used in LLM personas
human_cluster_effects <- merge(
  persona_country_map[, .(UserCountry3, PersonaCluster)],
  human_effects,
  by = "UserCountry3",
  allow.cartesian = TRUE
)[PersonaCluster %in% c("East", "West"), .(
  HumanClusterEstimate = mean(HumanEstimate, na.rm = TRUE),
  Countries = uniqueN(UserCountry3),
  EffectRows = .N
), by = .(PersonaCluster, Effect)]
fwrite(human_cluster_effects, file.path(output_dir, "h3_human_main_effects_by_persona_cluster.csv"))

human_cluster_wide <- dcast(
  human_cluster_effects,
  Effect ~ PersonaCluster,
  value.var = "HumanClusterEstimate"
)
if (all(c("East", "West") %in% names(human_cluster_wide))) {
  human_cluster_wide[, HumanEastMinusWest := East - West]
  human_cluster_wide[, HumanAbsEastMinusWest := abs(HumanEastMinusWest)]
}
fwrite(human_cluster_wide, file.path(output_dir, "h3_human_east_west_amce_differences_by_effect.csv"))

## H3: Test whether LLM East-West moral difference distance is smaller than human East-West distance
## H3 is supported when LlmEastWestMDD < HumanEastWestMDD
h3_east_west_mdd_by_effect <- merge(
  cluster_wide[, .(Effect, ReferenceLevel, ComparedLevel, Contrast, LlmEastMinusWest = EastMinusWest, LlmAbsEastMinusWest = AbsEastMinusWest)],
  human_cluster_wide[, .(Effect, HumanEastMinusWest, HumanAbsEastMinusWest)],
  by = "Effect"
)
h3_east_west_mdd_by_effect[, AbsDifferenceGap := HumanAbsEastMinusWest - LlmAbsEastMinusWest]
fwrite(h3_east_west_mdd_by_effect, file.path(output_dir, "h3_llm_vs_human_east_west_amce_differences_by_effect.csv"))

h3_east_west_mdd <- h3_east_west_mdd_by_effect[
  !is.na(LlmEastMinusWest) & !is.na(HumanEastMinusWest),
  .(
    LlmEastWestMDD = sqrt(sum(LlmEastMinusWest^2)),
    HumanEastWestMDD = sqrt(sum(HumanEastMinusWest^2)),
    ComparedEffects = .N
  )
]
h3_east_west_mdd[, MDDDifference := HumanEastWestMDD - LlmEastWestMDD]
h3_east_west_mdd[, H3Supported := LlmEastWestMDD < HumanEastWestMDD]
fwrite(h3_east_west_mdd, file.path(output_dir, "h3_llm_vs_human_east_west_mdd.csv"))





## PCA analysis
## Uses the H2 wide LLM AMCE matrix created above


if (ggplot2_available && ggrepel_available && nrow(preference_matrix) >= 2) {
  llm_matrix <- as.data.frame(preference_matrix)
  row_labels <- llm_matrix$PersonaGroup
  effect_columns <- setdiff(
    names(llm_matrix),
    c("PersonaGroup", "UserCountry3", "PersonaCluster", "PersonaNationality")
  )
  pca_input <- llm_matrix[, effect_columns, drop = FALSE]
  rownames(pca_input) <- row_labels
  pca_input <- pca_input[complete.cases(pca_input), , drop = FALSE]

  if (nrow(pca_input) >= 2) {
    pca_result <- prcomp(pca_input, center = TRUE, scale. = FALSE)
    explained <- pca_result$sdev^2 / sum(pca_result$sdev^2)
    pca_plot <- as.data.frame(pca_result$x)
    pca_plot$PersonaGroup <- rownames(pca_plot)

    ggplot2::ggsave(
      file.path(output_dir, "h2_llm_persona_pca.png"),
      plot = ggplot2::ggplot(pca_plot, ggplot2::aes(x = PC1, y = PC2, label = PersonaGroup)) +
        ggplot2::geom_point(size = 3) +
        ggrepel::geom_label_repel(size = 3, max.overlaps = Inf) +
        ggplot2::labs(
          x = paste0("PC1 (", round(explained[1] * 100, 1), "%)"),
          y = paste0("PC2 (", round(explained[2] * 100, 1), "%)")
        ) +
        ggplot2::theme_bw(),
      width = 7,
      height = 6
    )
  }
}



## Additional plots to add later:
## h1_distance_from_neutral_amce_by_persona.png
## Bar plot of each persona's AMCE distance from the Neutral baseline

## h2_persona_vs_baseline_human_distance_improvement.png
## Bar plot where positive values mean persona prompting is closer to matched human AMCEs than Neutral

## h2_persona_vs_baseline_human_distance_by_cluster.png
## Bar plot comparing East/West mean persona-human distance with Neutral-human distance

## h3_llm_vs_human_east_west_mdd.png
## bar plot comparing LLM East-West MDD with human East-West MDD



message("Saved hypothesis-aligned LLM-human comparison outputs to ", output_dir)
