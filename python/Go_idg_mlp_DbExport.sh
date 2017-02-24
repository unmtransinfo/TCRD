#!/bin/sh
#
DB="mlp_assay"
SCHEMA="public"
#
DATADIR="data"
#
###
#Assay/target export:
ass_csvfile="$DATADIR/mlp_assay_tcrd.csv"
#
(psql -d $DB <<__EOF__
COPY (SELECT
	a.id AS "aid",
	a.assayname,
	a.source,
	a.depositdate,
	a.activesidcount,
	a.totalsidcount,
	at.tgt_gi,
	at.tgt_species,
	at.tgt_name,
	tt.id AS "tcrd_tid",
	tt.tdl AS "tcrd_tdl",
	tt.idgfam AS "tcrd_idgfam",
	tt.uniprot AS "tcrd_uniprot",
	tt.name AS "tcrd_name"
FROM
	assay a
JOIN
	assay_target at ON a.id = at.aid
LEFT OUTER JOIN
	tcrd_tgt tt ON tt.geneid = at.tgt_gi
ORDER BY a.id, at.tgt_gi
) TO STDOUT
WITH (FORMAT CSV, HEADER, DELIMITER ',')
__EOF__
	) \
	>${ass_csvfile}
#
#
