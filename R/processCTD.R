#!/usr/bin/env Rscript

library(data.table)

dt <- read.table("CTD_genes_diseases.tsv.gz", header = F, sep = "\t", stringsAsFactors = F, col.names = c("GeneSymbol","GeneID","DiseaseName","DiseaseID","DirectEvidence","InferenceChemicalName","InferenceScore","OmimIDs","PubMedIDs"), quote = NULL)
setDT(dt)
dt <- dt[!is.na(DirectEvidence) & nchar(DirectEvidence) > 0]
mesh.doid <- fread("doid_mesh_map.tsv", sep = "\t", header = T, key = "XREF")
mesh.doid <- unique(mesh.doid, by = "XREF")
omim.doid <- fread("doid_omim_map.tsv", sep = "\t", header = T, key = "XREF")
omim.doid <- unique(omim.doid, by = "XREF")

dt[, c("DiseaseID_Source", "DiseaseID") := tstrsplit(DiseaseID, ":", fixed = T)]
dt[, `:=`(OmimIDs = NULL, InferenceScore = NULL, InferenceChemicalName = NULL)]
setkey(dt, "DiseaseID")
dt.omim <- dt[DiseaseID_Source == "OMIM"]
dt.mesh <- dt[DiseaseID_Source == "MESH"]

dt.omim <- merge(dt.omim, omim.doid, by.x = "DiseaseID", by.y = "XREF", all.x = T)
dt.mesh <- merge(dt.mesh, mesh.doid, by.x = "DiseaseID", by.y = "XREF", all.x = T)

dt <- rbindlist(list(dt.mesh, dt.omim))
dt[nchar(PubMedIDs) == 0, PubMedIDs := NA]
write.table(dt, file = "CTD_genes_diseases_directonly.tsv", sep = "\t", quote = T, row.names = F, col.names = T)