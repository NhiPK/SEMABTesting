library(data.table)

ggplot2_available <- requireNamespace("ggplot2", quietly = TRUE)
if (!ggplot2_available) {
  stop("Package 'ggplot2' is required for plotting.")
}
ggrepel_available <- requireNamespace("ggrepel", quietly = TRUE)

args <- commandArgs(trailingOnly = TRUE)
output_dir <- ifelse(length(args) >= 1, args[[1]], "outputs/model_comparison")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

model_files <- list(
  "GPT-4o-mini" = "outputs/analysis_openai4/h1_distance_from_neutral_amce_by_persona.csv",
  "Claude-Sonnet" = "outputs/analysis_sonnet/h1_distance_from_neutral_amce_by_persona.csv",
  "GPT-5.6" = "outputs/analysis_openai5/h1_distance_from_neutral_amce_by_persona.csv"
)

h2_model_files <- list(
  "GPT-4o-mini" = "outputs/analysis_openai4/h2_persona_vs_baseline_human_distance_by_cluster.csv",
  "Claude-Sonnet" = "outputs/analysis_sonnet/h2_persona_vs_baseline_human_distance_by_cluster.csv",
  "GPT-5.6" = "outputs/analysis_openai5/h2_persona_vs_baseline_human_distance_by_cluster.csv"
)

h3_model_files <- list(
  "GPT-4o-mini" = "outputs/analysis_openai4/h3_llm_vs_human_east_west_mdd.csv",
  "Claude-Sonnet" = "outputs/analysis_sonnet/h3_llm_vs_human_east_west_mdd.csv",
  "GPT-5.6" = "outputs/analysis_openai5/h3_llm_vs_human_east_west_mdd.csv"
)

main_effect_files <- list(
  "GPT-4o-mini" = "outputs/analysis_openai4/main_effects_by_persona.csv",
  "Claude-Sonnet" = "outputs/analysis_sonnet/main_effects_by_persona.csv",
  "GPT-5.6" = "outputs/analysis_openai5/main_effects_by_persona.csv"
)

cluster_effect_files <- list(
  "GPT-4o-mini" = "outputs/analysis_openai4/h3_llm_main_effects_by_persona_cluster.csv",
  "Claude-Sonnet" = "outputs/analysis_sonnet/h3_llm_main_effects_by_persona_cluster.csv",
  "GPT-5.6" = "outputs/analysis_openai5/h3_llm_main_effects_by_persona_cluster.csv"
)

pca_matrix_files <- list(
  "GPT-4o-mini" = "outputs/analysis_openai4/h2_llm_amce_matrix_by_country_persona.csv",
  "Claude-Sonnet" = "outputs/analysis_sonnet/h2_llm_amce_matrix_by_country_persona.csv",
  "GPT-5.6" = "outputs/analysis_openai5/h2_llm_amce_matrix_by_country_persona.csv"
)

read_model_h1 <- function(model_name, path) {
  if (!file.exists(path)) {
    stop("Missing H1 file for ", model_name, ": ", path)
  }
  data <- fread(path)
  data[, Model := model_name]
  data
}

read_model_h2 <- function(model_name, path) {
  if (!file.exists(path)) {
    stop("Missing H2 file for ", model_name, ": ", path)
  }
  data <- fread(path)
  data[, Model := model_name]
  data
}

read_model_h3 <- function(model_name, path) {
  if (!file.exists(path)) {
    stop("Missing H3 file for ", model_name, ": ", path)
  }
  data <- fread(path)
  data[, Model := model_name]
  data
}

read_main_effects <- function(model_name, path) {
  if (!file.exists(path)) {
    stop("Missing main effects file for ", model_name, ": ", path)
  }
  data <- fread(path)
  data[, Model := model_name]
  data
}

read_cluster_effects <- function(model_name, path) {
  if (!file.exists(path)) {
    stop("Missing cluster effects file for ", model_name, ": ", path)
  }
  data <- fread(path)
  data[, Model := model_name]
  data
}

read_pca_matrix <- function(model_name, path) {
  if (!file.exists(path)) {
    stop("Missing PCA matrix file for ", model_name, ": ", path)
  }
  data <- fread(path)
  data[, Model := model_name]
  data
}

h1_data <- rbindlist(
  Map(read_model_h1, names(model_files), model_files),
  use.names = TRUE,
  fill = TRUE
)

persona_order <- h1_data[
  , .(
    PersonaCluster = first(PersonaCluster),
    MeanDistance = mean(EuclideanDistanceFromNeutral, na.rm = TRUE)
  ),
  by = PersonaGroup
][order(PersonaCluster, MeanDistance)]$PersonaGroup

h1_data[, PersonaGroup := factor(PersonaGroup, levels = persona_order)]
h1_data[, Model := factor(Model, levels = names(model_files))]

point_plot <- ggplot2::ggplot(
  h1_data,
  ggplot2::aes(
    x = EuclideanDistanceFromNeutral,
    y = PersonaGroup,
    color = Model,
    shape = PersonaCluster
  )
) +
  ggplot2::geom_point(
    position = ggplot2::position_dodge(width = 0.65),
    size = 2.7
  ) +
  ggplot2::labs(
    title = "H1: Persona Distance From Neutral Baseline Across Models",
    subtitle = "Larger values indicate stronger persona-induced AMCE shifts",
    x = "Euclidean distance from Neutral AMCE profile",
    y = NULL,
    color = "Model",
    shape = "Persona cluster"
  ) +
  ggplot2::theme_bw() +
  ggplot2::theme(
    legend.position = "right",
    panel.grid.major.y = ggplot2::element_line(color = "gray90")
  )

bar_plot <- ggplot2::ggplot(
  h1_data,
  ggplot2::aes(
    x = EuclideanDistanceFromNeutral,
    y = PersonaGroup,
    fill = PersonaCluster
  )
) +
  ggplot2::geom_col(width = 0.7, color = "black", linewidth = 0.2) +
  ggplot2::facet_wrap(~ Model, nrow = 1) +
  ggplot2::scale_fill_manual(values = c("East" = "#7fb3d5", "West" = "#f5b041")) +
  ggplot2::labs(
    title = "H1: Persona Distance From Neutral Baseline Across Models",
    subtitle = "Each panel shows persona-induced AMCE shifts within one model",
    x = "Euclidean distance from Neutral AMCE profile",
    y = NULL,
    fill = "Persona cluster"
  ) +
  ggplot2::theme_bw() +
  ggplot2::theme(
    legend.position = "right",
    strip.background = ggplot2::element_rect(fill = "gray90", color = "black"),
    panel.grid.major.y = ggplot2::element_line(color = "gray90")
  )

ggplot2::ggsave(
  file.path(output_dir, "h1_distance_from_neutral_by_model.png"),
  plot = point_plot,
  width = 10,
  height = 7,
  dpi = 300
)

ggplot2::ggsave(
  file.path(output_dir, "h1_distance_from_neutral_by_model_bar.png"),
  plot = bar_plot,
  width = 13,
  height = 7,
  dpi = 300
)

summary_table <- h1_data[
  , .(
    MeanDistanceFromNeutral = mean(EuclideanDistanceFromNeutral, na.rm = TRUE),
    MaxDistanceFromNeutral = max(EuclideanDistanceFromNeutral, na.rm = TRUE),
    PersonaWithMaxDistance = PersonaGroup[which.max(EuclideanDistanceFromNeutral)],
    MinDistanceFromNeutral = min(EuclideanDistanceFromNeutral, na.rm = TRUE),
    PersonaWithMinDistance = PersonaGroup[which.min(EuclideanDistanceFromNeutral)],
    PersonasCompared = .N
  ),
  by = Model
]

fwrite(
  summary_table,
  file.path(output_dir, "h1_distance_from_neutral_by_model_summary.csv")
)

h2_data <- rbindlist(
  Map(read_model_h2, names(h2_model_files), h2_model_files),
  use.names = TRUE,
  fill = TRUE
)
h2_data[, Model := factor(Model, levels = names(h2_model_files))]
h2_data[, PersonaCluster := factor(PersonaCluster, levels = c("East", "West"))]

h2_plot_data <- melt(
  h2_data,
  id.vars = c("Model", "PersonaCluster"),
  measure.vars = c(
    "MeanPersonaEuclideanDistanceToHuman",
    "MeanBaselineEuclideanDistanceToHuman"
  ),
  variable.name = "DistanceType",
  value.name = "Distance"
)
h2_plot_data[, DistanceType := fifelse(
  DistanceType == "MeanPersonaEuclideanDistanceToHuman",
  "Persona LLM vs Human",
  "Neutral LLM vs Human"
)]
h2_plot_data[, DistanceType := factor(
  DistanceType,
  levels = c("Neutral LLM vs Human", "Persona LLM vs Human")
)]

h2_cluster_plot <- ggplot2::ggplot(
  h2_plot_data,
  ggplot2::aes(x = Model, y = Distance, fill = DistanceType)
) +
  ggplot2::geom_col(
    position = ggplot2::position_dodge(width = 0.75),
    color = "black",
    width = 0.65
  ) +
  ggplot2::facet_wrap(~ PersonaCluster, nrow = 1) +
  ggplot2::scale_fill_manual(
    values = c(
      "Neutral LLM vs Human" = "#f8766d",
      "Persona LLM vs Human" = "#00bfc4"
    )
  ) +
  ggplot2::labs(
    title = "H2: Cluster-Level Human Alignment Across Models",
    subtitle = "Lower distance means closer alignment with human AMCEs",
    x = NULL,
    y = "Mean Euclidean distance to human AMCE profile",
    fill = NULL
  ) +
  ggplot2::theme_bw() +
  ggplot2::theme(
    legend.position = "right",
    axis.text.x = ggplot2::element_text(angle = 30, hjust = 1),
    strip.background = ggplot2::element_rect(fill = "gray90", color = "black")
  )

ggplot2::ggsave(
  file.path(output_dir, "h2_cluster_human_alignment_by_model.png"),
  plot = h2_cluster_plot,
  width = 10,
  height = 5.5,
  dpi = 300
)

h3_data <- rbindlist(
  Map(read_model_h3, names(h3_model_files), h3_model_files),
  use.names = TRUE,
  fill = TRUE
)
h3_data[, Model := factor(Model, levels = names(h3_model_files))]

human_mdd <- unique(h3_data$HumanEastWestMDD)
if (length(human_mdd) > 1) {
  warning("Human East-West MDD differs across model analysis folders.")
}

h3_plot_data <- rbindlist(list(
  data.table(Group = "Humans", EastWestMDD = human_mdd[[1]], Type = "Humans"),
  h3_data[
    ,
    .(
      Group = as.character(Model),
      EastWestMDD = LlmEastWestMDD,
      Type = "LLM personas"
    )
  ]
))
h3_plot_data[, Group := factor(
  Group,
  levels = c("Humans", names(h3_model_files))
)]
h3_plot_data[, Type := factor(Type, levels = c("Humans", "LLM personas"))]

h3_mdd_plot <- ggplot2::ggplot(
  h3_plot_data,
  ggplot2::aes(x = Group, y = EastWestMDD, fill = Type)
) +
  ggplot2::geom_col(color = "black", width = 0.65, show.legend = FALSE) +
  ggplot2::scale_fill_manual(
    values = c("Humans" = "#f8766d", "LLM personas" = "#00bfc4")
  ) +
  ggplot2::labs(
    title = "H3: East-West Moral Difference Distance Across Models",
    subtitle = "Lower MDD means weaker East-West differentiation",
    x = NULL,
    y = "East-West MDD"
  ) +
  ggplot2::theme_bw() +
  ggplot2::theme(
    axis.text.x = ggplot2::element_text(angle = 20, hjust = 1)
  )

ggplot2::ggsave(
  file.path(output_dir, "h3_east_west_mdd_by_model.png"),
  plot = h3_mdd_plot,
  width = 8,
  height = 5.5,
  dpi = 300
)

main_effects <- rbindlist(
  Map(read_main_effects, names(main_effect_files), main_effect_files),
  use.names = TRUE,
  fill = TRUE
)

cluster_effects <- rbindlist(
  Map(read_cluster_effects, names(cluster_effect_files), cluster_effect_files),
  use.names = TRUE,
  fill = TRUE
)

neutral_heatmap_data <- main_effects[
  PersonaGroup == "Neutral",
  .(
    Model,
    PromptCondition = "Neutral baseline",
    Effect,
    Estimate
  )
]

cluster_heatmap_data <- cluster_effects[
  PersonaCluster %in% c("East", "West"),
  .(
    Model,
    PromptCondition = paste0(PersonaCluster, " personas"),
    Effect,
    Estimate = ClusterEstimate
  )
]

heatmap_data <- rbindlist(
  list(neutral_heatmap_data, cluster_heatmap_data),
  use.names = TRUE
)

effect_order <- c(
  "Age",
  "Fitness",
  "Gender",
  "Intervention",
  "Law",
  "No. Characters",
  "Relation to AV",
  "Social Status",
  "Species"
)

heatmap_data[, Model := factor(Model, levels = names(main_effect_files))]
heatmap_data[, Effect := factor(Effect, levels = effect_order)]
heatmap_data[, PromptCondition := factor(
  PromptCondition,
  levels = c("Neutral baseline", "East personas", "West personas")
)]

amce_heatmap <- ggplot2::ggplot(
  heatmap_data,
  ggplot2::aes(x = Effect, y = Model, fill = Estimate)
) +
  ggplot2::geom_tile(color = "white", linewidth = 0.5) +
  ggplot2::geom_text(
    ggplot2::aes(label = sprintf("%.2f", Estimate)),
    size = 3
  ) +
  ggplot2::facet_wrap(~ PromptCondition, ncol = 1) +
  ggplot2::scale_fill_gradient2(
    low = "#2166ac",
    mid = "white",
    high = "#b2182b",
    midpoint = 0,
    limits = c(-1, 1),
    name = "AMCE"
  ) +
  ggplot2::labs(
    title = "AMCE Profiles Across Models and Prompting Conditions",
    x = NULL,
    y = NULL
  ) +
  ggplot2::theme_bw() +
  ggplot2::theme(
    axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
    strip.background = ggplot2::element_rect(fill = "gray90", color = "black"),
    panel.grid = ggplot2::element_blank()
  )

ggplot2::ggsave(
  file.path(output_dir, "amce_heatmap_neutral_east_west_by_model.png"),
  plot = amce_heatmap,
  width = 10,
  height = 8,
  dpi = 300
)

fwrite(
  heatmap_data,
  file.path(output_dir, "amce_heatmap_neutral_east_west_by_model.csv")
)