#!/usr/bin/env Rscript

library(data.table)

contrasts <- fread(input = "contrastdetails.tsv", col.names = c("exp_id", "contrast_id", "rt", "rt_type", "rt_val", "label", "url"), colClasses = c("character", "character", "factor", "character","character","character","character"), sep = "\t", header = F)
ct.ref <- contrasts[rt == "reference" & rt_type == "factor" & rt_val == "disease" & label %in% c("normal", "healthy")]
ct.test <- contrasts[rt == "test" & rt_type == "factor" & rt_val == "disease" & !label %in% c("normal", "healthy")]

all <- data.table()

for(i in 1:nrow(ct.test)) {
  test <- ct.test[i]
  ref <- ct.ref[exp_id == test[1, exp_id] & contrast_id == test[1, contrast_id]]
  if(nrow(ref) == 0) {
    next
  }
  file.list <- list.files(test[1, exp_id], pattern = "-analytics.tsv$", full.names=T)
  log2.fold.name <- paste(test[1, contrast_id], "log2foldchange", sep = ".")
  p.val.name <- paste(test[1, contrast_id], "p-value", sep = ".")
  for(fn in file.list) {
    dt <- fread(input = fn, sep = "\t", header = T)
    if(!"Gene ID" %in% names(dt)) {
      next
    }
    if(log2.fold.name %in% names(dt)) {
      dt.sub <- dt[get(p.val.name) <= 0.05 & abs(get(log2.fold.name)) > 1, .(`Gene ID`, `Gene Name`, get(log2.fold.name), get(p.val.name))]
      setnames(dt.sub, "V3", "log2foldchange")
      setnames(dt.sub, "V4", "p-value")
      dt.sub[, disease := test[1, label]]
      dt.sub[, experiment_id := test[1, exp_id]]
      dt.sub[, contrast_id := test[1, contrast_id]]
      all <- rbindlist(list(all, dt.sub))
    }
  }
}

write.table(all, file = "disease_assoc.tsv", sep = "\t", row.names = F, col.names = T)