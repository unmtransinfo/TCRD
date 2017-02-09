#!/usr/bin/env Rscript

library(dplyr)
source("hpa_tau.R")

data <- read.csv("normal_tissue.csv", stringsAsFactors = F)
data <- filter(data, Reliability == "Supportive")
data$Tissue[data$Tissue == "endometrium 1"] <- "endometrium"
data$Tissue[data$Tissue == "endometrium 2"] <- "endometrium"
data$Tissue[data$Tissue == "skin 1"] <- "skin"
data$Tissue[data$Tissue == "skin 2"] <- "skin"
data$Tissue[data$Tissue == "stomach 1"] <- "stomach"
data$Tissue[data$Tissue == "stomach 2"] <- "stomach"
data$Tissue[data$Tissue == "soft tissue 1"] <- "soft tissue"
data$Tissue[data$Tissue == "soft tissue 2"] <- "soft tissue"
data <- mutate(data, Tissue = paste(Tissue, Cell.type, sep = " - "))
data$Cell.type <- NULL
data.tau <- group_by(data, Gene) %>% do(TAU = tau(.))
data.tau$TAU <- unlist(data.tau$TAU)
data.tau <- filter(data.tau, !is.na(TAU))
write.table(data.tau, paste("HPA.Protein.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
write.table(data, paste("HPA.Protein.expression.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
