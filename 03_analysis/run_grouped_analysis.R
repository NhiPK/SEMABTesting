library(data.table)

source("03_analysis/moral_machine_functions.R")

args <- commandArgs(trailingOnly = TRUE)
input_path <- ifelse(length(args) >= 1, args[[1]], "outputs/shared_responses_llm.csv")
output_dir <- ifelse(length(args) >= 2, args[[2]], "outputs/analysis")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

profiles <- fread(input_path, na.strings = c(""))
profiles <- PreprocessProfiles(profiles)

overall_effects <- GetMainEffectSizes(copy(profiles))
overall_effects[, AnalysisGroup := "Overall"]
fwrite(overall_effects, file.path(output_dir, "main_effects_overall.csv"))
PlotEffects(overall_effects, file.path(output_dir, "main_effects_overall.png"))

overall_util <- GetUtilitarianByDifference(copy(profiles))
overall_util[, AnalysisGroup := "Overall"]
fwrite(overall_util, file.path(output_dir, "utilitarian_by_difference_overall.csv"))

persona_effects <- rbindlist(lapply(sort(unique(profiles$PersonaGroup)), function(persona) {
  subset <- profiles[PersonaGroup == persona]
  result <- GetMainEffectSizes(copy(subset))
  result[, PersonaGroup := persona]
  result[, UserCountry3 := unique(subset$UserCountry3)[1]]
  result[, PersonaCluster := unique(subset$PersonaCluster)[1]]
  result[, PersonaNationality := unique(subset$PersonaNationality)[1]]
  return(result)
}), fill = TRUE)
fwrite(persona_effects, file.path(output_dir, "main_effects_by_persona.csv"))

persona_util <- rbindlist(lapply(sort(unique(profiles$PersonaGroup)), function(persona) {
  subset <- profiles[PersonaGroup == persona]
  result <- GetUtilitarianByDifference(copy(subset))
  result[, PersonaGroup := persona]
  result[, UserCountry3 := unique(subset$UserCountry3)[1]]
  result[, PersonaCluster := unique(subset$PersonaCluster)[1]]
  result[, PersonaNationality := unique(subset$PersonaNationality)[1]]
  return(result)
}), fill = TRUE)
fwrite(persona_util, file.path(output_dir, "utilitarian_by_difference_by_persona.csv"))


persona_country_map <- unique(profiles[, .(
  PersonaGroup,
  UserCountry3,
  PersonaCluster,
  PersonaNationality
)])
setorder(persona_country_map, PersonaCluster, PersonaNationality)
fwrite(persona_country_map, file.path(output_dir, "persona_country_map.csv"))

message("Saved analysis outputs to ", output_dir)
