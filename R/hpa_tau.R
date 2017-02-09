tau <- function(gene.sample) {
  require(dplyr)
  gene.sample$Level[gene.sample$Level == "Not detected"] <- 0
  gene.sample$Level[gene.sample$Level == "Low"] <- 1
  gene.sample$Level[gene.sample$Level == "Medium"] <- 2
  gene.sample$Level[gene.sample$Level == "High"] <- 3
  gene.sample$Level <- as.numeric(gene.sample$Level)
  gene.sample <- group_by(gene.sample, Tissue) %>% summarize(Level = median(Level))  
  tau <- sum(1-(gene.sample$Level/max(gene.sample$Level)))/(length(unique(gene.sample$Tissue)) - 1)
  return(tau)
}