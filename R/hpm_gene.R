#!/usr/bin/env Rscript

library(dplyr)
library(tidyr)
source("hpm_tau.R")
source("hpm_level.R")

gene <- read.csv("HPM_gene_level_epxression_matrix_Kim_et_al_052914.csv.gz", stringsAsFactors = F, sep = ",", quote = "", check.names=F)
gene <- gather(gene, Tissue, Expression, 2:31)
gene.tau <- group_by(gene, Gene) %>% do(Tau = tau(.))
gene.tau$Tau <- unlist(gene.tau$Tau)
gene.tau <- filter(gene.tau, !is.na(Tau))
write.table(gene.tau, paste("HPM.gene.tau", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
gene.level <- group_by(gene, Gene) %>% do(Level = level(.))
gene.level <- filter(gene.level, Gene != "")
data.level <- data.frame()
for(i in 1:nrow(gene.level)) {
	subset <- gene.level$Level[[i]]
	data.level <- bind_rows(data.level, subset)
}
write.table(data.level, paste("HPM.gene.qualitative", Sys.Date(), "tsv", sep = "."), row.names = F, sep = "\t", quote = T)
