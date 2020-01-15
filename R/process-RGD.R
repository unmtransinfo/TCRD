#!/usr/bin/env Rscript
# For demo and explanation of what's going on in here, see ../notebooks/RGD.ipynb

library(data.table)
library(tidyr)
library(RMySQL, quietly = T)

DBHOST <- 'localhost'
DBNAME <- 'tcrd6'
DBUSER <- 'smathias'
#RAT_QTLS_FILE <- '/Users/smathias/TCRD/data/RGD/rat_qtls.tsv'
#RAT_TERMS_FILE <- '/Users/smathias/TCRD/data/RGD/rat_terms.tsv'
RAT_QTLS_FILE <- '../data/RGD/rat_qtls.tsv'
RAT_TERMS_FILE <- '../data/RGD/rat_terms.tsv'

rat_genes <- read.delim2("ftp://ftp.rgd.mcw.edu/pub/data_release/GENES_RAT.txt", header = T, comment.char = "#", stringsAsFactors = F, na.strings = "", quote = "\"")
setDT(rat_genes)
rat_genes <- rat_genes[!is.na(UNIPROT_ID)]
rat_genes <- rat_genes[, c("GENE_RGD_ID","UNIPROT_ID"), with=FALSE]
rat_genes <- separate_rows(rat_genes, UNIPROT_ID, sep = ";", convert = T)

qtl <- fread("ftp://ftp.rgd.mcw.edu/pub/data_release/QTLS_RAT.txt", header = T, sep = "\t", na.strings = "", quote = "\"", skip = 70, verbose = T, col.names = c("QTL_RGD_ID","SPECIES","QTL_SYMBOL","QTL_NAME","CHROMOSOME_FROM_REF","LOD","P_VALUE","VARIANCE","FLANK_1_RGD_ID","FLANK_1_SYMBOL","FLANK_2_RGD_ID","FLANK_2_SYMBOL","PEAK_RGD_ID","PEAK_MARKER_SYMBOL","TRAIT_NAME","MEASUREMENT_TYPE","(UNUSED)","PHENOTYPES","ASSOCIATED_DISEASES","CURATED_REF_RGD_ID","CURATED_REF_PUBMED_ID","CANDIDATE_GENE_RGD_IDS","CANDIDATE_GENE_SYMBOLS","INHERITANCE_TYPE","RELATED_QTLS","UNUSED","5.0_MAP_POS_CHR","5.0_MAP_POS_START","5.0_MAP_POS_STOP","5.0_MAP_POS_METHOD","3.4_MAP_POS_CHR","3.4_MAP_POS_START","3.4_MAP_POS_STOP","3.4_MAP_POS_METHOD","CROSS_TYPE","CROSS_PAIR","STRAIN_RGD_ID1","STRAIN_RGD_ID2","STRAIN_RGD_SYMBOL1","STRAIN_RGD_SYMBOL2","6.0_MAP_POS_CHR","6.0_MAP_POS_START","6.0_MAP_POS_STOP","6.0_MAP_POS_METHOD","STRAIN_RGD_ID3","STRAIN_RGD_SYMBOL3","SSTRAIN"))
qtl <- qtl[!is.na(CANDIDATE_GENE_RGD_IDS)]
qtl <- separate_rows(qtl, CANDIDATE_GENE_RGD_IDS, CANDIDATE_GENE_SYMBOLS, sep = ";", convert = T)
qtl <- separate_rows(qtl, PHENOTYPES, sep = ";")
qtl <- qtl[, .(QTL_RGD_ID, QTL_SYMBOL, QTL_NAME, LOD, P_VALUE, TRAIT_NAME, MEASUREMENT_TYPE, ASSOCIATED_DISEASES, CANDIDATE_GENE_RGD_IDS, PHENOTYPES)]
qtl <- qtl[CANDIDATE_GENE_RGD_IDS %in% rat_genes$GENE_RGD_ID]

dbconn <- dbConnect(MySQL(), host=DBHOST, dbname=DBNAME, user=DBUSER)
sql <- "SELECT id AS nhprotein_id, uniprot FROM nhprotein WHERE taxid = 10116"
prots <- dbGetQuery(dbconn, sql)
dbDisconnect(dbconn)
rm(dbconn)
setDT(prots)
nhprot2rgd <- merge(rat_genes, prots, by.x = "UNIPROT_ID", by.y = "uniprot")
nhprot2rgd[, UNIPROT_ID := NULL]

rat_qtls <- merge(nhprot2rgd, qtl, by.x = "GENE_RGD_ID", by.y = "CANDIDATE_GENE_RGD_IDS")
if(file.exists(RAT_QTLS_FILE)) {
  file.remove(RAT_QTLS_FILE)
}
fwrite(rat_qtls, file = RAT_QTLS_FILE, sep = "\t", col.names = T, row.names = F, quote = T, na = "None")

rat.do <- fread("ftp://ftp.rgd.mcw.edu/pub/data_release/with_terms/rattus_terms_do", sep = "\t", na.strings = "", skip = 27, verbose = T, quote = "")
rat.do <- rat.do[OBJECT_TYPE == "gene"]
rat.do <- rat.do[, .(RGD_ID, OBJECT_SYMBOL, TERM_ACC_ID, TERM_NAME, QUALIFIER, EVIDENCE)]
rat.do[, ONTOLOGY := "Disease Ontology"]
rat.do <- rat.do[RGD_ID %in% rat_genes$GENE_RGD_ID]
rat.do <- unique(rat.do, by = c("RGD_ID", "TERM_ACC_ID"))

rat.mp <- fread("ftp://ftp.rgd.mcw.edu/pub/data_release/with_terms/rattus_terms_mp", sep = "\t", na.strings = "", skip = 27, verbose = T, quote = "")
rat.mp <- rat.mp[OBJECT_TYPE == "gene"]
rat.mp <- rat.mp[, .(RGD_ID, OBJECT_SYMBOL, TERM_ACC_ID, TERM_NAME, QUALIFIER, EVIDENCE)]
rat.mp[, ONTOLOGY := "Mammalian Phenotype"]
rat.mp <- rat.mp[RGD_ID %in% rat_genes$GENE_RGD_ID]
rat.mp <- unique(rat.mp, by = c("RGD_ID", "TERM_ACC_ID"))

rat.rdo <- fread("ftp://ftp.rgd.mcw.edu/pub/data_release/with_terms/rattus_terms_rdo", sep = "\t", na.strings = "", skip = 27, verbose = T, quote = "")
rat.rdo <- rat.rdo[OBJECT_TYPE == "gene"]
rat.rdo <- rat.rdo[, .(RGD_ID, OBJECT_SYMBOL, TERM_ACC_ID, TERM_NAME, QUALIFIER, EVIDENCE)]
rat.rdo[, ONTOLOGY := "RGD Disease Ontology"]
rat.rdo <- rat.rdo[RGD_ID %in% rat_genes$GENE_RGD_ID]
rat.rdo <- unique(rat.rdo, by = c("RGD_ID", "TERM_ACC_ID"))

if (file.exists(RAT_TERMS_FILE)) {
  file.remove(RAT_TERMS_FILE)
}
fwrite(rat.do, file = RAT_TERMS_FILE, append = file.exists(RAT_TERMS_FILE), col.names = !file.exists(RAT_TERMS_FILE), sep = "\t", row.names = F, quote = T, na = "None")
fwrite(rat.mp, file = RAT_TERMS_FILE, append = file.exists(RAT_TERMS_FILE), col.names = !file.exists(RAT_TERMS_FILE), sep = "\t", row.names = F, quote = T, na = "None")
fwrite(rat.rdo, file = RAT_TERMS_FILE, append = file.exists(RAT_TERMS_FILE), col.names = !file.exists(RAT_TERMS_FILE), sep = "\t", row.names = F, quote = T, na = "None")
