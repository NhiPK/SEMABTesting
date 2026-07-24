library(data.table)
library(ggplot2)

PreprocessProfiles <- function(profiles) {
  profiles[, Saved := as.numeric(Saved)]
  profiles[, Intervention := as.numeric(Intervention)]
  profiles[, PedPed := as.numeric(PedPed)]
  profiles[, Barrier := factor(Barrier, levels = c(1, 0))]
  profiles[, CrossingSignal := factor(CrossingSignal, levels = c(0, 2, 1))]
  profiles[, ScenarioType := as.factor(ScenarioType)]
  profiles[, ScenarioTypeStrict := as.factor(ScenarioTypeStrict)]
  profiles[, AttributeLevel := factor(
    AttributeLevel,
    levels = c(
      "Rand", "Male", "Female", "Fat", "Fit", "Low", "High",
      "Old", "Young", "Less", "More", "Pets", "Hoomans"
    )
  )]
  return(profiles)
}

CalcTheoreticalInt <- function(X) {
  intervention <- as.integer(X[["Intervention"]])
  barrier <- as.integer(X[["Barrier"]])
  ped_ped <- as.integer(X[["PedPed"]])
  crossing_signal <- as.integer(X[["CrossingSignal"]])

  if (intervention == 0) {
    if (barrier == 0) {
      if (ped_ped == 1) p <- 0.48 else p <- 0.32

      if (crossing_signal == 0) p <- p * 0.48
      else if (crossing_signal == 1) p <- p * 0.2
      else p <- p * 0.32
    } else {
      p <- 0.2
    }
  } else {
    if (barrier == 0) {
      if (ped_ped == 1) {
        p <- 0.48
        if (crossing_signal == 0) p <- p * 0.48
        else if (crossing_signal == 1) p <- p * 0.32
        else p <- p * 0.2
      } else {
        p <- 0.2
        if (crossing_signal == 0) p <- p * 0.48
        else if (crossing_signal == 1) p <- p * 0.2
        else p <- p * 0.32
      }
    } else {
      p <- 0.32
    }
  }
  return(p)
}

calcWeightsTheoretical <- function(profiles) {
  p <- apply(profiles, 1, CalcTheoreticalInt)
  return(1 / p)
}

fit_effect <- function(data, formula, term_index = 2) {
  if (nrow(data) == 0) return(c(estimate = NA_real_, se = NA_real_, n = 0))

  model <- tryCatch(
    lm(formula, data = data, weights = BC.weights),
    error = function(e) NULL
  )
  if (is.null(model) || length(coef(model)) < term_index) {
    return(c(estimate = NA_real_, se = NA_real_, n = nrow(data)))
  }

  model_summary <- summary(model)
  return(c(
    estimate = unname(coef(model)[[term_index]]),
    se = unname(model_summary$coefficients[term_index, "Std. Error"]),
    n = nrow(data)
  ))
}

effect_row <- function(effect, reference_level, compared_level, estimate) {
  data.table(
    Effect = effect,
    ReferenceLevel = reference_level,
    ComparedLevel = compared_level,
    Contrast = paste(compared_level, "-", reference_level),
    Estimate = estimate[["estimate"]],
    SE = estimate[["se"]],
    N = estimate[["n"]]
  )
}

GetMainEffectSizes <- function(profiles) {
  rows <- list()
  profiles[, BC.weights := calcWeightsTheoretical(.SD)]

  rows[["Intervention"]] <- effect_row(
    "Intervention",
    "Omission",
    "Commission",
    fit_effect(profiles, Saved ~ as.factor(Intervention))
  )

  relation <- profiles[CrossingSignal == 0 & PedPed == 0]
  relation[, BC.weights := calcWeightsTheoretical(.SD)]
  rows[["Relation to AV"]] <- effect_row(
    "Relation to AV",
    "Passengers",
    "Pedestrians",
    fit_effect(relation, Saved ~ as.factor(Barrier))
  )

  legality <- profiles[CrossingSignal != 0 & PedPed == 1]
  legality[, CrossingSignal := factor(CrossingSignal, levels = c(2, 1))]
  legality[, BC.weights := calcWeightsTheoretical(.SD)]
  rows[["Law"]] <- effect_row(
    "Law",
    "Illegal",
    "Legal",
    fit_effect(legality, Saved ~ as.factor(CrossingSignal))
  )

  dimensions <- list(
    "Gender" = list(levels = c("Male", "Female"), labels = c("Male", "Female")),
    "Fitness" = list(levels = c("Fat", "Fit"), labels = c("Large", "Fit")),
    "Social Status" = list(levels = c("Low", "High"), labels = c("Low", "High")),
    "Age" = list(levels = c("Old", "Young"), labels = c("Elderly", "Young")),
    "No. Characters" = list(levels = c("Less", "More"), labels = c("Less", "More")),
    "Species" = list(levels = c("Pets", "Hoomans"), labels = c("Pets", "Humans"))
  )

  for (label in names(dimensions)) {
    scenario_type <- ifelse(label == "No. Characters", "Utilitarian", label)
    attribute_levels <- dimensions[[label]][["levels"]]
    contrast_labels <- dimensions[[label]][["labels"]]
    temp <- profiles[ScenarioType == scenario_type & ScenarioTypeStrict == scenario_type]
    temp[, AttributeLevel := factor(AttributeLevel, levels = attribute_levels)]
    temp[, BC.weights := calcWeightsTheoretical(.SD)]
    rows[[label]] <- effect_row(
      label,
      contrast_labels[1],
      contrast_labels[2],
      fit_effect(temp, Saved ~ as.factor(AttributeLevel))
    )
  }

  return(rbindlist(rows, use.names = TRUE))
}

GetUtilitarianByDifference <- function(profiles) {
  results <- list()
  for (diff in 1:4) {
    temp <- profiles[
      ScenarioType == "Utilitarian" &
        ScenarioTypeStrict == "Utilitarian" &
        DiffNumberOFCharacters == diff
    ]
    temp[, AttributeLevel := factor(AttributeLevel, levels = c("Less", "More"))]
    temp[, BC.weights := calcWeightsTheoretical(.SD)]
    effect <- fit_effect(temp, Saved ~ as.factor(AttributeLevel))
    results[[as.character(diff)]] <- data.table(
      Effect = "No. Characters",
      DiffNumberOFCharacters = diff,
      ReferenceLevel = "Less",
      ComparedLevel = "More",
      Contrast = "More - Less",
      Estimate = effect[["estimate"]],
      SE = effect[["se"]],
      N = effect[["n"]]
    )
  }
  return(rbindlist(results))
}

PlotEffects <- function(effect_data, output_path) {
  plot_data <- copy(effect_data)
  plot_data[, Effect := factor(Effect, levels = rev(unique(Effect)))]

  gg <- ggplot(plot_data, aes(x = Effect, y = Estimate)) +
    geom_col(width = 0.55, fill = "gray75", color = "black", na.rm = TRUE) +
    geom_errorbar(aes(ymin = Estimate - SE, ymax = Estimate + SE), width = 0.2, na.rm = TRUE) +
    geom_hline(yintercept = 0, color = "black") +
    coord_flip() +
    labs(x = NULL, y = "AMCE / change in save probability") +
    theme_bw()

  ggsave(output_path, plot = gg, width = 9, height = 6)
}