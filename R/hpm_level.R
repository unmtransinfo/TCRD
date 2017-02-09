level <- function(gene.sample) {
	require(dplyr)
	gene.sample <- mutate(gene.sample, logExp = ifelse(Expression > 0.0,log10(Expression), NA))
	gene.sample$Level <- "Not detected"
	if(nrow(filter(gene.sample, Expression > 0.0)) == 0) {
		return(gene.sample)
	}
	gene.quant <- quantile(filter(gene.sample, Expression > 0)$logExp)
	if(length(unique(gene.quant)) == 1) {
		gene.quant <- gene.quant-0.0001
	}
	for(i in 1:nrow(gene.sample)) {
		if(is.na(gene.sample$logExp[i])) {
			next
		}
		if(gene.sample$logExp[i] >= gene.quant[1] & gene.sample$logExp[i] < gene.quant[2]) {
			gene.sample$Level[i] <- "Low"
			next
		}
		if(gene.sample$logExp[i] >= gene.quant[2] & gene.sample$logExp[i] <= gene.quant[4]) {
			gene.sample$Level[i] <- "Medium"
			next
		}
		if(gene.sample$logExp[i] > gene.quant[4]) {
			gene.sample$Level[i] <- "High"
		}
	}
	return(gene.sample)
}