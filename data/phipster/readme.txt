09/26/2019
Description of P-hipster predictions (viral-human protein protein interactions -PPIs-)
For technical questions please email gorka.lasso@gmail.com

This directory describes the viral-human PPIs predicted with high-confidence (final likelihood ratio >= 100).


phipster_predictions_finalLR100.txt
########################################################
Tab delimited file describing the predicted PPIs.
	term1: Viral protein | human protein
		Viral protein is described by the virus taxonomic id and a phipster identifier.
		e.g. tx1006008_id15
		virus taxonomic id: 1006008
		viral protein phipster id: 15
		
		human protein is described the the uniprot AC and its corresponding Gene name
	term 2: Likelihood ratio of the interaction

virus_taxonomy.txt
########################################################
Tab delimited file describing the taxonomy of human viruses. You can use this file to extract information on each virus based on the corresponding taxonomy identifier.
	term 1: Taxonomy id for virus
	term 2: Broad virus classification (DNA virus, RNA virus, retrovirus)
	term 3: Baltimore classification
	term 4: Viral order
	term 5: Viral family
	term 6: Viral subfamily
	term 7: Viral genus
	term 8: Viral specie
	term 9: Virus name

virProtein_name.txt
########################################################
Tab delimited file describing the name of viral protein.
	term 1: phipster identifier for viral protein
	term 2: protein name

virProtein_ncbi.txt
########################################################
Tab delimited file mapping each viral protein to an NCBI identifier. If interested to link the viral protein to the NCBI database you can use the following link ncbi.nlm.nih.gov/protein/ + protein identifier
	term 1: phipster identifier for viral protein
	term 2: NCBI protein identifier (genebank, refseq)

