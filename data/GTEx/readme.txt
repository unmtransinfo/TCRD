GTEx tissue expression data downloaded from http://www.gtexportal.org/home/

Processing steps:
1. Compute "tau" tissue specificity using the definition from http://dx.doi.org/10.1093/bioinformatics/bti042 results in file gtex.tau.${system.date}.tsv
   results file data columns:
   ENSG - Ensembl gene id
   TAU - tissue specificity index
   AGE - tissue donor age group
   GENDER - tissue donor gender
2. Compute median RPKM and qualitative ("Not detected", "Low", "Medium", "High") expression levels for: all samples, samples grouped by gender, and samples grouped by gender and age groups. Results in file gtex.rpkm.qualitative.${system.date}.tsv
   results file data columns:
   ENSG - Ensembl gene id
   SMTSD - GTEx tissue name
   MEDIAN_RPKM - median RPKM value for group defined by values in columns GENDER and AGE
   LEVEL - qualitative expression levels based on quartile values:
   	"Low" - 1st quartile
	"Medium" - 2nd and 3rd quartile
	"High" - 4th quartile
	"Not detected" - median RPKM = 0
   LOG_MEDIAN_RPKM - log2 of median RPKM
   AGE - tissue donor age group
   GENDER - tissue donor gender
   
   
   
   
File ../../R/exp-atlas_process.R contains R script used to run processing steps above using as input GTEx downloaded files
