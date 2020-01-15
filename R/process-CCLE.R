#!/usr/bin/env Rscript
# For demo and explanation of what's going on in here, see ../notebooks/CCLE.ipynb

library(data.table)
library(RMySQL, quietly = T)

# Register to download CCLE at https://portals.broadinstitute.org/ccle
# Download the latest *RNASeq_RPKM* file and save in CCLE_DIR
#CCLE_DIR <- '/Users/smathias/TCRD/data/CCLE'
CCLE_DIR <- '/home/smathias/TCRD/data/CCLE'
INPUT_FILE <- paste(CCLE_DIR, 'CCLE_DepMap_18q3_RNAseq_RPKM_20180718.gct', sep="/")
OUTPUT_FILE <- paste(CCLE_DIR, 'CCLE.tsv', sep="/")
GZIP_FILE <- paste(OUTPUT_FILE, 'gz', sep=".")
# TCRD connection parameters
DBHOST <- 'localhost'
DBNAME <- 'tcrd6'
DBUSER <- 'smathias'

ccle <- fread(INPUT_FILE, header = T, skip = 2, sep = "\t", quote = "")
ccle[, Description := NULL]

ccle <- melt(ccle, id.vars = "Name", variable.name = "cell_id", value.name = "expression", variable.factor = F, value.factor = F)
ccle[, cell_id2 := tstrsplit(cell_id, "_", fixed = T, keep = 1)]
ccle[cell_id2 != cell_id, tissue := substr(cell_id, nchar(cell_id2) + 2, nchar(cell_id))]
ccle[, cell_id := NULL]
setnames(ccle, c("cell_id2"), c("cell_id"))
ccle[, ENSG := tstrsplit(Name, ".", fixed = T, keep = 1)]
ccle[, Name := NULL]

dbconn <- dbConnect(MySQL(), host=DBHOST, dbname=DBNAME, user=DBUSER)
sql <- "SELECT p.id AS protein_id, x.value AS ensg 
        FROM protein p, xref x 
        WHERE p.id = x.protein_id AND x.xtype = 'ENSG'"
prots <- dbGetQuery(dbconn, sql)
dbDisconnect(dbconn)
rm(dbconn)
setDT(prots)

dt <- merge(ccle, prots, by.x = "ENSG", by.y = "ensg", all.x = T, allow.cartesian = T)
dt <- dt[!is.na(protein_id)]
dt[, ENSG := NULL]

setcolorder(dt, c("protein_id", "cell_id", "tissue", "expression"))
dt <- unique(dt)

fwrite(dt, file = OUTPUT_FILE, quote = T, sep = "\t", col.names = T, row.names = F, na = "None")
if(file.exists(GZIP_FILE)) {
  file.remove(GZIP_FILE)
}
system(sprintf("gzip -9v %s", OUTPUT_FILE))
