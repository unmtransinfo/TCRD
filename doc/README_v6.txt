Create empty schema with types
------------------------------
[smathias@juniper SQL]$ mysqldump --no-data tcrd5 | sed 's/ AUTO_INCREMENT=[0-9]*\b//g' > create-TCRD.sql
[smathias@juniper SQL]$ mysqldump --no-create-db --no-create-info tcrd5 cmpd_activity_type compartment_type data_type disease_type expression_type info_type pathway_type phenotype_type ppi_type xref_type > types_v6.sql
mysql> create database tcrd6;
mysql> use tcrd6
mysql> \. create-TCRD.sql
mysql> \. types_v6.sql
Check that everything is good:
mysql> SHOW TABLE STATUS FROM `tcrd6`;
[smathias@juniper SQL]$ mysqldump tcrd6 > create-TCRDv6.sql
[smathias@juniper SQL]$ rm create-TCRD.sql types_v6.sql
There are too many xref types (from UniProt) that are not used, so fix this:
DELETE FROM xref_type where name NOT IN ('UniProt Keyword', 'NCBI GI', 'HGNC', 'MGI ID', 'Ensembl', 'STRING', 'DrugBank', 'BRENDA', 'ChEMBL', 'MIM', 'PANTHER', 'PDB', 'UniGene', 'InterPro', 'Pfam', 'PROSITE', 'SMART'); -- NB 'RefSeq' (for HPM Protein) and 'L1000 ID' are needed here.
[smathias@juniper SQL]$ mysqldump tcrd6 > create-TCRDv6.sql

mysql> drop database tcrd6;
mysql> create database tcrd6;
mysql> use trrd6
mysql> \. create-TCRDv6.sql
New tables and changes to support metapath are in SQL/tcrdmp.sql
mysql> \. tcrdmp.sql


[smathias@juniper loaders]$ ./load-UniProt.py --dbname tcrd6 --loglevel 20

load-UniProt.py (v3.1.0) [Fri Apr  5 11:20:36 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing Evidence Ontology file ../data/eco.obo

Parsing file ../data/UniProt/uniprot-reviewed-human_20190103.xml
Loading data for 20412 UniProt records
Progress: 100% [######################################################################] Time: 0:10:47
Processed 20412 UniProt records. Elapsed time: 0:11:00.536
  Loaded 20412 targets/proteins

Parsing file ../data/UniProt/uniprot-mouse_20190103.xml
Loading data for 85187 UniProt records
Progress: 100% [######################################################################] Time: 0:06:55
Processed 85187 UniProt records. Elapsed time: 0:07:15.195
  Loaded 85187 nhproteins

Parsing file ../data/UniProt/uniprot-rat_20190103.xml
Loading data for 36090 UniProt records
Progress: 100% [######################################################################] Time: 0:02:44
Processed 36090 UniProt records. Elapsed time: 0:02:54.415
  Loaded 36090 nhproteins

load-UniProt.py: Done. Total elapsed time: 0:21:19.482

Some UniProt records have multiple Gene IDs. The loader takes the first
one, but this is not always the right one. So manual fixes to Gene IDs:
mysql> \. update_geneids.sql

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-1.sql


# HGNC
[smathias@juniper loaders]$ ./load-HGNC.py --dbname tcrd6 --loglevel 20

load-HGNC.py (v3.0.0) [Fri Apr  5 11:50:20 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 41618 lines in file ../data/HGNC/HGNC_20190104.tsv
Progress: 100% [######################################################################] Time: 0:22:12
Processed 41618 lines - 20205 targets annotated.
No target found for 21397 lines.
  Inserted 20373 HGNC ID xrefs
  Inserted 20373 MGI ID xrefs
WARNING: 244 discrepant HGNC symbols. See logfile ./tcrd6logs/load-HGNC.py.log for details
  Added 1196 new NCBI Gene IDs
WARNING: 200 discrepant NCBI Gene IDs. See logfile ./tcrd6logs/load-HGNC.py.log for details

load-HGNC.py: Done. Elapsed time: 0:22:12.969

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-2.sql


# GIs
[smathias@juniper loaders]$ ./load-GIs.py --dbname tcrd6

load-GIs.py (v2.2.0) [Fri Apr  5 12:15:08 2019]:

Downloading  ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping_selected.tab.gz
         to  ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Uncompressing ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Done. Elapsed time: 0:00:10.177

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 169671 rows in file ../data/UniProt/HUMAN_9606_idmapping_selected.tab
Progress: 100% [######################################################################] Time: 0:03:26

169671 rows processed
  Inserted 257171 new GI xref rows for 20402 targets
  Skipped 149269 rows with no GI

load-GIs.py: Done. Elapsed time: 0:03:26.453

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-3.sql


# ENSGs
[smathias@juniper loaders]$ ./load-ENSGs.py --dbname tcrd6

load-ENSGs.py (v1.0.0) [Fri Apr  5 12:27:39 2019]:

Parsing file ../data/UniProt/uniprot-rat_20190103.xml
Processing 36090 UniProt records
Progress: 100% [######################################################################] Time: 0:00:27
Parsing file ../data/UniProt/uniprot-mouse_20190103.xml
Processing 85187 UniProt records
Progress: 100% [######################################################################] Time: 0:02:20
Parsing file ../data/UniProt/uniprot-reviewed-human_20190103.xml
Processing 20412 UniProt records
Progress: 100% [######################################################################] Time: 0:00:10
Now have 98655 UniProt to ENSG mappings.

Processing 29366 lines in file ../data/Ensembl/Rattus_norvegicus.Rnor_6.0.94.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Processing 68769 lines in file ../data/Ensembl/Mus_musculus.GRCm38.94.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Processing 115384 lines in file ../data/Ensembl/Homo_sapiens.GRCh38.94.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Now have 146382 UniProt to ENSG mappings.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:00:47
20412 targets processed
  Inserted 21608 new ENSG xref rows for 19452 proteins
  No ENSG found for 960 UniProt accessions. See logfile ./tcrd6logs/load-ENSGs.py.log for details.

Processing 121277 TCRD nhproteins
Progress: 100% [######################################################################] Time: 0:00:53
121277 nhproteins processed
  Inserted 56226 new ENSG xref rows for 55313 nhproteins
  No ENSG found for 65964 UniProt accessions. See logfile ./tcrd6logs/load-ENSGs.py.log for details.

load-ENSGs.py: Done. Elapsed time: 0:05:21.985

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-4.sql


# NCBI Gene
mysql> INSERT INTO xref_type (name) VALUES ('PubMed');

[smathias@juniper loaders]$ ./load-NCBIGene.py --dbname tcrd6 --loglevel 20

load-NCBIGene.py (v2.2.0) [Fri Apr  5 12:35:29 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading NCBI Gene annotations for 20412 TCRD targets
Progress: 100% [######################################################################] Time: 8:19:53
Processed 20412 targets.
Skipped 259 targets with no geneid
Loaded NCBI annotations for 20150 targets
Total targets remaining for retries: 3 

Retry loop 1: Loading NCBI Gene annotations for 3 TCRD targets
Progress: 100% [######################################################################] Time: 0:00:43
Processed 3 targets.
  Annotated 3 additional targets
  Total annotated targets: 20153

Inserted 53920 aliases
Inserted 12900 NCBI Gene Summary tdl_infos
Inserted 20153 NCBI Gene PubMed Count tdl_infos
Inserted 740376 GeneRIFs
Inserted 1205815 PubMed xrefs
WARNNING: 3 XML parsing errors occurred. See logfile ./tcrd6logs/load-NCBIGene.py.log for details.

load-NCBIGene.py: Done. Elapsed time: 8:20:37.281

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-5.sql


# STRING IDs
[smathias@juniper loaders]$ ./load-STRINGIDs.py --dbname tcrd6

load-STRINGIDs.py (v2.7.0) [Mon Apr  8 09:51:46 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 19184 input lines in file ../data/JensenLab/human.uniprot_2_string.2018.tsv
Progress: 100% [######################################################################] Time: 0:00:00
19184 input lines processed.
  Skipped 1877 non-identity lines
  Got 34612 uniprot/name to STRING ID mappings

Processing 2224813 input lines in file ../data/JensenLab/9606.protein.aliases.v11.0.txt
Progress: 100% [######################################################################] Time: 0:00:07
2224813 input lines processed.
  Added 2137567 alias to STRING ID mappings
  Skipped 52633 aliases that would override UniProt mappings. See logfile ./tcrd6logs/load-STRINGIDs.py.log for details.

Loading STRING IDs for 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:10:33
Updated 19121 STRING ID values
No stringid found for 1291 proteins. See logfile ./tcrd6logs/load-STRINGIDs.py.log for details.

load-STRINGIDs.py: Done. Elapsed time: 0:10:42.026

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-6.sql


# DrugCentral
[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd6

load-DrugCentral.py (v2.3.0) [Mon Apr  8 10:20:31 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 4531 input lines in file ../data/DrugCentral/drug_name_id_10122018.tsv
4531 input lines processed.
Saved 4531 keys in infos map

Processing 1866 input lines in file ../data/DrugCentral/drug_info_10122018.tsv
1866 input lines processed.
Saved 1866 keys in infos map

Processing 3219 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_10122018.tsv
3219 DrugCentral Tclin rows processed.
  Inserted 3205 new drug_activity rows
WARNNING: DrugCentral ID not found for 14 drug names. See logfile ./tcrd6logs/load-DrugCentral.py.log for details.

Processing 663 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_10122018.tsv
663 DrugCentral Tchem rows processed.
  Inserted 662 new drug_activity rows
WARNNING: DrugCentral ID not found for 1 drug names. See logfile ./tcrd6logs/load-DrugCentral.py.log for details.

Processing 10958 lines from indications file ../data/DrugCentral/drug_indications_10122018.tsv
10958 DrugCentral indication rows processed.
  Inserted 12671 new disease rows
WARNNING: 1036 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:12.324

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-7.sql


# JensenLab PubMed Scores
[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd6

load-JensenLabPubMedScores.py (v2.2.0) [Mon Apr  8 10:31:29 2019]:

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:04.107

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 383751 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [######################################################################] Time: 0:05:24
383751 input lines processed.
  Inserted 384954 new pmscore rows for 17982 targets
No target found for 229 STRING IDs. See logfile ./tcrd6logs/load-JensenLabPubMedScores.py.log for details.

Loading 17982 JensenLab PubMed Score tdl_infos
17982 processed
  Inserted 17982 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done. Elapsed time: 0:05:35.314

mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/tmp/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';
Edit that to create InsMissingJLPMSs_TCRDv6.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /tmp/nojlpms.csv > InsZeroJLPMSs_TCRDv6.sql
Edit InsZeroJLPMSs_TCRDv6.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv6.sql

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-8.sql


# IDG2 List/families
# NB. This must be done before loading ChEMBL or IUPHAR
[smathias@juniper loaders]$ ./load-IDG2List.py --dbname tcrd6 

load-IDG2List.py (v1.0.0) [Mon Apr  8 11:36:35 2019]:
Traceback (most recent call last):
  File "./load-IDG2List.py", line 132, in <module>
    load(args)
  File "./load-IDG2List.py", line 54, in load
    fh = logging.FileHandler(logfile)
UnboundLocalError: local variable 'logfile' referenced before assignment
[smathias@juniper loaders]$ ./load-IDG2List.py --dbname tcrd6 

load-IDG2List.py (v1.0.0) [Mon Apr  8 11:36:57 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 417 lines in list file ../data/IDG_TargetList_20190124.csv
Progress: 100% [######################################################################] Time: 0:00:03
417 lines processed
416 targets updated with IDG2 flags
416 targets updated with fams

load-IDG2List.py: Done. Elapsed time: 0:00:03.666

# IDG Families from Miami
File modified to v2 with following changes:
Q9NSE7 - obsolete; deleted
O60344 - obsolete; changed to P0DPD6
Q5T4J0 - obsolete; deleted
P0CW71 - obsolete; deleted
Q9NX53 - obsolete; changed to Q8N9H8
[smathias@juniper loaders]$ ./load-IDGFams.py --dbname tcrd6

load-IDGFams.py (v1.3.0) [Mon Apr  8 11:38:26 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 8147 lines in file ../data/IDG_Families_UNM_UMiami_v2.csv
Progress: 100% [######################################################################] Time: 0:00:20
8147 rows processed.
7731 IDG family designations loaded into TCRD.
5207 IDG extended family designations loaded into TCRD.
Skipped 415 IDG2 targets.

load-IDGFams.py: Done. Elapsed time: 0:00:20.187

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-9.sql


# Antibodypedia
[smathias@juniper loaders]$ ./load-Antibodypedia.py --dbname tcrd6

load-Antibodypedia.py (v2.2.0) [Mon Apr  8 16:10:37 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading Antibodypedia annotations for 20412 TCRD targets
Progress: 100% [#####################################################################] Time: 13:05:10
20412 TCRD targets processed.
  Inserted 20412 Ab Count tdl_info rows
  Inserted 20412 MAb Count tdl_info rows
  Inserted 20412 Antibodypedia.com URL tdl_info rows

load-Antibodypedia.py: Done. Elapsed time: 13:05:10.689

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-10.sql


# ChEMBL
[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd6 --loglevel 20

load-ChEMBL.py (v3.1.0) [Tue Apr  9 09:26:02 2019]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 10926 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
10926 input lines processed.

Processing 8617 UniProt to ChEMBL ID(s) mappings
Progress: 100% [######################################################################] Time: 0:22:35
8617 UniProt accessions processed.
  1951 targets have no qualifying TCRD activities in ChEMBL
Inserted 489802 new cmpd_activity rows
Inserted 1791 new ChEMBL First Reference Year tdl_infos
WARNING: 9 database errors occured. See logfile ./tcrd6logs/load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 17923 selective compounds
Inserted 755 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 0:23:35.766

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-11.sql


# GuideToPharmacology
[smathias@juniper loaders]$ ./load-GuideToPharmacology.py --dbname tcrd6

load-GuideToPharmacology.py (v1.1.0) [Tue Apr  9 13:01:27 2019]:

Downloading  http://www.guidetopharmacology.org/DATA/ligands.csv
         to  ../data/GuideToPharmacology/ligands.csv
Downloading  http://www.guidetopharmacology.org/DATA/interactions.csv
         to  ../data/GuideToPharmacology/interactions.csv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 9663 lines in input file ../data/GuideToPharmacology/ligands.csv
  Got info for 7285 ligands
  Skipped 2377 antibodies/peptides

Processing 18884 lines in input file ../data/GuideToPharmacology/interactions.csv
Progress: 100% [######################################################################] Time: 0:00:13
18884 rows processed.
  Inserted 11191 new cmpd_activity rows for 1321 targets
  Skipped 0 with below cutoff activity values
  Skipped 2451 activities with multiple targets
  Skipped 3793 antibody/peptide activities
  Skipped 3797 activities with missing data
No target found for 21 uniprots/symbols. See logfile ./tcrd6logs/load-GuideToPharmacology.py.log for details.

load-GuideToPharmacology.py: Done. Elapsed time: 0:00:29.306

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-12.sql


# GO Experimental and Functional Leaf terms
[smathias@juniper loaders]$ ./load-GOExptFuncLeafTDLIs.py --dbname tcrd6

load-GOExptFuncLeafTDLIs.py (v2.2.0) [Tue Apr  9 13:03:08 2019]:

Downloading  http://www.geneontology.org/ontology/go.obo
         to  ../data/GO/go.obo
Done.

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:10:16
20412 TCRD targets processed.
  Inserted 7107 new  tdl_info rows

load-GOExptFuncLeafTDLIs.py: Done. Elapsed time: 0:10:20.499

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-13.sql


# TDLs
[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v3.0.0) [Wed Apr 10 09:08:31 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:10:06
20412 TCRD targets processed.
Set TDL values for 20412 targets:
  613 targets are Tclin
  1639 targets are Tchem
  11792 targets are Tbio - 590 bumped from Tdark
  6368 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:10:06.920

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-14.sql


##
## Ontologies
##
[smathias@juniper loaders]$ ./load-DO.py --dbname tcrd6

load-DO.py (v3.1.0) [Wed Apr 10 10:58:44 2019]:

Downloading  http://purl.obolibrary.org/obo/doid.obo
         to  ../data/DiseaseOntology/doid.obo
Done.

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
Got 9233 Disease Ontology terms

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading 9233 Disease Ontology terms
Progress: 100% [######################################################################] Time: 0:00:15
9233 terms processed.
  Inserted 9233 new do rows

load-DO.py: Done. Elapsed time: 0:00:18.782

[smathias@juniper loaders]$ ./load-MPO.py --dbname tcrd6

load-MPO.py (v1.0.0) [Wed Apr 10 10:59:31 2019]:

Downloading  http://www.informatics.jax.org/downloads/reports/mp.owl
         to  ../data/MPO/mp.owl
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing Mammalian Phenotype Ontology file ../data/MPO/mp.owl
Got 12894 MP terms

Loading 12894 Mammalian Phenotype Ontology terms
Progress: 100% [######################################################################] Time: 0:00:05
12894 terms processed.
  Inserted 12894 new mpo rows

load-MPO.py: Done. Elapsed time: 0:00:10.421

[smathias@juniper loaders]$ ./load-RDO.py --dbname tcrd6

load-RDO.py (v1.0.0) [Wed Apr 10 11:00:07 2019]:

Downloading  ftp://ftp.rgd.mcw.edu/pub/ontology/disease/RDO.obo
         to  ../data/RGD/RDO.obo
Done.

Parsing RGD Disease Ontology file ../data/RGD/RDO.obo
Got 18085 RGD Disease Ontology terms

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading 18085 RGD Disease Ontology terms
Progress: 100% [######################################################################] Time: 0:00:15
18085 terms processed.
  Inserted 18085 new rdo rows

load-RDO.py: Done. Elapsed time: 0:00:20.383

[smathias@juniper loaders]$ ./load-Uberon.py --dbname tcrd6

load-Uberon.py (v1.0.0) [Wed Apr 10 11:00:51 2019]:

Downloading  http://purl.obolibrary.org/obo/uberon/ext.obo
         to  ../data/Uberon/ext.obo
Done.

Parsing Uberon file ../data/Uberon/ext.obo
Got 18117 good Uberon terms

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading 18117 Uberon terms
Progress: 100% [######################################################################] Time: 0:00:27
18117 terms processed.
  Inserted 18117 new uberon rows

load-Uberon.py: Done. Elapsed time: 0:00:33.677

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-15.sql

##
## Orthologs
##
# KMC
[smathias@juniper loaders]$ ./load-Orthologs.py --dbname tcrd6

load-Orthologs.py (v1.4.0) [Wed Apr 10 11:05:45 2019]:

Processing 1044735 lines in input file ../data/HGNC/human_all_hcop_sixteen_column.txt
  Generated ortholog dataframe with 182956 entries

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading ortholog data for 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:15:45
Processed 20412 targets.
Loaded 178756 new ortholog rows
  Skipped 3665 empty ortholog entries
  Skipped 167 targets with no sym/geneid

load-Orthologs.py: Done. Elapsed time: 0:15:54.295

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-16.sql

# Homologene
Run DDL in tcrdmp.sql to create homologene table

[smathias@juniper loaders]$ ./load-HomoloGene.py --dbname tcrd6

load-HomoloGene.py (v1.0.0) [Wed Apr 10 15:24:29 2019]:

Downloading  ftp://ftp.ncbi.nih.gov/pub/HomoloGene/current/homologene.data
         to  ../data/NCBI/homologene.data
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 275237 input lines in file ../data/NCBI/homologene.data
Progress: 100% [######################################################################] Time: 0:52:58
Processed 275237 lines.
Loaded 69991 new homologene rows
  Skipped 214285 non-Human/Mouse/Rat lines
WARNNING: No target/nhprotein found for 5840 lines. See logfile tcrd6logs/load-HomoloGene.py.log for details.

load-HomoloGene.py: Done. Elapsed time: 0:53:31.339

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-17.sql

# PubTator
[smathias@juniper loaders]$ ./load-PubTatorScores.py --dbname tcrd6

load-PubTatorScores.py (v2.2.0) [Thu Apr 11 10:08:43 2019]:

Downloading  http://download.jensenlab.org/KMC/Medline/pubtator_counts.tsv
         to  ../data/JensenLab/pubtator_counts.tsv
Done. Elapsed time: 0:00:07.606

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 1208672 lines in file ../data/JensenLab/pubtator_counts.tsv
Progress: 100% [######################################################################] Time: 1:03:51
1208672 lines processed.
  Inserted 468019 new ptscore rows for 18310 targets.
No target found for 166634 NCBI Gene IDs. See logfile ./tcrd6logs/load-PubTatorScores.py.log for details.

Loading 18310 PubTator Score tdl_infos
/home/app/TCRD/loaders/TCRD.py:586: Warning: Data truncated for column 'number_value' at row 1
  curs.execute(sql, (xid, itype, value))
18310 processed
Inserted 18310 new PubTator PubMed Score tdl_info rows

load-PubTatorScores.py: Done. Elapsed time: 1:04:08.283

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-18.sql


# Fix for CD97 : obsolete sysmbol
mysql> UPDATE protein set sym = 'ADGRE5' where id = 2322;
# Orthologs are messed up for CD97/'ADGRE5', so redo:
mysql> DELETE from ortholog;

[smathias@juniper loaders]$ ./load-Orthologs.py --dbname tcrd6

load-Orthologs.py (v1.4.0) [Thu Apr 11 11:32:06 2019]:

Processing 1044735 lines in input file ../data/HGNC/human_all_hcop_sixteen_column.txt
  Generated ortholog dataframe with 182956 entries

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading ortholog data for 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:17:32
Processed 20412 targets.
Loaded 178759 new ortholog rows
  Skipped 3665 empty ortholog entries
  Skipped 167 targets with no sym/geneid

load-Orthologs.py: Done. Elapsed time: 0:17:41.516

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-19.sql


##
## Diseases
## 
# JensenLab DISEASES
[smathias@juniper loaders]$ ./load-JensenLab-DISEASES.py --dbname tcrd6

load-JensenLab-DISEASES.py (v2.2.0) [Thu Apr 11 12:01:55 2019]:

Downloading  http://download.jensenlab.org/human_disease_knowledge_filtered.tsv
         to  ../data/JensenLab/human_disease_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_experiments_filtered.tsv
         to  ../data/JensenLab/human_disease_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_textmining_filtered.tsv
         to  ../data/JensenLab/human_disease_textmining_filtered.tsv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 6894 lines in file ../data/JensenLab/human_disease_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:02:58
6894 lines processed.
Inserted 7110 new disease rows for 3520 proteins
No target found for 35 stringids/symbols. See logfile ./tcrd6logs/load-JensenLab-DISEASES.py.log for details.
WARNING: 253 DB errors occurred. See logfile ./tcrd6logs/load-JensenLab-DISEASES.py.log for details.

Processing 23328 lines in file ../data/JensenLab/human_disease_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 0:09:58
23328 lines processed.
Inserted 23401 new disease rows for 12302 proteins
No target found for 52 stringids/symbols. See logfile ./tcrd6logs/load-JensenLab-DISEASES.py.log for details.

Processing 57093 lines in file ../data/JensenLab/human_disease_textmining_filtered.tsv
Progress: 100% [######################################################################] Time: 0:24:23
57093 lines processed.
Inserted 56459 new disease rows for 13030 proteins
No target found for 1275 stringids/symbols. See logfile ./tcrd6logs/load-JensenLab-DISEASES.py.log for details.

load-JensenLab-DISEASES.py: Done. Elapsed time: 0:37:27.668

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-20.sql

# DisGeNET
[smathias@juniper loaders]$ ./load-DisGeNET.py --dbname tcrd6

load-DisGeNET.py (v2.2.0) [Fri Apr 12 11:00:57 2019]:

Downloading http://www.disgenet.org/static/disgenet_ap1/files/downloads/curated_gene_disease_associations.tsv.gz
         to ../data/DisGeNET/curated_gene_disease_associations.tsv.gz
Uncompressing ../data/DisGeNET/curated_gene_disease_associations.tsv.gz

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 81747 lines in file ../data/DisGeNET/curated_gene_disease_associations.tsv
Progress: 100% [######################################################################] Time: 0:01:51
81747 lines processed.
Loaded 82875 new disease rows for 9025 proteins.
No target found for 494 symbols/geneids. See logfile ./tcrd6logs/load-DisGeNET.py.log for details.

load-DisGeNET.py: Done. Elapsed time: 0:01:53.947

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-21.sql

# Monarch
[smathias@juniper python]$ ./exp-Monarch.py 

exp-Monarch.py (v1.0.0) [Mon Apr 15 11:59:46 2019]:

Connected to TCRD database tcrd (schema ver 5.1.0, data ver 5.4.2)

Processing 20244 TCRD targets
Progress: 100% [######################################################################] Time: 0:24:59
20244 targets processed.
  9509 Monarch diseases exported to file ../exports/TCRDv5.4.2_MonarchDiseases.csv.
  37902 Monarch ortholog_diseases exported to file ../exports/TCRDv5.4.2_MonarchOrthologDiseases.csv.
  WARNING: No ortholog found for 60 ortholog_diseases.

exp-Monarch.py: Done.

[smathias@juniper loaders]$ ./load-MonarchDiseases.py --dbname tcrd6

load-MonarchDiseases.py (v1.2.0) [Tue Apr 16 11:45:24 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 9511 lines in file ../exports/TCRDv5.4.2_MonarchDiseases.csv
Progress: 100% [######################################################################] Time: 0:00:19
9511 lines processed.
Loaded 9509 new disease rows for 3825 proteins.
WARNING: No target found for 1 UniProts/symbols. See logfile ./tcrd6logs/load-MonarchDiseases.py.log for details.

load-MonarchDiseases.py: Done. Elapsed time: 0:00:19.212

[smathias@juniper loaders]$ ./load-MonarchOrthologDiseases.py --dbname tcrd6

load-MonarchOrthologDiseases.py (v1.2.0) [Tue Apr 16 11:45:51 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 113895 orthologs from TCRD

Processing 37902 lines in file ../exports/TCRDv5.4.2_MonarchOrthologDiseases.csv
Progress: 100% [######################################################################] Time: 1:13:51
37902 lines processed.
  Inserted 37852 new ortholog_disease rows for 3827 proteins.
WARNING: No ortholog found for 3 symbols/geneids. See logfile tcrd6logs/load-MonarchOrthologDiseases.py.log for details.

load-MonarchOrthologDiseases.py: Done. Elapsed time: 1:13:53.454

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-22.sql

# Expression Atlas
[smathias@juniper loaders]$ ./load-ExpressionAtlas-Diseases.py --dbname tcrd6

load-ExpressionAtlas-Diseases.py (v2.2.0) [Tue Apr 16 14:51:30 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 171747 lines in file ../data/ExpressionAtlas/disease_assoc_human_do_uniq.tsv
Progress: 100% [######################################################################] Time: 0:17:48
171746 lines processed.
Loaded 159846 new disease rows for 16784 proteins.
No target found for 5814 symbols/ensgs. See logfile ./tcrd6logs/load-ExpressionAtlas-Diseases.py.log for details.

load-ExpressionAtlas-Diseases.py: Done. Elapsed time: 0:17:48.705

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-23.sql

# CTD
[smathias@juniper loaders]$ ./load-CTD-Diseases.py --dbname tcrd6

load-CTD-Diseases.py (v1.1.0) [Tue Apr 16 15:49:37 2019]:

Downloading http://ctdbase.org/reports/CTD_genes_diseases.tsv.gz
         to ../data/CTD/CTD_genes_diseases.tsv.gz
Uncompressing ../data/CTD/CTD_genes_diseases.tsv.gz

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 70483262 lines in file ../data/CTD/CTD_genes_diseases.tsv
Progress: 100% [######################################################################] Time: 0:04:47
70483262 lines processed.
Loaded 35187 new disease rows for 7837 proteins.
Skipped 70452276 with no direct evidence.
No target found for 810 symbols/geneids. See logfile ./tcrd6logs/load-CTD-Diseases.py.log for details.

load-CTD-Diseases.py: Done. Elapsed time: 0:04:58.526

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-24.sql

# eRAM
[smathias@juniper loaders]$ ./load-eRAM.py --dbname tcrd6

load-eRAM.py (v1.1.0) [Tue Apr 16 15:56:02 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 15942 disease names in shelf file ../data/eRAM/eRAM.db
Progress: 100% [######################################################################] Time: 0:02:18
15942 lines processed.
Inserted 14660 new disease rows for 5694 proteins
Skipped 332 diseases with no currated genes. See logfile ./tcrd6logs/load-eRAM.py.log for details.
55 disease names cannot be decoded to strs. See logfile ./tcrd6logs/load-eRAM.py.log for details.
No target found for 374 stringids/symbols. See logfile ./tcrd6logs/load-eRAM.py.log for details.

load-eRAM.py: Done. Elapsed time: 0:02:18.713

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-25.sql


##
## Phenotypes
##
# OMIM
[smathias@juniper loaders]$ ./load-OMIM.py --dbname tcrd6

load-OMIM.py (v2.2.0) [Wed Apr 17 11:13:51 2019]:

Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/genemap.txt
         to  ../data/OMIM/genemap.txt
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/mimTitles.txt
         to  ../data/OMIM/mimTitles.txt
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/phenotypicSeries.txt
         to  ../data/OMIM/phenotypicSeries.txt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 26237 lines from input file ../data/OMIM/mimTitles.txt
Progress: 100% [######################################################################] Time: 0:00:09
26237 lines processed
  Skipped 16 commented lines.
Loaded 26221 new omim rows

Processing 4378 lines from input file ../data/OMIM/phenotypicSeries.txt
Progress: 100% [######################################################################] Time: 0:00:01
4378 lines processed
  Skipped 3 commented lines.
Loaded 4375 new omim_ps rows

Processing 17044 lines from input file ../data/OMIM/genemap.txt
Progress: 100% [######################################################################] Time: 0:03:56
17044 lines processed
  Skipped 160 commented lines.
  Skipped 404 provisional phenotype rows.
  Skipped 143 deletion/duplication syndrome rows.
Loaded 14147 OMIM phenotypes for 13856 targets
No target found for 2729 good lines. See logfile ./tcrd6logs/load-OMIM.py.log for details.

load-OMIM.py: Done. Elapsed time: 0:04:07.720

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-26.sql

# GWAS Catalog
[smathias@juniper loaders]$ ./load-GWASCatalog.py --dbname tcrd6

load-GWASCatalog.py (v2.2.0) [Wed Apr 17 11:41:04 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 134704 lines from input file ../data/EBI/gwas_catalog_v1.0.2-associations_e96_r2019-04-06.tsv
Progress: 100% [######################################################################] Time: 0:16:52
134704 lines processed.
Inserted 124149 new gwas rows for 13116 proteins
No target found for 12674 symbols. See logfile ./tcrd6logs/load-GWASCatalog.py.log for details.

load-GWASCatalog.py: Done. Elapsed time: 0:16:52.928

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-27.sql

# IMPC
[smathias@juniper loaders]$ ./load-IMPC-Phenotypes.py --dbname tcrd6

load-IMPC-Phenotypes.py (v2.4.0) [Wed Apr 17 12:07:54 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 28115 lines from input file ../data/IMPC/IMPC_genotype_phenotype.csv
Progress: 100% [######################################################################] Time: 0:37:24
28114 lines processed.
Loaded 123440 IMPC phenotypes for 16782 nhproteins
No nhprotein found for 50 gene symbols. See logfile ./tcrd6logs/load-IMPC-Phenotypes.py.log for details.
Skipped 403 lines with no term_id or term_name.

Processing 1555293 lines from input file ../data/IMPC/IMPC_ALL_statistical_results.csv
Progress: 100% [######################################################################] Time: 2:16:35
1555081 lines processed.
Loaded 447399 IMPC phenotypes for 22093 nhproteins
No nhprotein found for 88 gene symbols. See logfile ./tcrd6logs/load-IMPC-Phenotypes.py.log for details.
Skipped 771697 lines with no term_id/term_name or no p-value.
Skipped 664201 lines with p-value > 0.05.

load-IMPC-Phenotypes.py: Done. Elapsed time: 2:54:01.417

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-28.sql

# JAX/MGI Human Ortholog Phenotype
[smathias@juniper loaders]$ ./load-JAX-Phenotypes.py --dbname tcrd6

load-JAX-Phenotypes.py (v2.3.0) [Thu Apr 18 09:44:09 2019]:

Downloading  http://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt
         to  ../data/JAX/HMD_HumanPhenotype.rpt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing Mammalian Phenotype Ontology file ../data/JAX/../data/MPO/mp.owl
Got 13283 MP terms

Processing 18747 lines from input file ../data/JAX/HMD_HumanPhenotype.rpt
Progress: 100% [######################################################################] Time: 0:01:39
18747 lines processed.
Loaded 58398 new phenotype rows for 10204 proteins
  Skipped 8414 lines with no MP terms
No target found for 119 gene symbols/ids. See logfile ./tcrd6logs/load-JAX-Phenotypes.py.log for details.

load-JAX-Phenotypes.py: Done. Elapsed time: 0:01:43.414

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-29.sql

# RGD Phenotypes
[smathias@juniper R]$ ./process-RGD.R

Run DDL in tcrdmp.sql to create rat_qtl and rat_term tables.

[smathias@juniper loaders]$ ./load-RGD.py --dbname tcrd6

load-RGD.py (v1.0.0) [Tue Apr 23 12:08:29 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 1800 lines in processed RGD file ../data/RGD/rat_qtls.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Processed 1800 lines
  Inserted 1799 new rat_qtl rows for 908 nhproteins.

Processing 117603 lines in processed RGD file ../data/RGD/rat_terms.tsv
Progress: 100% [######################################################################] Time: 0:00:48
Processed 117603 lines
  Inserted 117602 new rat_term rows.

load-RGD.py: Done. Elapsed time: 0:00:49.231

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-30.sql


## Fix IDG Flags for year 3

mysql> select fam, count(*) from target where idg2 group by fam;
+--------+----------+
| fam    | count(*) |
+--------+----------+
| GPCR   |      152 |
| IC     |      102 |
| Kinase |      162 |
+--------+----------+

mysql> ALTER table target CHANGE idg2 idg tinyint(1) NOT NULL DEFAULT 0;
mysql> UPDATE target SET idg = 0;

mysql> delete from provenance where dataset_id = 11;
mysql> delete from dataset where id = 11;

[smathias@juniper loaders]$ ./load-IDGList.py --dbname tcrd6

load-IDGList.py (v2.0.0) [Thu Aug 15 13:42:15 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 329 lines in list file ../data/IDG_Lists/IDG_List_v3.1-QCd_6-10-2019.csv
Progress: 100% [######################################################################] Time: 0:00:02
329 lines processed
329 targets updated with IDG flags
329 targets updated with fams
  116 targets updated with famexts

load-IDGList.py: Done. Elapsed time: 0:00:02.634

mysql> select fam, count(*) from target where idg group by fam;
+--------+----------+
| fam    | count(*) |
+--------+----------+
| GPCR   |      117 |
| IC     |       62 |
| Kinase |      150 |
+--------+----------+
mysql> select fam, famext, count(*) from target where idg group by fam, famext;
+--------+-----------+----------+
| fam    | famext    | count(*) |
+--------+-----------+----------+
| GPCR   | NULL      |        1 |
| GPCR   | adhesion  |       18 |
| GPCR   | frizzled  |        1 |
| GPCR   | group A   |       67 |
| GPCR   | group C   |        5 |
| GPCR   | other 7TM |        2 |
| GPCR   | taste     |       23 |
| IC     | NULL      |       62 |
| Kinase | NULL      |      150 |
+--------+-----------+----------+

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-31.sql


##
## Expression
##
For v6, we are going to put GTEx in a separate table because it will have all the SABV stuff
that no other sources have. So we will also remove columns from expression that were only
used by GTEx.

mysql> ALTER TABLE expression DROP COLUMN age;
mysql> ALTER TABLE expression DROP COLUMN sex;

# JensenLab TISSUES
mysql> INSERT INTO expression_type (name, data_type, description) VALUES ('JensenLab Experiment Cardiac proteome', 'String', 'JensenLab Experiment channel using Cardiac proteome');

[smathias@juniper loaders]$ ./load-JensenLab-TISSUES.py --dbname tcrd6

load-JensenLab-TISSUES.py (v2.3.0) [Thu Aug 15 15:07:26 2019]:

Downloading  http://download.jensenlab.org/human_tissue_knowledge_filtered.tsv
         to  ../data/JensenLab/human_tissue_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_tissue_experiments_filtered.tsv
         to  ../data/JensenLab/human_tissue_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_tissue_textmining_filtered.tsv
         to  ../data/JensenLab/human_tissue_textmining_filtered.tsv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 147 tissue to Uberon ID mappings from file ../data/Tissue2Uberon.txt

Processing 64890 lines in input file ../data/JensenLab/human_tissue_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:19:52
64890 rows processed.
  Inserted 68777 new expression rows for 16750 proteins
No target found for 28 stringids/symbols. See logfile ./tcrd6logs/load-JensenLab-TISSUES.py.log for details.
No Uberon ID found for 105 tissues. See logfile ./tcrd6logs/load-JensenLab-TISSUES.py.log for details.

Processing 1613114 lines in input file ../data/JensenLab/human_tissue_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 5:33:51
1613114 rows processed.
  Inserted 1621005 new expression rows for 18202 proteins
  Skipped 0 zero confidence rows
No target found for 93 stringids/symbols. See logfile ./tcrd6logs/load-JensenLab-TISSUES.py.log for details.
No Uberon ID found for 5 tissues. See logfile ./tcrd6logs/load-JensenLab-TISSUES.py.log for details.

Processing 63225 lines in input file ../data/JensenLab/human_tissue_textmining_filtered.tsv
/home/app/TCRD/loaders/TCRDMP.py:655: Warning: Data truncated for column 'conf' at row 1ETA:  0:41:08
  curs.execute(sql, params)
Progress: 100% [######################################################################] Time: 0:19:39
63225 rows processed.
  Inserted 62098 new expression rows for 12668 proteins
No target found for 1372 stringids/symbols. See logfile ./tcrd6logs/load-JensenLab-TISSUES.py.log for details.
No Uberon ID found for 2763 tissues. See logfile ./tcrd6logs/load-JensenLab-TISSUES.py.log for details.

load-JensenLab-TISSUES.py: Done. Elapsed time: 6:13:37.893

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-32.sql

# GTEx

CREATE TABLE `gtex` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) DEFAULT NULL,
  `tissue` text COLLATE utf8_unicode_ci NOT NULL,
  `gender` enum('F', 'M') COLLATE utf8_unicode_ci NOT NULL,
  `tpm` decimal(12,6) NOT NULL,
  `tpm_rank` decimal(4,3) DEFAULT NULL,
  `tpm_rank_bysex` decimal(4,3) DEFAULT NULL,
  `tpm_level` enum('Not detected','Low','Medium','High') COLLATE utf8_unicode_ci NOT NULL,
  `tpm_level_bysex` enum('Not detected','Low','Medium','High') COLLATE utf8_unicode_ci DEFAULT NULL,
  `tpm_f` decimal(12,6) DEFAULT NULL,
  `tpm_m` decimal(12,6) DEFAULT NULL,
  `log2foldchange` decimal(4,3) DEFAULT NULL,
  `tau` decimal(4,3) DEFAULT NULL,
  `tau_bysex` decimal(4,3) DEFAULT NULL,
  `uberon_id` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `expression_idx1` (`protein_id`),
  -- KEY `expression_idx2` (`uberon_id`),
  CONSTRAINT `fk_gtex_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
  -- CONSTRAINT `fk_gtex_uberon` FOREIGN KEY (`uberon_id`) REFERENCES `uberon` (`uid`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

[smathias@juniper loaders]$ ./load-GTEx.py --dbname tcrd6

load-GTEx.py (v3.0.0) [Fri Aug 16 09:35:32 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 147 tissue to Uberon ID mappings from file ../data/Tissue2Uberon.txt

Processing 1803825 lines in GTEx file ../data/GTEx/gtex_rnaseq_sabv_alltissues.tsv
Progress: 100% [######################################################################] Time: 2:24:25
Processed 1803825 lines
  Inserted 1805436 new expression rows for 18474 proteins (18476 ENSGs)
  No target found for 28 ENSGs. See logfile tcrd6logs/load-GTEx.py.log for details.
No Uberon ID found for 5 tissues. See logfile tcrd6logs/load-GTEx.py.log for details.

load-GTEx.py: Done. Elapsed time: 2:24:25.349

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-33.sql

# HPA

mysql> DELETE FROM info_type WHERE name like 'HPA%';
mysql> INSERT INTO info_type (name, data_type, description) VALUES ('HPA Tissue Specificity Index', 'Number', 'Tau as defined in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005) calculated on HPA Protein data.');
mysql> DELETE FROM expression_type where name like 'HPA%';
mysql> INSERT INTO expression_type (name, data_type, description) VALUES ('HPA', 'String', 'Human Protein Atlas normal tissue expression values.');

[smathias@juniper loaders]$ ./load-HPA.py --dbname tcrd6

load-HPA.py (v3.0.0) [Fri Aug 16 15:15:05 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 147 tissue to Uberon ID mappings from file ../data/Tissue2Uberon.txt

Processing 782712 lines in HPA file ../data/HPA/HPA.tsv
Progress: 100% [######################################################################] Time: 0:10:31
Processed 782712 HPA lines.
  Inserted 782711 new expression rows for 124 proteins.
No Uberon ID found for 50 tissues. See logfile tcrd6logs/load-HPA.py.log for details.

Processing 10529 lines in HPA TAU file ../data/HPA/HPA_TAU.tsv
/home/app/TCRD/loaders/TCRDMP.py:616: Warning: Data truncated for column 'number_value' at row 1--:--
  curs.execute(sql, (xid, itype, value))
Progress: 100% [######################################################################] Time: 0:00:08
Processed 10529 lines.
  Inserted 10485 new HPA Tissue Specificity Index tdl_info rows for 2004 proteins.
  Skipped 43 rows with no tau.

load-HPA.py: Done. Elapsed time: 0:10:40.131

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-34.sql

# HPM
INSERT INTO xref_type (name, description) VALUES ('RefSeq', 'RefSeq mappings loaded from UniProt XML');

[smathias@juniper loaders]$ ./load-UniProtXRefs.py --dbname tcrd6

load-UniProtXRefs.py (v1.0.0) [Mon Aug 19 15:02:27 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing file ../data/UniProt/uniprot-reviewed-human_20190103.xml
Loading RefSeq xrefs for 20412 UniProt records in file ../data/UniProt/uniprot-reviewed-human_20190103.xml
Progress: 100% [######################################################################] Time: 0:01:44
Processed 20412 UniProt records. Elapsed time: 0:01:57.311
  Loaded 55647 RefSeq xrefs for 18992 proteins.

load-UniProtXRefs.py: Done. Total elapsed time: 0:02:02.597

[smathias@juniper loaders]$ ./load-HPM.py --dbname tcrd6

load-HPM.py (v3.0.0) [Tue Aug 20 10:33:32 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 147 tissue to Uberon ID mappings from file ../data/Tissue2Uberon.txt

Processing 901681 lines in HPM file ../data/HPM/HPM.protein.qualitative.2015-09-10.tsv
Progress: 100% [######################################################################] Time: 1:46:55
Processed 901681 lines.
  Inserted 840420 new expression rows for 16303 proteins (27924 RefSeqs)
No target found for 2132 RefSeqs. See logfile tcrd6logs/load-HPM.py.log for details.
No Uberon ID found for 10 tissues. See logfile tcrd6logs/load-HPM.py.log for details.

Processing 30057 lines in Tissue Specificity Index file ../data/HPM/HPM.protein.tau.2015-09-10.tsv
/home/app/TCRD/loaders/TCRDMP.py:616: Warning: Data truncated for column 'number_value' at row 1--:--
  curs.execute(sql, (xid, itype, value))
Progress: 100% [######################################################################] Time: 0:00:18
Processed 30057 lines.
  Inserted 28014 new HPM Protein Tissue Specificity Index tdl_info rows for 16303 proteins.
  Skipped 2132 rows with RefSeqs not in map from expression file.

Processing 518821 lines in HPM file ../data/HPM/HPM.gene.qualitative.2015-09-10.tsv
Progress: 100% [######################################################################] Time: 0:45:11
Processed 518821 lines.
  Inserted 482640 new expression rows for 16088 proteins (15976 Gene Symbols)
  No target found for 1318 symbols. See logfile tcrd6logs/load-HPM.py.log for details.
No Uberon ID found for 10 tissues. See logfile tcrd6logs/load-HPM.py.log for details.

Processing 17295 lines in Tissue Specificity Index file ../data/HPM/HPM.gene.tau.2015-09-10.tsv
Progress: 100% [######################################################################] Time: 0:00:07
Processed 17295 lines.
  Inserted 15976 new HPM Gene Tissue Specificity Index tdl_info rows for 1 proteins.
  Skipped 1318 rows with symbols not in map from expression file

load-HPM.py: Done. Elapsed time: 2:32:34.762

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-35.sql

# HCA

[smathias@juniper loaders]$ ./load-HumanCellAtlas.py --dbname tcrd6

load-HumanCellAtlas.py (v2.0.0) [Tue Aug 20 14:44:39 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Calculating expression level percentiles

Processing 19629 lines from HCA file ../data/HCA/aal3321_Thul_SM_table_S1.csv
Progress: 100% [######################################################################] Time: 0:15:13
Processed 19628 lines.
  Inserted 1075480 new expression rows for 19070 proteins.
  No target found for 538 Symbols/ENSGs. See logfile tcrd6logs/load-HumanCellAtlas.py.log for details

Processing 12004 lines from HCA file ../data/HCA/aal3321_Thul_SM_table_S6.csv
Progress: 100% [######################################################################] Time: 0:00:39
Processed 12003 lines.
  Inserted 18659 new compartment rows for 11906 protein.s
  No target found for 108 UniProts/Symbols. See logfile tcrd6logs/load-HumanCellAtlas.py.log for details

load-HumanCellAtlas.py: Done. Elapsed time: 0:15:53.299

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-36.sql

# Cell Surface Protein Atlas

[smathias@juniper loaders]$ ./load-CSPA.py --dbname tcrd6

load-CSPA.py (v2.0.0) [Tue Aug 20 15:09:31 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 1500 lines from CSPA file ../data/CSPA/S1_File.csv
Progress: 100% [######################################################################] Time: 0:00:08
Processed 1499 CSPA lines.
  Inserted 10104 new expression rows for 1038 proteins.
  Skipped 460 non-high confidence rows
  No target found for 1 UniProts/GeneIDs. See logfile tcrd6logs/load-CSPA.py.log for details

load-CSPA.py: Done. Elapsed time: 0:00:08.710

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-37.sql

# CCLE

INSERT INTO expression_type (name, data_type, description) VALUES ('CCLE', 'Number', 'Broad Institute Cancer Cell Line Encyclopedia expression data.');

[smathias@juniper loaders]$ ./load-CCLE.py --dbname tcrd6

load-CCLE.py (v1.0.0) [Tue Aug 20 15:55:22 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 21716004 lines in processed CCLE file ../data/CCLE/CCLE.tsv.gz
Progress: 100% [#################################################################] Time: 3:22:50
Processed 21716004 lines
  Inserted 21716003 new expression rows for 18750 proteins.

load-CCLE.py: Done. Elapsed time: 3:23:28.647

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-38.sql

# Consensus

[smathias@juniper loaders]$ ./load-ConsensusExpressions.py --dbname tcrd6

load-ConsensusExpressions.py (v3.0.0) [Wed Aug 21 09:12:59 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processiong 249 lines in tissue mapping file: ../data/Tissues_Typed_v2.1.csv
  Got 197 tissue name mappings

Calculating/Loading Consensus expressions for 20412 TCRD targets
Progress: 100% [#################################################################] Time: 0:17:23
Processed 20412 targets.
  Inserted 206312 new Consensus expression rows.

load-ConsensusExpressions.py: Done. Elapsed time: 0:17:23.808

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-39.sql

# Uberon IDs (for UniProt Tissue etype)

[smathias@juniper loaders]$ ./load-Uberon-IDs.py --dbname tcrd6

load-Uberon-IDs.py (v1.0.0) [Wed Aug 21 10:56:11 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 147 tissue to Uberon ID mappings from file ../data/Tissue2Uberon.txt

Processing 70198 UniProt Tissue expression rows
Progress: 100% [#################################################################] Time: 0:13:58
70198 UniProt Tissue expression rows processed.
  Updated 43655 with Uberon IDs
No Uberon ID found for 269 tissues. See logfile tcrd6logs/load-Uberon-IDs.py.log for details.

load-Uberon-IDs.py: Done. Elapsed time: 0:13:58.993

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-40.sql

#
# JensenLab COMPARTMETS
#
[smathias@juniper loaders]$ ./load-JensenLab-COMPARTMENTS.py --dbname tcrd6

load-JensenLab-COMPARTMENTS.py (v3.0.0) [Wed Aug 21 11:27:38 2019]:

Downloading  http://download.jensenlab.org/human_compartment_knowledge_full.tsv
         to  ../data/JensenLab/human_compartment_knowledge_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_experiments_full.tsv
         to  ../data/JensenLab/human_compartment_experiments_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_textmining_full.tsv
         to  ../data/JensenLab/human_compartment_textmining_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_predictions_full.tsv
         to  ../data/JensenLab/human_compartment_predictions_full.tsv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 721830 lines in input file ../data/JensenLab/human_compartment_knowledge_full.tsv
Progress: 100% [######################################################################] Time: 0:09:22
721830 lines processed.
  Inserted 841536 new compartment rows for 17491 proteins
  Skipped 63954 lines with conf < 3
No target found for 128 ENSPs/symbols. See logfile tcrd6logs/load-JensenLab-COMPARTMENTS.py.log for details.

Processing 120408 lines in input file ../data/JensenLab/human_compartment_experiments_full.tsv
Progress: 100% [######################################################################] Time: 0:00:01
120408 lines processed.
  Inserted 2316 new compartment rows for 214 proteins
  Skipped 118112 lines with conf < 3

Processing 880634 lines in input file ../data/JensenLab/human_compartment_textmining_full.tsv
Progress: 100% [######################################################################] Time: 0:02:55
880634 lines processed.
  Inserted 187750 new compartment rows for 12981 proteins
  Skipped 690666 lines with conf < 3
No target found for 733 ENSPs/symbols. See logfile tcrd6logs/load-JensenLab-COMPARTMENTS.py.log for details.

Processing 399795 lines in input file ../data/JensenLab/human_compartment_predictions_full.tsv
Progress: 100% [######################################################################] Time: 0:00:20
399795 lines processed.
  Inserted 25561 new compartment rows for 9822 proteins
  Skipped 374079 lines with conf < 3
No target found for 63 ENSPs/symbols. See logfile tcrd6logs/load-JensenLab-COMPARTMENTS.py.log for details.

load-JensenLab-COMPARTMENTS.py: Done. Elapsed time: 0:13:06.436

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-41.sql

##
## Pathways
##

# KEGG

[smathias@juniper loaders]$ ./load-KEGGPathways.py --dbname tcrd6

load-KEGGPathways.py (v3.0.0) [Wed Aug 21 12:43:00 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Mapping KEGG pathways to gene lists
Processing 335 KEGG Pathways
Progress: 100% [######################################################################] Time: 0:04:58
Processed 335 KEGG Pathways.
  Inserted 32325 pathway rows for 7686 proteins.
  No target found for 304 Gene IDs. See logfile ./tcrd6logs/load-KEGGPathways.py.log for details.

load-KEGGPathways.py: Done. Elapsed time: 0:05:02.207

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-42.sql

# PathwayCommons

[smathias@juniper loaders]$ ./load-PathwayCommons.py --dbname tcrd6

load-PathwayCommons.py (v3.0.0) [Wed Aug 21 12:53:23 2019]:

Downloading  http://www.pathwaycommons.org/archives/PC2/v11/PathwayCommons11.All.uniprot.gmt.gz
         to  ../data/PathwayCommons/PathwayCommons11.All.uniprot.gmt.gz
Uncompressing ../data/PathwayCommons/PathwayCommons11.All.uniprot.gmt.gz

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 3021 records from PathwayCommons file ../data/PathwayCommons/PathwayCommons11.All.uniprot.gmt
Progress: 100% [######################################################################] Time: 0:00:17
Processed 3021 Pathway Commons records.
  Inserted 25066 new pathway rows for 5001 proteins.
  Skipped 1807 records from 'kegg', 'wikipathways', 'reactome'
  No target found for 20 UniProt accessions. See logfile ./tcrd6logs/load-PathwayCommons.py.log for details.

load-PathwayCommons.py: Done. Elapsed time: 0:00:18.260

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-43.sql

# Reactome

[smathias@juniper loaders]$ ./load-ReactomePathways.py --dbname tcrd6

load-ReactomePathways.py (v3.0.0) [Wed Aug 21 14:16:23 2019]:
Downloading  http://www.reactome.org/download/current/ReactomePathways.gmt.zip
         to  ../data/Reactome/ReactomePathways.gmt.zip
Unzipping ../data/Reactome/ReactomePathways.gmt.zip

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 2248 input line from Reactome Pathways file ../data/Reactome/ReactomePathways.gmt
Progress: 100% [######################################################################] Time: 0:02:16
Processed 2248 Reactome Pathways.
  Inserted 110872 pathway rows for 10781 proteins.
  No target found for 255 Gene IDs. See logfile ./tcrd6logs/load-ReactomePathways.py.log for details.

load-ReactomePathways.py: Done. Elapsed time: 0:02:17.702

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-44.sql

# WikiPathways

[smathias@juniper loaders]$ ./load-WikiPathways.py --dbname tcrd6

load-WikiPathways.py (v3.0.0) [Wed Aug 21 14:26:33 2019]:
Downloading  http://www.pathvisio.org/data/bots/gmt/current/gmt_wp_Homo_sapiens.gmt
         to  ../data/WikiPathways/gmt_wp_Homo_sapiens.gmt

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 539 input line from WikiPathways file ../data/WikiPathways/gmt_wp_Homo_sapiens.gmt
Progress: 100% [######################################################################] Time: 0:02:07
Processed 539 WikiPathways.
  Inserted 162449 pathway rows for 6411 proteins.
  No target found for 434 Gene IDs. See logfile ./tcrd6logs/load-WikiPathways.py.log for details.

load-WikiPathways.py: Done. Elapsed time: 0:02:09.266

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-45.sql


##
## PPIs
##
# BioPlex

[smathias@juniper loaders]$ ./load-BioPlexPPIs.py --dbname tcrd6

load-BioPlexPPIs.py (v3.0.0) [Wed Aug 21 14:52:03 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 56553 lines from BioPlex PPI file ../data/BioPlex/BioPlex_interactionList_v4a.tsv
Progress: 100% [######################################################################] Time: 0:01:22
56553 BioPlex PPI rows processed.
  Inserted 56353 new ppi rows
  No target found for 39 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4955 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_May2016.tsv
Progress: 100% [######################################################################] Time: 0:00:26
4955 BioPlex PPI rows processed.
  Inserted 4903 new ppi rows
  No target found for 14 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4305 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Aug2016.tsv
Progress: 100% [######################################################################] Time: 0:00:23
4305 BioPlex PPI rows processed.
  Inserted 4276 new ppi rows
  No target found for 10 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 3160 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Dec2016.tsv
Progress: 100% [######################################################################] Time: 0:00:18
3160 BioPlex PPI rows processed.
  Inserted 3140 new ppi rows
  No target found for 12 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4046 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_April2017.tsv
Progress: 100% [######################################################################] Time: 0:00:21
4046 BioPlex PPI rows processed.
  Inserted 4010 new ppi rows
  No target found for 19 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4464 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Nov2017.tsv
Progress: 100% [######################################################################] Time: 0:00:22
4464 BioPlex PPI rows processed.
  Inserted 4431 new ppi rows
  No target found for 16 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

load-BioPlexPPIs.py: Done. Elapsed time: 0:03:16.008

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-46.sql

# Reactome

mysql> ALTER TABLE ppi ADD COLUMN interaction_type varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL;

[smathias@juniper loaders]$ ./load-ReactomePPIs.py --dbname tcrd6

load-ReactomePPIs.py (v3.0.0) [Wed Aug 21 15:33:08 2019]:

Downloading  https://reactome.org/download/current/interactors/reactome.homo_sapiens.interactions.tab-delimited.txt
         to  ../data/Reactome/reactome.homo_sapiens.interactions.tab-delimited.txt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 82401 lines from Reactome PPI file ../data/Reactome/reactome.homo_sapiens.interactions.tab-delimited.txt
Progress: 100% [######################################################################] Time: 0:00:27
82401 Reactome PPI rows processed.
  Inserted 23507 (23507) new ppi rows
  Skipped 36367 duplicate PPIs
  No target found for 272 UniProt accessions. See logfile ./tcrd6logs/load-ReactomePPIs.py.log for details.

load-ReactomePPIs.py: Done. Elapsed time: 0:00:28.641

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-47.sql


# STRINGDB

mysql> ALTER TABLE ppi ADD COLUMN score int(4) DEFAULT NULL;

[smathias@juniper loaders]$ ./load-STRINGDB.py --dbname tcrd6

load-STRINGDB.py (v1.0.0) [Thu Aug 22 10:41:32 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 11759455 lines in file ../data/STRING/9606.protein.links.v11.0.txt
Progress: 100% [######################################################################] Time: 1:44:21
11759455 lines processed.
  Inserted 11638446 new ppi rows
No target found for 424 ENSPs. See logfile ./tcrd6logs/load-STRINGDB.py.log for details.

load-STRINGDB.py: Done. Elapsed time: 1:44:22.503

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-49.sql

#
# TIN-X
#

[smathias@juniper python]$ ./TIN-X.py --dbname tcrd6

TIN-X.py (v3.0.0) [Thu Aug 22 10:56:50 2019]:

Downloading http://download.jensenlab.org/disease_textmining_mentions.tsv
         to ../data/JensenLab/disease_textmining_mentions.tsv
Downloading http://download.jensenlab.org/human_textmining_mentions.tsv
         to ../data/JensenLab/human_textmining_mentions.tsv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11659 Disease Ontology terms

Processing 21898 lines in protein file ../data/JensenLab/human_textmining_mentions.tsv
Progress: 100% [######################################################################################] Time: 0:04:12
21898 lines processed.
  Skipped 3761 non-ENSP lines
  Saved 18032 protein to PMIDs mappings
  Saved 5142463 PMID to protein count mappings
  No target found for 109 ENSPs. See logfile ../loaders/tcrd6logs/TIN-X.py.log for details.

Processing 9305 lines in file ../data/JensenLab/disease_textmining_mentions.tsv
Progress: 100% [######################################################################################] Time: 0:01:50
9305 lines processed.
  Skipped 1701 non-DOID lines
  Saved 7604 DOID to PMIDs mappings
  Saved 10635277 PMID to disease count mappings

Computing protein novely scores
  Wrote 18032 novelty scores to file ../data/TIN-X/TCRDv6/ProteinNovelty.csv

Computing disease novely scores
  Wrote 7604 novelty scores to file ../data/TIN-X/TCRDv6/DiseaseNovelty.csv

Computing importance scores
  Wrote 3015526 importance scores to file ../data/TIN-X/TCRDv6/Importance.csv

Computing PubMed rankings
  Wrote 53609232 PubMed rankings to file ../data/TIN-X/TCRDv6/PMIDRanking.csv

TIN-X.py: Done. Elapsed time: 3:49:48.017

[smathias@juniper loaders]$ ./load-TIN-X.py --dbname tcrd6

load-TIN-X.py (v3.0.0) [Mon Aug 26 14:19:59 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11659 Disease Ontology terms

Processing 7605 lines in file ../data/TIN-X/TCRDv6/DiseaseNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:03
7604 lines processed.
  Inserted 7604 new tinx_disease rows
  Saved 7604 keys in dmap

Processing 18033 lines in file ../data/TIN-X/TCRDv6/ProteinNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:06
18032 lines processed.
  Inserted 18032 new tinx_novelty rows

Processing 3015527 lines in file ../data/TIN-X/TCRDv6/Importance.csv
Progress: 100% [######################################################################] Time: 0:24:52
3015526 lines processed.
  Inserted 3015526 new tinx_importance rows
  Saved 3015526 keys in imap

Processing 53609233 lines in file ../data/TIN-X/TCRDv6/PMIDRanking.csv
Progress: 100% [######################################################################] Time: 6:47:33
53609232 lines processed.
  Inserted 53609232 new tinx_articlerank rows

load-TIN-X.py: Done. Elapsed time: 7:12:43.119

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-50.sql


# EBI Patent Counts

[smathias@juniper loaders]$ ./load-EBI-PatentCounts.py --dbname tcrd6

load-EBI-PatentCounts.py (v3.0.0) [Tue Aug 27 15:20:03 2019]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/IDG/patent_counts/latest
         to  ../data/EBI/patent_counts/latest
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 41281 lines in file ../data/EBI/patent_counts/latest
Progress: 100% [######################################################################] Time: 0:01:53
41280 lines processed.
Inserted 41280 new patent_count rows for 1710 proteins

Loading 1710 Patent Count tdl_infos
  1710 processed
  Inserted 1710 new EBI Total Patent Count tdl_info rows

load-EBI-PatentCounts.py: Done. Elapsed time: 0:01:59.287

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-51.sql

# KEGG Distances

[smathias@juniper loaders]$ ./load-KEGGDistances.py --dbname tcrd6 --loglevel 20

load-KEGGDistances.py (v3.0.0) [Tue Aug 27 15:29:56 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 292 KGML files in ../data/KEGG/pathways
Progress: 100% [######################################################################] Time: 0:00:09
  Got 204569 total unique non-zero shortest path lengths

Processing 204569 KEGG Distances
Progress: 100% [######################################################################] Time: 0:02:59
204569 KEGG Distances processed.
  Inserted 208238 new kegg_distance rows
  200 KEGG IDs not found in TCRD - Skipped 6560 rows. See logfile ./tcrd6logs/load-KEGGDistances.py.log for details.

load-KEGGDistances.py: Done. Elapsed time: 0:03:08.350

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-52.sql

# KEGG Nearest Tclins

[smathias@juniper loaders]$ ./load-KEGGNearestTclins.py --dbname tcrd6

load-KEGGNearestTclins.py (v3.0.0) [Tue Aug 27 15:38:55 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:01:07

20412 targets processed.
  1864 non-Tclin targets have upstream Tclin target(s)
    Inserted 7563 upstream kegg_nearest_tclin rows
  1919 non-Tclin targets have downstream Tclin target(s)
    Inserted 8348 upstream kegg_nearest_tclin rows

load-KEGGNearestTclins.py: Done. Elapsed time: 0:01:07.344

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-53.sql


# LINCS L1000 Xrefs
mysql> INSERT INTO xref_type (name, description) VALUES ('L1000 ID', 'CMap landmark gene ID. See http://support.lincscloud.org/hc/en-us/articles/202092616-The-Landmark-Genes');

[smathias@juniper loaders]$ ./load-L1000XRefs.py --dbname tcrd6

load-L1000XRefs.py (v3.0.0) [Wed Aug 28 10:08:38 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 978 rows in file ../data/CMap_LandmarkGenes_n978.csv
Progress: 100% [######################################################################] Time: 0:00:09
978 rows processed.
  Inserted 978 new L1000 ID xref rows for 978 proteins.

load-L1000XRefs.py: Done. Elapsed time: 0:00:09.403

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-54.sql


# LocSigDB

[smathias@juniper loaders]$ ./load-LocSigDB.py --dbname tcrd6

load-LocSigDB.py (v2.0.0) [Wed Aug 28 10:19:56 2019]:
Downloading  http://genome.unmc.edu/LocSigDB/doc/LocSigDB.csv
         to  ../data/LocSigDB/LocSigDB.csv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 534 lines in input file ../data/LocSigDB/LocSigDB.csv
Progress: 100% [######################################################################] Time: 0:03:57
534 lines processed.
  Inserted 106521 new locsig rows for 18916 proteins
  Skipped 234 non-human rows
No target found for 463229 UniProts. See logfile ./tcrd6logs/load-LocSigDB.py.log for details.

load-LocSigDB.py: Done. Elapsed time: 0:04:14.458

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-55.sql


# PANTHER protein classes

[smathias@juniper loaders]$ ./load-PANTHERClasses.py --dbname tcrd6

load-PANTHERClasses.py (v3.0.0) [Wed Aug 28 11:28:36 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 301 lines in relationships file ../data/PANTHER/Protein_class_relationship
301 input lines processed.
  Got 255 PANTHER Class relationships

Processing 302 lines in class file ../data/PANTHER/Protein_Class_14.0
302 lines processed.
  Inserted 256 new panther_class rows

Processing 19984 lines in classification file ../data/PANTHER/PTHR14.1_human_
Progress: 100% [######################################################################] Time: 0:00:36
19984 lines processed.
  Inserted 22520 new p2pc rows for 8070 distinct proteins
  Skipped 11704 rows without PCs
No target found for 212 UniProt/HGNCs. See logfile ./tcrd6logs/load-PANTHERClasses.py.log for details.

load-PANTHERClasses.py: Done. Elapsed time: 0:00:36.247

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-56.sql

# PubChem CIDs

[smathias@juniper loaders]$ ./load-PubChemCIDs.py --dbname tcrd6

load-PubChemCIDs.py (v2.0.0) [Wed Aug 28 11:32:53 2019]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/wholeSourceMapping/src_id1/src1src22.txt.gz
         to  ../data/ChEMBL/UniChem/src1src22.txt.gz
Uncompressing ../data/ChEMBL/UniChem/src1src22.txt.gz
Done. Elapsed time: 0:00:04.716

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 1836641 lines in file ../data/ChEMBL/UniChem/src1src22.txt
Got 1812804 ChEMBL to PubChem mappings

Loading PubChem CIDs for 489802 ChEMBL activities
Progress: 100% [######################################################################] Time: 0:04:40
489802 ChEMBL activities processed.
  Inserted 452824 new PubChem CIDs
  19127 ChEMBL IDs not found. See logfile ./tcrd6logs/load-PubChemCIDs.py.log for details.

Loading PubChem CIDs for 3867 drug activities
Progress: 100% [######################################################################] Time: 0:00:02
3867 drug activities processed.
  Inserted 2885 new PubChem CIDs
  Skipped 687 drug activities with no ChEMBL ID
  173 ChEMBL IDs not found. See logfile ./tcrd6logs/load-PubChemCIDs.py.log for details.

load-PubChemCIDs.py: Done. Elapsed time: 0:04:56.943

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-57.sql


# Transcription Factor Flags

[smathias@juniper loaders]$ ./load-TFs.py --dbname tcrd6

load-TFs.py (v2.0.0) [Wed Aug 28 11:44:48 2019]:

Downloading  http://humantfs.ccbr.utoronto.ca/download/v_1.01/DatabaseExtract_v_1.01.csv
         to  ../data/UToronto/DatabaseExtract_v_1.01.csv
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 2766 lines in input file ../data/UToronto/DatabaseExtract_v_1.01.csv
Progress: 100% [######################################################################] Time: 0:00:36

2765 lines processed.
  Inserted 1632 new 'Is Transcription Factor' tdl_infos
  Skipped 1126 non-TF lines
No target found for 7 symbols/geneids/ENSGs. See logfile tcrd6logs/load-TFs.py.log for details.
Tclin: 19
Tchem: 59
Tbio: 1013
Tdark: 541

load-TFs.py: Done. Elapsed time: 0:00:37.919

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-58.sql

# TMHMM Predictions

[smathias@juniper loaders]$ ./load-TMHMM_Predictions.py --dbname tcrd6

load-TMHMM_Predictions.py (v3.0.0) [Wed Aug 28 11:51:30 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:34:03
20412 targets processed.
  Inserted 5350 new TMHMM Prediction tdl_info rows

load-TMHMM_Predictions.py: Done. Elapsed time: 0:34:04.021

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-59.sql


# PubMed

[smathias@juniper loaders]$ ./load-PubMed.py --dbname tcrd6

load-PubMed.py (v3.0.0) [Wed Aug 28 12:36:55 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading pubmeds for 20412 TCRD targets
Progress: 100% [#####################################################################] Time: 19:47:22
Processed 20412 targets.
  Successfully loaded all PubMeds for 20044 targets
  Inserted 576647 new pubmed rows
  Inserted 1190162 new protein2pubmed rows
WARNING: 1 DB errors occurred. See logfile ./tcrd6logs/load-PubMed.py.log for details.

Checking for 2505076 TIN-X PubMed IDs in TCRD

Processing 2170250 TIN-X PubMed IDs not in TCRD
Processed 2170230 TIN-X PubMed IDs.
  Inserted 2170211 new pubmed rows
WARNING: 19 DB errors occurred. See logfile ./tcrd6logs/load-PubMed.py.log for details.

load-PubMed.py: Done. Elapsed time: 38:16:28.350

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-60.sql

# GeneRIF Years

[smathias@juniper python]$ ./mk-PubMed2DateMap.py --dbname tcrd6

mk-PubMed2DateMap.py (v2.0.0) [Fri Aug 30 10:53:36 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 740376 GeneRIFs
Progress: 100% [######################################################################] Time: 0:03:50
740376 GeneRIFs processed.
Got date mapping for 474369 PubMeds in TCRD

Getting 6515 missing PubMeds from E-Utils
  Processing chunk 1
  ...
  Processing chunk 33
740376 PubMed IDs processed.
Got date mapping for 6422 PubMeds not in TCRD
No date for 93 PubMeds
Dumping map to file: ../data/TCRDv6_PubMed2Date.p

mk-PubMed2DateMap.py: Done. Elapsed time: 0:06:35.699

[smathias@juniper loaders]$ ./load-GeneRIF_Years.py --dbname tcrd6

load-GeneRIF_Years.py (v2.0.0) [Fri Aug 30 11:27:29 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 480791 PubMed date mappings from file ../data/TCRDv6_PubMed2Date.p

Processing 740376 GeneRIFs
Progress: 100% [######################################################################] Time: 0:08:10
740376 GeneRIFs processed.
  Updated 721650 genefifs with years
  Skipped 18726 generifs with no years.

load-GeneRIF_Years.py: Done. Elapsed time: 0:08:16.627

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-61.sql


# DRGC Resources
CREATE TABLE `drgc_resource` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) NOT NULL,
  `resource_type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `json` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `drgc_resource_idx1` (`target_id`),
  CONSTRAINT `fk_drgc_resource__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

[smathias@juniper loaders]$ ./load-DRGC_Resources.py --dbname tcrd6

load-DRGC_Resources.py (v2.0.0) [Fri Aug 30 12:38:22 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Getting targets from RSS...
  Got 48 targets with DRGC resource(s)
48 targets processed.
  Inserted 18 new drgc_resource rows for 18 targets

load-DRGC_Resources.py: Done. Elapsed time: 0:00:02.887

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-62.sql


#
# Harmonizome & Harmonogram CDFs
#
mysql> SELECT 'sym', 'pid6', 'pid5' UNION ALL SELECT p6.sym, p6.id AS id6, p5.id AS id5 from tcrd6.protein p6, tcrd5.protein p5 WHERE p6.uniprot = p5.uniprot INTO OUTFILE '/home/app/TCRD/exports/TCRDsym26id5id.csv' FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';

mysql> use tcrd5
mysql> SELECT 'id', 'name', 'association', 'description', 'resource_group', 'measurement', 'attribute_group', 'attribute_type', 'pubmed_ids', 'url' UNION ALL SELECT * FROM gene_attribute_type INTO OUTFILE '/home/app/TCRD/exports/TCRD5-gene_attribute_type.csv' FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';
mysql> SELECT 'id', 'protein_id', 'gat_id', 'name', 'value' UNION ALL SELECT * FROM gene_attribute INTO OUTFILE '/home/app/TCRD/exports/TCRD5-gene_attribute.csv' FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';

[smathias@juniper python]$ ./cnv-HarmonizomeExport.py 

cnv-HarmonizomeExport.py (v1.0.0) [Tue Aug 27 15:07:09 2019]:

Got 20215 TCRD5 to TCRD6 protein.id mappings.

Processing 114 lines in file ../exports/TCRD5-gene_attribute_type.csv
Progress: 100% [######################################################################] Time: 0:00:00
Processed 114 lines
  Wrote 113 new gene_attribute_type rows to file ../SQL/TCRD6-gene_attribute_types.csv

Processing 65592067 lines in file ../exports/TCRD5-gene_attribute.csv
Progress: 100% [######################################################################] Time: 0:04:06
Processed 65592067 lines.
  Wrote 65558185 new gene_attribute rows to file ../SQL/TCRD6-gene_attributes.csv
  Skipped 33881 rows that do not map from v5 to v6.

cnv-HarmonizomeExport.py: Done. Elapsed time: 0:04:12.696

mysql> LOAD DATA INFILE '/home/app/TCRD/SQL/TCRD6-gene_attribute_types.csv' INTO TABLE gene_attribute_type
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

mysql> LOAD DATA INFILE '/home/app/TCRD/SQL/TCRD6-gene_attributes.csv' INTO TABLE gene_attribute
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES; -- takes ~ 30min

mysql> INSERT INTO dataset (name, source, app, app_version, url) VALUES ('Harmonizome', 'API at http://amp.pharm.mssm.edu/Harmonizome/', 'cnv-HarmonizomeExport.py', '1.0.0', 'http://amp.pharm.mssm.edu/Harmonizome/');
mysql> INSERT INTO provenance (dataset_id, table_name) VALUES (72, 'gene_attribute_type');
mysql> INSERT INTO provenance (dataset_id, table_name) VALUES (72, 'gene_attribute'); 

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-63.sql


#
# LINCS
#
CREATE TABLE `lincs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `cellid` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `zscore` decimal(8,6) NOT NULL,
  `pert_dcid` int(11) NOT NULL,
  `pert_smiles` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lincs_idx1` (`protein_id`),
  CONSTRAINT `fk_lincs_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

[smathias@juniper loaders]$ ./load-LINCS.py --dbname tcrd6

load-LINCS.py (v1.0.0) [Wed Aug 21 17:00:25 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 83926092 lines in file ../data/LINCS.csv
/home/app/TCRD/loaders/TCRDMP.py:2093: Warning: Data truncated for column 'zscore' at row 1  --:--:--
  curs.execute(sql, params)
Progress: 100% [#####################################################################] Time: 16:41:25
83926092 lines processed.
Loaded 84097720 new lincs rows for 980 proteins.
No target found for 2 geneids. See logfile tcrd6logs/load-LINCS.py.log for details.

load-LINCS.py: Done. Elapsed time: 16:41:33.945

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-48.sql
[smathias@juniper SQL]$ mysqldump --no-create-db tcrd6 lincs > dumps6/tcrd6-lincs.sql
mysql> drop table lincs;
[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-48-nolincs.sql

[smathias@juniper SQL]$ mysql tcrd6
mysql> \. dumps6/tcrd6-lincs.sql

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-64.sql


# HGram CDFs (forgot to do this)

[smathias@juniper loaders]$ ./load-HGramCDFs.py --dbname tcrd6 

load-HGramCDFs.py (v3.0.0) [Wed Sep  4 09:36:49 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Collecting counts for 113 gene attribute types on 20412 TCRD targets
Progress: 100% [######################################################################] Time: 1:01:44

Calculatig Gene Attribute stats. See logfile tcrd6logs/load-HGramCDFs.py.log.

Loading HGram CDFs for 20412 TCRD targets
./load-HGramCDFs.py:143: RuntimeWarning: invalid value encountered in double_scalars ] ETA:  --:--:--
  err = math.erf((ct - mu) / (sigma * math.sqrt(2.0)))
./load-HGramCDFs.py:124: RuntimeWarning: invalid value encountered in double_scalars
  attr_cdf = 1.0 / (1.0 + math.exp(-1.702*((attr_count-stats[type]['mean']) / stats[type]['std'] )))
/home/app/TCRD/loaders/TCRDMP.py:1343: Warning: Data truncated for column 'attr_cdf' at row 1
  curs.execute(sql, params)
Progress: 100% [######################################################################] Time: 1:11:26
Processed 20412 targets.
  Loaded 1167880 new hgram_cdf rows
  Skipped 19009 NaN CDFs

load-HGramCDFs.py: Done. Elapsed time: 2:13:11.612

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-65.sql


# IMPC Mouse Clones

[smathias@juniper loaders]$ ./load-IMPCMiceTDLInfos.py --dbname tcrd6

load-IMPCMiceTDLInfos.py (v3.0.0) [Wed Sep  4 12:05:31 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 385 rows from input file ../data/IMPC/notifications_by_gene_for_idg-04-09-19--11-09.csv
Progress: 100% [######################################################################] Time: 0:00:13
384 rows processed.
Inserted 311 new 'IMPC Status' tdl_info rows
Inserted 270 new 'IMPC Clones' tdl_info rows
Skipped 25 rows with no relevant info
No target found for 49 rows. See logfile ./tcrd6logs/load-IMPCMiceTDLInfos.py.log for details.

load-IMPCMiceTDLInfos.py: Done. Elapsed time: 0:00:13.718

mysql> update dbinfo set data_ver = '6.0.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.0.0.sql


#
# DTO
#
mysql> ALTER TABLE target CHANGE fam varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL;


