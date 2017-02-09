tau <- function(gene.sample) {
  require(dplyr)
  gene.sample <- mutate(gene.sample, logExp = ifelse(Expression > 0, log10(Expression), NA))
  exp.quant <- quantile(gene.sample$logExp, probs = seq(0,1,0.1), na.rm = T)
  gene.sample$level <- 0
  if(length(unique(exp.quant)) == 1) {
	  exp.quant <- c(exp.quant[1], exp.quant[1] + 0.1)
  }
  for(i in 2:length(exp.quant)) {
	  for(j in 1:nrow(gene.sample)) {
		  if(is.na(gene.sample$logExp[j])) {
			  next
		  }
		  if(gene.sample$logExp[j] >= exp.quant[length(exp.quant)]) {
			  gene.sample$level[j] <- length(exp.quant) - 1
			  next
		  }
		  if((gene.sample$logExp[j] >= exp.quant[i-1]) & (gene.sample$logExp[j] < exp.quant[i])) {
			  gene.sample$level[j] <- (i - 1)
		  }
	  }
  }
  t <- sum(1-(gene.sample$level/max(gene.sample$level)))/(nrow(gene.sample) - 1)
  return(t)
}
