#!/usr/bin/env Rscript

library(dplyr)
source("hpa_tau.R")


tnames <- c("adipose tissue","adrenal gland","appendix","bone marrow","cerebral cortex","colon","duodenum","endometrium","esophagus","fallopian tube","gallbladder","heart muscle","kidney","liver","lung","lymph node","ovary","pancreas","placenta","prostate","rectum","salivary gland","skeletal muscle","skin","small intestine","smooth muscle","spleen","stomach","testis","thyroid gland","tonsil","urinary bladder")
data <- read.csv("rna.csv", stringsAsFactors = F)
data <- filter(data, Sample %in% tnames)
data <- rename(data, Tissue = Sample)
data <- rename(data, Level = Abundance)
data.tau <- group_by(data, Gene) %>% do(TAU = tau(.))
data.tau$TAU <- unlist(data.tau$TAU)
data.tau <- filter(data.tau, !is.na(TAU))
write.table(data.tau, paste("HPA.RNA.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
write.table(data, paste("HPA.RNA.expression.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
