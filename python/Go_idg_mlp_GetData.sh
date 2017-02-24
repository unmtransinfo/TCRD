#!/bin/sh
#############################################################################
### Get assay data from PubChem, via eUtils/eDirect.
### Revised to use eDirect in 2017; change to https problematic for previous
### Perl eUtils.
#############################################################################
# <DocumentSummary>
# <ProteinTargetList>
#   <ProteinTarget>
#     <Name>ERAP1 protein [Homo sapiens]</Name>
#     <GI>21315078</GI>
#     <GeneSymbol>ERAP1</GeneSymbol>
#     <CddId>189008</CddId>
#     <CddName>M1_APN_2</CddName>
#     <CddDescription>Peptidase M1 Aminopeptidase N family incudes tricorn interacting factor F3</CddDescription>
#   </ProteinTarget>
# </ProteinTargetList>
# </DocumentSummary>
#############################################################################
#
DATADIR="data"
#
xmlfile_ass="$DATADIR/assay.xml"
csvfile_ass="$DATADIR/assay.csv"
csvfile_tgt="$DATADIR/assay_target.csv"
#
qry="\"NIH Molecular Libraries Program\"[SourceCategory]"
#
if [ ! -e "${xmlfile_ass}" ]; then
	esearch -db pcassay -query "${qry}" |efetch -format docsum >${xmlfile_ass}
	#Problem: XML errors, manually remove excess <DocumentSummmarySet> tags.
else
	printf "Not overwritten: %s\n" "${xmlfile_ass}"
fi
#
# (Github:xmlutils):
xml2csv --input ${xmlfile_ass} --output ${csvfile_ass} --tag "DocumentSummary"
#
#Problem: This does not extract GI number, due to change in XML schema.
#Need custom program?
#Output: aid,tgt_gi,tgt_species,tgt_name
###
#
python/mlpassay_xml2targets.py --i ${xmlfile_ass} --o ${csvfile_tgt} assaytargets
#
###
#Get TCRD targets for Xref:
tcrd_csvfile="$DATADIR/tcrd_tgt.csv"
tcrd_app.py --list_targets --o $tcrd_csvfile
#
csv_utils.py \
        --i ${tcrd_csvfile} \
        --coltags "id,protein:geneid,tdl,idgfam,protein:sym,protein:uniprot,name" \
        --subsetcols \
        --overwrite_input_file
#
csv_utils.py --i ${tcrd_csvfile} --overwrite_input_file \
	--renamecol --coltag "protein:geneid" --newtag "geneid"
csv_utils.py --i ${tcrd_csvfile} --overwrite_input_file \
	--renamecol --coltag "protein:uniprot" --newtag "uniprot"
csv_utils.py --i ${tcrd_csvfile} --overwrite_input_file \
	--renamecol --coltag "protein:sym" --newtag "sym"
#
