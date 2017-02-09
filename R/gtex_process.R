#!/usr/bin/env Rscript

library(dplyr)
library(stringr)
library(tidyr)
library(data.table)
library(Hmisc)

tau <- function(x) {
  if(sum(is.na(x)) == length(x)) {
    return(0.0)
  }
  deciles <- cut2(x, g = 10)
  t <- as.data.frame(table(deciles, useNA = "ifany")) %>% mutate(deciles = ifelse(is.na(deciles), 0, deciles)) %>% mutate(x = (1 - deciles/max(deciles)))
  return(sum(t$Freq*t$x)/(sum(t$Freq) - 1))
}


sample.label <- read.csv("GTEx_Data_V6_Annotations_SampleAttributesDS.txt", header = T, sep = "\t", stringsAsFactors = F, quote = "")
subject.label <- read.csv("GTEx_Data_V6_Annotations_SubjectPhenotypesDS.txt", header = T, sep = "\t", stringsAsFactors = F, quote = "")
subject.label <- mutate(subject.label, GENDER = ifelse(GENDER == 1, "M", "F"))
subject.label <- mutate(subject.label, GENDER = factor(GENDER, levels = c("M","F")))
sample.subj <- select(sample.label, SAMPID) %>% mutate(SAMPID.D = SAMPID) %>% separate(SAMPID.D, c("C1","C2"), sep = "-", extra = "drop") %>% unite(SUBJID, C1, C2, sep = "-")
subject.label <- inner_join(subject.label, sample.subj, by = "SUBJID")
sample.label <- inner_join(sample.label, select(subject.label, SUBJID, GENDER, AGE, SAMPID), by = "SAMPID")
sample.label <- select(sample.label, SAMPID,SMTS,SMTSD, GENDER, AGE)
setDT(sample.label)
setkey(sample.label, SAMPID)
data <- fread(input = "GTEx_Analysis_v6_RNA-seq_RNA-SeQCv1.1.8_gene_rpkm.gct", sep = "\t", header = T, skip = 2)
data[, Description := NULL]
setnames(data, old = c("Name"), new = c("ENSG"))
data <- melt(data, value.name = "RPKM", na.rm = T, variable.name = "SAMPID", id.vars = c("ENSG"))
setkey(data, SAMPID)
data <- data[!ENSG %like% "ENSGR"]
data <- merge(data, sample.label, by = "SAMPID")
data.tau <- data[, .(MEDIAN = median(RPKM, na.rm = T)), by = .(ENSG, SMTSD)][, LOG_MEDIAN := ifelse(MEDIAN > 0.0, log10(MEDIAN), NA)][, .(TAU = tau(LOG_MEDIAN)), by = ENSG][, AGE := "ALL"][, GENDER := "ALL"]
write.table(data.tau, paste("gtex.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T, col.names = T)
rm(data.tau)
data.tau.gender <- data[, .(MEDIAN = median(RPKM, na.rm = T)), by = .(ENSG, SMTSD, GENDER)][, LOG_MEDIAN := ifelse(MEDIAN > 0.0, log10(MEDIAN), NA)][, .(TAU = tau(LOG_MEDIAN)), by = .(ENSG, GENDER)][, AGE := "ALL"]
setcolorder(data.tau.gender, c("ENSG", "TAU", "AGE", "GENDER"))
write.table(data.tau.gender, paste("gtex.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T, col.names = F, append = T)
rm(data.tau.gender)
data.tau.gender.age <- data[, .(MEDIAN = median(RPKM, na.rm = T)), by = .(ENSG, SMTSD, GENDER, AGE)][, LOG_MEDIAN := ifelse(MEDIAN > 0.0, log10(MEDIAN), NA)][, .(TAU = tau(LOG_MEDIAN)), by = .(ENSG, GENDER, AGE)]
setcolorder(data.tau.gender.age, c("ENSG", "TAU", "AGE", "GENDER"))
write.table(data.tau.gender.age, paste("gtex.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T, col.names = F, append = T)
rm(data.tau.gender.age)

setkey(data, ENSG)
#d2 <- data[ENSG %in% c("ENSG00000043591.4","ENSG00000169252.4")]
data.level <- data[, .(MEDIAN_RPKM = median(RPKM, na.rm = T)), by = .(ENSG, SMTSD)][, RANK := frank(MEDIAN_RPKM)/.N, by = ENSG][MEDIAN_RPKM == 0.0, RANK := 0.0][RANK == 0.0, LEVEL := "Not detected"][RANK > 0.0 & RANK < 0.25, LEVEL := "Low"][RANK >= 0.25 & RANK < 0.75, LEVEL := "Medium"][RANK >= 0.75, LEVEL := "High"][, RANK := NULL][, LOG_MEDIAN_RPKM := ifelse(MEDIAN_RPKM > 0.0, log10(MEDIAN_RPKM), NA)][, AGE := "ALL"][, GENDER := "ALL"]
write.table(data.level, paste("gtex.rpkm.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T, col.names = T)
rm(data.level)
data.level.gender <- data[, .(MEDIAN_RPKM = median(RPKM, na.rm = T)), by = .(ENSG, SMTSD, GENDER)][, RANK := frank(MEDIAN_RPKM)/.N, by = ENSG][MEDIAN_RPKM == 0.0, RANK := 0.0][RANK == 0.0, LEVEL := "Not detected"][RANK > 0.0 & RANK < 0.25, LEVEL := "Low"][RANK >= 0.25 & RANK < 0.75, LEVEL := "Medium"][RANK >= 0.75, LEVEL := "High"][, RANK := NULL][, LOG_MEDIAN_RPKM := ifelse(MEDIAN_RPKM > 0.0, log10(MEDIAN_RPKM), NA)][, AGE := "ALL"]
setcolorder(data.level.gender, c("ENSG","SMTSD","MEDIAN_RPKM","LEVEL","LOG_MEDIAN_RPKM","AGE","GENDER"))
write.table(data.level.gender, paste("gtex.rpkm.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T, col.names = F, append = T)
rm(data.level.gender)
data.level.gender.age <- data[, .(MEDIAN_RPKM = median(RPKM, na.rm = T)), by = .(ENSG, SMTSD, GENDER, AGE)][, RANK := frank(MEDIAN_RPKM)/.N, by = ENSG][MEDIAN_RPKM == 0.0, RANK := 0.0][RANK == 0.0, LEVEL := "Not detected"][RANK > 0.0 & RANK < 0.25, LEVEL := "Low"][RANK >= 0.25 & RANK < 0.75, LEVEL := "Medium"][RANK >= 0.75, LEVEL := "High"][, RANK := NULL][, LOG_MEDIAN_RPKM := ifelse(MEDIAN_RPKM > 0.0, log10(MEDIAN_RPKM), NA)]
setcolorder(data.level.gender.age, c("ENSG","SMTSD","MEDIAN_RPKM","LEVEL","LOG_MEDIAN_RPKM","AGE","GENDER"))
write.table(data.level.gender.age, paste("gtex.rpkm.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T, col.names = F, append = T)
rm(data.level.gender.age)
