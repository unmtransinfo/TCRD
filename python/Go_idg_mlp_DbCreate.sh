#!/bin/sh
#############################################################################
### Go_kmc_mlp_DbCreate.sh
### 
### Also see Go_kmc_mlp_DbBadappleT.sh
### 
### Jeremy Yang
###   9 Feb 2017
#############################################################################
#
#
DB="mlp_assay"
SCHEMA="public"
#
createdb "$DB"
#
psql -d $DB -c "COMMENT ON DATABASE $DB IS 'MLP Assays and associated protein targets'";
#
DATADIR="data"
#
CSVFILES="\
${DATADIR}/assay.csv \
${DATADIR}/assay_target.csv \
${DATADIR}/tcrd_tgt.csv \
"
#
for csvfile in $CSVFILES ; do
	#
	csv2sql.py \
		--i $csvfile \
		--create \
		--schema "$SCHEMA" \
		--fixtags \
		--maxchar 4096 \
		|psql -d $DB
	#
	csv2sql.py \
		--i $csvfile \
		--insert \
		--schema "$SCHEMA" \
		--fixtags \
		--maxchar 4096 \
		|psql -q -d $DB
	#
done
###
psql -d $DB -c "COMMENT ON TABLE assay IS 'MLP Assays'"
psql -d $DB -c "COMMENT ON TABLE assay_target IS 'MLP Assay Targets (AID to NCBI GI links)'"
###
psql -d $DB -c "ALTER TABLE assay DROP COLUMN proteintargetlist"
psql -d $DB -c "ALTER TABLE assay DROP COLUMN sourcenamelist"
psql -d $DB -c "ALTER TABLE assay RENAME COLUMN sourcenamelist_string TO source"
psql -d $DB -c "UPDATE assay SET activesidcount = '0' WHERE activesidcount = ''"
psql -d $DB -c "UPDATE assay SET totalsidcount = '0' WHERE totalsidcount = ''"
###
#############################################################################
###
#./Go_kmc_mlp_DbBadappleT.sh
