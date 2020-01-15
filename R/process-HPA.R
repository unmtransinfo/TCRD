#!/usr/bin/env Rscript
# For demo and explanation of what's going on in here, see ../notebooks/HPA.ipynb

library(data.table)
library(dplyr, quietly = T)
library(RMySQL, quietly = T)

DBHOST <- 'localhost'
DBNAME <- 'tcrd6'
DBUSER <- 'smathias'
OUTPUT_FILE <- '../data/HPA/HPA.tsv'

hpa_tau <- function(exps) {
  exps$Level2 <- numeric(nrow(exps))
  exps$Level2[exps$Level == "Not detected"] <- 0
  exps$Level2[exps$Level == "Low"] <- 1
  exps$Level2[exps$Level == "Medium"] <- 2
  exps$Level2[exps$Level == "High"] <- 3
  #exps$Level2 <- as.numeric(exps$Level2)
  exps <- group_by(exps, Tissue) %>% summarize(Level2 = median(Level2))  
  tau <- sum(1-(exps$Level2/max(exps$Level2)))/(length(unique(exps$Tissue)) - 1)
  return(tau)
}

dbconn <- dbConnect(MySQL(), host=DBHOST, dbname=DBNAME, user=DBUSER)
sql <- "SELECT p.id AS protein_id, x.value AS ensg 
        FROM protein p, xref x 
        WHERE p.id = x.protein_id AND x.xtype = 'ENSG'"
prots <- dbGetQuery(dbconn, sql)
dbDisconnect(dbconn)
rm(dbconn)
setDT(prots)

download.file('http://www.proteinatlas.org/download/normal_tissue.tsv.zip', destfile = '../data/HPA/normal_tissue.tsv.zip')
unzip('../data/HPA/normal_tissue.tsv.zip', exdir = "../data/HPA", overwrite = TRUE)

hpa <- fread("../data/HPA/normal_tissue.tsv", header = T, sep = "\t", quote = "", na.strings = "")
hpa <- merge(hpa, prots, by.x = "Gene", by.y = "ensg")
hpa[, Tissue := sub("\\s\\d+$","", Tissue)]
hpa <- mutate(hpa, Tissue = paste(Tissue, `Cell type`, sep = " - "))
hpa$`Cell type` <- NULL
hpa <- filter(hpa, Reliability != "Uncertain")
setDT(hpa)
hpa[, Level := factor(x = Level, levels = c("Not detected", "Low", "Medium", "High"), ordered = T)]
hpa[, Reliability := factor(x = Reliability, levels = c("Enhanced", "Supported", "Approved"), ordered = T)]
hpa <- hpa[, head(.SD[order(-Reliability, -Level)], 1), by = .(protein_id, Tissue)]
hpa.tau <- group_by(hpa, Gene) %>% do(TAU = hpa_tau(.))
hpa.tau$TAU <- unlist(hpa.tau$TAU)
hpa <- merge(hpa, hpa.tau, by.x = "Gene", by.y = "Gene")

if (file.exists(OUTPUT_FILE)) {
  file.remove(OUTPUT_FILE)
}
fwrite(hpa, file = OUTPUT_FILE, quote = T, sep = "\t", col.names = T, row.names = F, na = "None")

