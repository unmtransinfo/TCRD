SELECT
	target.id AS "tcrdTargetId",
	target.name AS "tcrdTargetName",
	target.fam AS "tcrdTargetFamily",
	target.tdl AS "TDL",
	target.idg AS "idgList",
	protein.id AS "tcrdProteinId",
	protein.sym AS "tcrdGeneSymbol",
	protein.family AS "tcrdProteinFamily",
	protein.geneid AS "ncbiGeneId",
	protein.uniprot AS "uniprotId",
	protein.up_version AS "uniprotVersion",
	protein.name AS "proteinName",
	protein.stringid AS "ensemblProteinId",
	protein.chr,
	protein.description AS "proteinDesc",
	protein.dtoid AS "dtoId",
	xref.value AS "ensemblGeneId"
FROM
	target
JOIN
	t2tc ON t2tc.target_id = target.id
JOIN
	protein ON protein.id = t2tc.protein_id
JOIN
	xref ON xref.protein_id = protein.id
WHERE
	xref.xtype = 'Ensembl' AND xref.value REGEXP '^ENSG'
        ;
