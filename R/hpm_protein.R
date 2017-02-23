#!/usr/bin/env Rscript

library(dplyr)
library(tidyr)
source("hpm_tau.R")
source("hpm_level.R")

prot <- read.csv("HPM_protein_level_expression_matrix_Kim_et_al_052914.csv.gz", stringsAsFactors = F, sep = ",", quote = "", check.names=F)
names(prot)[2] <- "RefSeq"
prot$Accession <- NULL
prot <- gather(prot, Tissue, Expression, 2:31)
prot.tau <- group_by(prot, RefSeq) %>% do(Tau = tau(.))
prot.tau$Tau <- unlist(prot.tau$Tau)
prot.tau <- filter(prot.tau, !is.na(Tau))
write.table(prot.tau, paste("HPM.protein.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
prot.level <- group_by(prot, RefSeq) %>% do(Level = level(.))
prot.level <- filter(prot.level, RefSeq != "")
data.level <- data.frame()
for(i in 1:nrow(prot.level)) {
	subset <- prot.level$Level[[i]]
	data.level <- bind_rows(data.level, subset)
}
write.table(data.level, paste("HPM.protein.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
