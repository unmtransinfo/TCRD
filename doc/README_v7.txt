Create empty schema with types
------------------------------
[smathias@juniper SQL]$ mysqldump --no-data tcrd6 | sed 's/ AUTO_INCREMENT=[0-9]*\b//g' > create-TCRDv7.sql
[smathias@juniper SQL]$ mysqldump --no-create-db --no-create-info tcrd6 cmpd_activity_type compartment_type data_type disease_type expression_type info_type pathway_type phenotype_type ppi_type xref_type > types_v7.sql
mysql> create database tcrd7;
mysql> use tcrd7
mysql> \. create-TCRDv7.sql
mysql> \. types_v7.sql
Check that everything is good:
mysql> SHOW TABLE STATUS FROM `tcrd7`;
mysql> INSERT INTO dbinfo (dbname, schema_ver, data_ver, owner) VALUES ('tcrd7', '7.0.0', '0.0.0', 'smathias');
[smathias@juniper SQL]$ mysqldump tcrd7 > create-TCRDv7.sql
[smathias@juniper SQL]$ rm types_v7.sql

# UniProt
[smathias@juniper loaders]$ ./load-UniProt.py --dbname tcrd7 --loglevel 20

load-UniProt.py (v4.0.0) [Mon May  4 11:07:02 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Parsing Evidence Ontology file ../data/eco.obo

Parsing file ../data/UniProt/uniprot-reviewed-human_20200504.xml
Loading data for 20365 UniProt records
Progress: 100% [######################################################################] Time: 0:09:35
Processed 20365 UniProt records. Elapsed time: 0:09:48.709
  Loaded 20365 targets/proteins

Parsing file ../data/UniProt/uniprot-mouse_20200504.xml
Loading data for 86453 UniProt records
Progress: 100% [######################################################################] Time: 0:06:28
Processed 86453 UniProt records. Elapsed time: 0:06:48.460
  Loaded 86453 nhproteins

Parsing file ../data/UniProt/uniprot-rat_20200504.xml
Loading data for 36152 UniProt records
Progress: 100% [######################################################################] Time: 0:02:51
Processed 36152 UniProt records. Elapsed time: 0:03:02.025
  Loaded 36152 nhproteins

load-UniProt.py: Done. Total elapsed time: 0:19:48.805

Some UniProt records have multiple Gene IDs. The loader takes the first
one, but this is not always the right one. So manual fixes to Gene IDs:
mysql> \. update_geneids7.sql

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-1.sql


# HGNC
[smathias@juniper loaders]$ ./load-HGNC.py --dbname tcrd7 --loglevel 20

load-HGNC.py (v4.0.0) [Mon May  4 13:46:37 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 47064 lines in file ../data/HGNC/HGNC_20200504.tsv
Progress: 100% [######################################################################] Time: 0:23:28
Processed 47064 lines - 20177 targets annotated.
No target found for 26777 lines.
  Inserted 20360 HGNC ID xrefs
  Inserted 17629 MGI ID xrefs
WARNING: 259 discrepant HGNC symbols. See logfile ./tcrd7logs/load-HGNC.py.log for details
  Added 1246 new NCBI Gene IDs
WARNING: 193 discrepant NCBI Gene IDs. See logfile ./tcrd7logs/load-HGNC.py.log for details

load-HGNC.py: Done. Elapsed time: 0:23:28.226

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-2.sql


#GIs
[smathias@juniper loaders]$ ./load-GIs.py --dbname tcrd7

load-GIs.py (v3.0.0) [Mon May  4 14:30:07 2020]:

Downloading  ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping_selected.tab.gz
         to  ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Uncompressing ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Done. Elapsed time: 0:02:02.129

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 188558 rows in file ../data/UniProt/HUMAN_9606_idmapping_selected.tab
Progress: 100% [######################################################################] Time: 0:04:17

188558 rows processed
  Inserted 257430 new GI xref rows for 20363 targets
  Skipped 168195 rows with no GI

load-GIs.py: Done. Elapsed time: 0:04:17.741

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-3.sql


#ENSGs

[smathias@juniper loaders]$ ./load-ENSGs.py --dbname tcrd7

load-ENSGs.py (v2.0.0) [Mon May  4 14:48:28 2020]:

Parsing file ../data/UniProt/uniprot-rat_20200504.xml
Processing 36152 UniProt records
Progress: 100% [#########################################################################] Time: 0:00
Parsing file ../data/UniProt/uniprot-mouse_20200504.xml
Processing 86453 UniProt records
Progress: 100% [######################################################################] Time: 0:02:29
Parsing file ../data/UniProt/uniprot-reviewed-human_20200504.xml
Processing 20365 UniProt records
Progress: 100% [######################################################################] Time: 0:00:11
Now have 99820 UniProt to ENSG mappings.

Processing 29363 lines in file ../data/Ensembl/Rattus_norvegicus.Rnor_6.0.100.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Processing 71641 lines in file ../data/Ensembl/Mus_musculus.GRCm38.100.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Processing 118135 lines in file ../data/Ensembl/Homo_sapiens.GRCh38.100.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Now have 153639 UniProt to ENSG mappings.

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 20365 TCRD targets
Progress: 100% [######################################################################] Time: 0:00:43
20365 targets processed
  Inserted 21579 new ENSG xref rows for 19406 proteins
  No ENSG found for 959 UniProt accessions. See logfile ./tcrd7logs/load-ENSGs.py.log for details.

Processing 122605 TCRD nhproteins
Progress: 100% [######################################################################] Time: 0:00:47
122605 nhproteins processed
  Inserted 57587 new ENSG xref rows for 56683 nhproteins
  No ENSG found for 65922 UniProt accessions. See logfile ./tcrd7logs/load-ENSGs.py.log for details.

load-ENSGs.py: Done. Elapsed time: 0:05:23.819

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-4.sql


# NCBI Gene
[smathias@juniper loaders]$ ./load-NCBIGene.py --dbname tcrd7 --loglevel 20

load-NCBIGene.py (v3.0.0) [Tue May  5 09:32:28 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Loading NCBI Gene annotations for 20365 TCRD targets
Progress:  53% [#####################################                                 ] ETA:  4:21:51

[smathias@juniper loaders]$ ./load-NCBIGene.py --dbname tcrd7 --loglevel 20 --pastid 11132

load-NCBIGene.py (v3.0.0) [Tue May  5 15:16:04 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)
Progress:   0% [                                                                     ] ETA:  --:--:--
Loading NCBI Gene annotations for 9233 TCRD targets
^CProgress:  38% [###########################                                           ] ETA:  2:28:Progress: 100% [######################################################################] Time: 3:48:52
Processed 9233 targets.
Skipped 194 targets with no geneid
Loaded NCBI annotations for 9038 targets
Total targets remaining for retries: 1 

Retry loop 1: Loading NCBI Gene annotations for 1 TCRD targets
Progress: 100% [######################################################################] Time: 0:00:01
Processed 1 targets.
  Annotated 1 additional targets
  Total annotated targets: 9039

Inserted 23521 aliases
Inserted 5420 NCBI Gene Summary tdl_infos
Inserted 9039 NCBI Gene PubMed Count tdl_infos
Inserted 296098 GeneRIFs
Inserted 469555 PubMed xrefs

load-NCBIGene.py: Done. Elapsed time: 3:48:53.262

mysql> select count(*) from alias where dataset_id = 8;
+----------+
| count(*) |
+----------+
|    54775 |
+----------+

mysql> select count(*) from tdl_info where itype = 'NCBI Gene Summary';
+----------+
| count(*) |
+----------+
|    12824 |
+----------+

mysql> select count(*) from tdl_info where itype = 'NCBI Gene PubMed Count';
+----------+
| count(*) |
+----------+
|    20099 |
+----------+

mysql> select count(*) from generif;
+----------+
| count(*) |
+----------+
|   729758 |
+----------+

mysql> select count(*) from xref where xtype = 'PubMed';
+----------+
| count(*) |
+----------+
|  1132378 |
+----------+

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-5.sql


# STRING IDs
[smathias@juniper loaders]$ ./load-STRINGIDs.py --dbname tcrd7

load-STRINGIDs.py (v3.0.0) [Wed May  6 09:13:36 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 19184 input lines in file ../data/JensenLab/human.uniprot_2_string.2018.tsv
Progress: 100% [######################################################################] Time: 0:00:00
19184 input lines processed.
  Skipped 1877 non-identity lines
  Got 34612 uniprot/name to STRING ID mappings

Processing 2224813 input lines in file ../data/JensenLab/9606.protein.aliases.v11.0.txt
Progress: 100% [######################################################################] Time: 0:00:07
2224813 input lines processed.
  Added 2137567 alias to STRING ID mappings
  Skipped 52633 aliases that would override UniProt mappings. See logfile ./tcrd7logs/load-STRINGIDs.py.log for details.

Loading STRING IDs for 20365 TCRD targets
Progress: 100% [######################################################################] Time: 0:10:32
Updated 19031 STRING ID values
No stringid found for 1334 proteins. See logfile ./tcrd7logs/load-STRINGIDs.py.log for details.

load-STRINGIDs.py: Done. Elapsed time: 0:10:41.194

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-6.sql


# Antibodypedia
[smathias@juniper loaders]$ ./load-Antibodypedia.py --dbname tcrd7

load-Antibodypedia.py (v3.0.0) [Wed May  6 09:33:07 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Loading Antibodypedia annotations for 20365 TCRD targets
Progress: 100% [#####################################################################] Time: 12:23:32
20365 TCRD targets processed.
  Inserted 20365 Ab Count tdl_info rows
  Inserted 20365 MAb Count tdl_info rows
  Inserted 20365 Antibodypedia.com URL tdl_info rows

load-Antibodypedia.py: Done. Elapsed time: 12:23:32.256

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-7.sql


# JensenLab PubMed Scores

[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd7

load-JensenLabPubMedScores.py (v3.0.0) [Thu May  7 15:44:20 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:03.360

Processing 389136 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [######################################################################] Time: 0:05:49
389136 input lines processed.
  Inserted 386243 new pmscore rows for 17961 targets
No target found for 254 STRING IDs. See logfile ./tcrd7logs/load-JensenLabPubMedScores.py.log for details.

Loading 17961 JensenLab PubMed Score tdl_infos
17961 processed
  Inserted 17961 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done. Elapsed time: 0:06:00.274

mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/tmp/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';
Edit that to create InsMissingJLPMSs_TCRDv7.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /tmp/nojlpms.csv > InsZeroJLPMSs_TCRDv7.sql
Edit InsZeroJLPMSs_TCRDv7.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv7.sql

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-8.sql


# IDG2 List/families
[smathias@juniper loaders]$ ./load-IDGList.py --dbname tcrd7

load-IDGList.py (v3.0.0) [Mon Jun 22 10:51:39 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 329 lines in list file ../data/IDG_Lists/IDG_List_v3.2_SLM20200508.csv
Progress: 100% [######################################################################] Time: 0:00:07
329 lines processed
329 targets updated with IDG flags
329 targets updated with fams
  118 targets updated with famexts

load-IDGList.py: Done. Elapsed time: 0:00:07.374

[smathias@juniper loaders]$ ./load-IDGFams.py --dbname tcrd7

load-IDGFams.py (v2.0.0) [Mon Jun 22 10:52:22 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 8147 lines in file ../data/IDG_Families_UNM_UMiami_v2.csv
^AProgress:  32% [######################                                                ] ETA:  0:00:Progress: 100% [######################################################################] Time: 0:00:17
8147 rows processed.
7814 IDG family designations loaded into TCRD.
5290 IDG extended family designations loaded into TCRD.
Skipped 329 IDG2 targets.
[WARNING] No target found for 3 UniProt accessions: Q5JXX5, E7EML9, Q9NPA5

load-IDGFams.py: Done. Elapsed time: 0:00:17.155

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-9.sql


# ChEMBL
[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd7 --loglevel 20

load-ChEMBL.py (v5.0.0) [Thu Jun 25 11:48:42 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done.

Connected to ChEMBL database chembl_27

Processing 11785 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
11785 input lines processed.

Processing 9218 UniProt to ChEMBL ID(s) mappings
Progress: 100% [######################################################################] Time: 0:12:20
9218 UniProt accessions processed.
  2129 targets have no qualifying TCRD activities in ChEMBL
Inserted 481656 new cmpd_activity rows
Inserted 1925 new ChEMBL First Reference Year tdl_infos

Running selective compound analysis...
  Found 19203 selective compounds
Inserted 820 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 0:14:12.848

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-10.sql


# GuideToPharmacology
[smathias@juniper loaders]$ ./load-GuideToPharmacology.py --dbname tcrd7

load-GuideToPharmacology.py (v2.0.0) [Thu Jun 25 12:32:21 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)
Downloading  http://www.guidetopharmacology.org/DATA/ligands.csv
         to  ../data/GuideToPharmacology/ligands.csv
Downloading  http://www.guidetopharmacology.org/DATA/interactions.csv
         to  ../data/GuideToPharmacology/interactions.csv

Processing 10396 lines in input file ../data/GuideToPharmacology/ligands.csv
  Got info for 7962 ligands
  Skipped 2433 antibodies/peptides

Processing 19779 lines in input file ../data/GuideToPharmacology/interactions.csv
Progress: 100% [######################################################################] Time: 0:00:22
19776 rows processed.
  Inserted 11841 new cmpd_activity rows for 1359 targets
  Skipped 0 with below cutoff activity values
  Skipped 2514 activities with multiple targets
  Skipped 3856 antibody/peptide activities
  Skipped 3965 activities with missing data
No target found for 23 uniprots/symbols. See logfile ./tcrd7logs/load-GuideToPharmacology.py.log for details.

load-GuideToPharmacology.py: Done. Elapsed time: 0:00:22.741

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-11.sql


# GO Experimental and Functional Leaf terms
[smathias@juniper loaders]$ ./load-GOExptFuncLeafTDLIs.py --dbname tcrd7

load-GOExptFuncLeafTDLIs.py (v3.0.0) [Thu Jun 25 13:02:12 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  http://www.geneontology.org/ontology/go.obo
         to  ../data/GO/go.obo
Done.

Parsing GO OBO file: ../data/GO/go.obo
load obo file ../data/GO/go.obo

Processing 20365 TCRD targets
Progress: 100% [######################################################################] Time: 0:19:49
20365 TCRD targets processed.
  Inserted 7423 new  tdl_info rows

load-GOExptFuncLeafTDLIs.py: Done. Elapsed time: 0:19:52.434

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-12.sql


# DrugCentral
[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd7

load-DrugCentral.py (v4.0.0) [Thu Jun 25 13:23:36 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 4642 input lines in file ../data/DrugCentral/drug_name_id_05122020.tsv
4642 input lines processed.
Saved 4642 keys in infos map

Processing 1973 input lines in file ../data/DrugCentral/drug_info_05122020.tsv
1973 input lines processed.
Saved 1973 keys in infos map

Processing 3361 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_05122020.tsv
3361 DrugCentral Tclin rows processed.
  Inserted 3361 new drug_activity rows

Processing 643 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_05122020.tsv
643 DrugCentral Tchem rows processed.
  Inserted 643 new drug_activity rows

Processing 11138 lines from indications file ../data/DrugCentral/drug_indications_05122020.tsv
11138 DrugCentral indication rows processed.
  Inserted 12853 new disease rows
WARNNING: 1054 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:26.943

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-13.sql


# TDLs
[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd7

load-TDLs.py (v3.0.0) [Thu Jun 25 13:32:07 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 20365 TCRD targets
Progress: 100% [######################################################################] Time: 0:02:39
20365 TCRD targets processed.
Set TDL values for 20365 targets:
  659 targets are Tclin
  1713 targets are Tchem
  11808 targets are Tbio - 600 bumped from Tdark
  6185 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:02:39.425

# Add indexes for IMPC queries fo MetapML
mysql> CREATE INDEX nhprotein_idx2  ON nhprotein(sym);
mysql> CREATE INDEX ortholog_idx2  ON ortholog(symbol);

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-14.sql


# Ontologies
[smathias@juniper loaders]$ ./load-Ontologies.py --dbname tcrd7

load-Ontologies.py (v1.0.0) [Mon Jun 29 12:48:53 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  http://purl.obolibrary.org/obo/doid.obo
         to  ../data/DiseaseOntology/doid.obo
Done.
Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 10151 Disease Ontology terms
Loading 10151 Disease Ontology terms
Progress: 100% [######################################################################] Time: 0:00:25
10151 terms processed.
  Inserted 10151 new do rows

Downloading  http://www.informatics.jax.org/downloads/reports/mp.owl
         to  ../data/MPO/mp.owl
Done.
Parsing Mammalian Phenotype Ontology file ../data/MPO/mp.owl
  Got 13153 Mammalian Phenotype Ontology terms
Loading 13153 Mammalian Phenotype Ontology terms
Progress: 100% [######################################################################] Time: 0:00:08
13153 terms processed.
  Inserted 13153 new mpo rows

Downloading  ftp://ftp.rgd.mcw.edu/pub/ontology/disease/RDO.obo
         to  ../data/RGD/RDO.obo
Done.
Parsing RGD Disease Ontology file ../data/RGD/RDO.obo
  Got 18491 RGD Disease Ontology terms
Loading 18491 RGD Disease Ontology terms
Progress: 100% [######################################################################] Time: 0:00:36
18491 terms processed.
  Inserted 18491 new rdo rows

Downloading  http://purl.obolibrary.org/obo/uberon/ext.obo
         to  ../data/Uberon/ext.obo
Done.
Parsing Uberon Ontology file ../data/Uberon/ext.obo
  Got 18149 Uberon Ontology terms
Loading 18149 Uberon terms
Progress: 100% [######################################################################] Time: 0:00:41
18149 terms processed.
  Inserted 18149 new uberon rows

load-Ontologies.py: Done. Elapsed time: 0:02:21.656

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-15.sql


# DTO
[smathias@juniper loaders]$ ./load-DTO.py --dbname tcrd7

load-DTO.py (v4.0.0) [Mon Jun 29 14:00:49 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Processing 9233 lines in file ../data/UMiami/DTO2UniProt_DTOv2.csv
Progress: 100% [######################################################################] Time: 0:00:39
9233 lines processed.
  Updated 9231 protein.dtoid values
Got 9231 UniProt to DTO mappings for TCRD targets
Got 9231 UniProt to Protein ID mappings for TCRD targets
WARNING: No target found for 1 UniProts. See logfile tcrd7logs/load-DTO.py.log for details.

Processing 9172 lines in file ../data/UMiami/Final_ProteomeClassification_Sep232019.csv
Progress: 100% [######################################################################] Time: 0:00:07
9172 lines processed.
  Updated 9170 protein.dtoclass values
WARNING: Got 1 unmapped UniProts. See logfile tcrd7logs/load-DTO.py.log for details.

Parsing Drug Target Ontology file ../data/UMiami/dto_proteome_classification_only.owl
  Got 17779 DTO terms
Loading 17779 Drug Target Ontology terms
Progress: 100% [######################################################################] Time: 0:00:11
17779 terms processed.
  Inserted 17779 new dto rows

load-DTO.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-16.sql


##
## Orthologs
##
# KMC
[smathias@juniper loaders]$ ./load-Orthologs.py --dbname tcrd7

load-Orthologs.py (v2.0.0) [Mon Jun 29 14:35:07 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/genenames/hcop/human_all_hcop_sixteen_column.txt.gz
         to  ../data/HGNC/human_all_hcop_sixteen_column.txt.gz
Uncompressing ../data/HGNC/human_all_hcop_sixteen_column.txt.gz
Done.

Processing 840819 lines in input file ../data/HGNC/human_all_hcop_sixteen_column.txt
  Generated ortholog dataframe with 191858 entries

Loading ortholog data for 20365 TCRD targets
Progress: 100% [######################################################################] Time: 0:18:30
Processed 20365 targets.
Loaded 176125 new ortholog rows
  Skipped 1126 empty ortholog entries
  Skipped 163 targets with no sym/geneid
  Skipped 13904 rows with unwanted ortholog species

load-Orthologs.py: Done. Elapsed time: 0:18:35.745

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-17.sql

# Homologene
[smathias@juniper loaders]$ ./load-HomoloGene.py --dbname tcrd7

load-HomoloGene.py (v2.0.0) [Mon Jun 29 15:06:36 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  ftp://ftp.ncbi.nih.gov/pub/HomoloGene/current/homologene.data
         to  ../data/NCBI/homologene.data
Done.

Processing 275237 input lines in file ../data/NCBI/homologene.data
Progress: 100% [######################################################################] Time: 0:57:49
Processed 275237 lines.
Loaded 69512 new homologene rows
  Skipped 214285 non-Human/Mouse/Rat lines
WARNNING: No target/nhprotein found for 5896 lines. See logfile tcrd7logs/load-HomoloGene.py.log for details.

load-HomoloGene.py: Done. Elapsed time: 0:57:49.358

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-18.sql


# PubTator
[smathias@juniper loaders]$ ./load-PubTatorScores.py --dbname tcrd7

load-PubTatorScores.py (v3.0.0) [Tue Jun 30 10:48:36 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Downloading  http://download.jensenlab.org/KMC/Medline/pubtator_counts.tsv
         to  ../data/JensenLab/pubtator_counts.tsv
Done. Elapsed time: 0:00:04.253

Processing 1238979 lines in file ../data/JensenLab/pubtator_counts.tsv
Progress: 100% [######################################################################] Time: 0:25:10
1238979 lines processed.
  Inserted 456357 new ptscore rows for 18367 targets.
No target found for 171003 NCBI Gene IDs. See logfile ./tcrd7logs/load-PubTatorScores.py.log for details.

Loading 18367 PubTator Score tdl_infos
18367 processed
Inserted 18367 new PubTator PubMed Score tdl_info rows

load-PubTatorScores.py (v3.0.0) [Tue Jun 30 11:14:07 2020]:

load-PubTatorScores.py: Done. Elapsed time: 0:25:25.809

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-19.sql


##
## Diseases
##
- Generate input file for Expression Atlas
[smathias@juniper ~]$ cd TCRD/data/ExpressionAtlas
[smathias@juniper ExpressionAtlas]$  wget ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz
[smathias@juniper ExpressionAtlas]$ tar xf atlas-latest-data.tar.gz
[smathias@juniper ExpressionAtlas]$ ./process.R
- Add new JensenLab Knowledge channel disease_type:
mysql> insert into disease_type (name, description) values ('JensenLab Knowledge AmyCo', 'JensenLab Knowledge channel using AmyCo');
- Manually download and uncompress CTD file http://ctdbase.org/reports/CTD_genes_diseases.tsv.gz (there's a Captcha, so programmatic download does not work).

[smathias@juniper loaders]$ ./load-Diseases.py --dbname tcrd7 --loglevel 20

load-Diseases.py (v1.0.0) [Mon Jul 27 11:48:28 2020]:

Connected to TCRD database tcrd7 (schema ver 7.0.0; data ver 0.0.0)

Working on JensenLab DISEASES...
Downloading  http://download.jensenlab.org/human_disease_knowledge_filtered.tsv
         to  ../data/JensenLab/human_disease_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_experiments_filtered.tsv
         to  ../data/JensenLab/human_disease_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_textmining_filtered.tsv
         to  ../data/JensenLab/human_disease_textmining_filtered.tsv
Processing 7344 lines in DISEASES Knowledge file ../data/JensenLab/human_disease_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:01:34
7344 lines processed.
Inserted 7101 new disease rows for 3651 proteins
  No target found for 30 stringids/symbols. See logfile ./tcrd7logs/load-Diseases.py.log for details.
WARNING: 260 DB errors occurred. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Processing 23462 lines in DISEASES Experiment file ../data/JensenLab/human_disease_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 0:05:04
23462 lines processed.
Inserted 23510 new disease rows for 12238 proteins
  No target found for 57 stringids/symbols. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Processing 175423 lines in DISEASES Text Mining file ../data/JensenLab/human_disease_textmining_filtered.tsv
Progress: 100% [######################################################################] Time: 0:37:04
175423 lines processed.
Inserted 166215 new disease rows for 16136 proteins
  No target found for 2922 stringids/symbols. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Done with DISEASES. Elapsed time: 0:43:43.430

Working on DisGeNET...
Downloading http://www.disgenet.org/static/disgenet_ap1/files/downloads/curated_gene_disease_associations.tsv.gz
         to ../data/DisGeNET/curated_gene_disease_associations.tsv.gz
Uncompressing ../data/DisGeNET/curated_gene_disease_associations.tsv.gz
Processing 84039 lines in DisGeNET file ../data/DisGeNET/curated_gene_disease_associations.tsv
Progress: 100% [######################################################################] Time: 0:03:04
84039 lines processed.
Loaded 81811 new disease rows for 9202 proteins.
  No target found for 527 symbols/geneids. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Done with DisGeNET. Elapsed time: 0:03:04.735

Working on Monarch...
Loading Monarch disease associations for 20365 TCRD targets
Progress: 100% [######################################################################] Time: 1:52:14
20365 targets processed.
Loaded 5562 new disease rows for 3234 proteins.
  Skipped 265 targets with no geneid or no associations.
Done with Monarch. Elapsed time: 1:52:14.811

Working on Expression Atlas...
Processing 132861 lines in Expression Atlas file ../data/ExpressionAtlas/disease_assoc_human_do_uniq.tsv
Progress: 100% [######################################################################] Time: 0:12:03
132860 lines processed.
Loaded 122878 new disease rows for 16202 proteins.
  No target found for 4573 symbols/ensgs. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Done with Expression Atlas. Elapsed time: 0:12:03.769

Working on CTD...
Processing 78970255 lines in CTD file ../data/CTD/CTD_genes_diseases.tsv
Progress: 100% [######################################################################] Time: 0:04:51
78970255 lines processed.
Loaded 34930 new disease rows for 7836 proteins.
  Skipped 78938041 with no direct evidence.
  No target found for 834 symbols/geneids. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Done with CTD. Elapsed time: 0:05:03.434

Working on eRAM...
Processing 15942 disease names in CTD shelf file ../data/eRAM/eRAM.db
Progress: 100% [######################################################################] Time: 0:02:30
15942 lines processed.
Loaded 13821 new disease rows for 5619 proteins
  Skipped 332 diseases with no currated genes. See logfile ./tcrd7logs/load-Diseases.py.log for details.
  55 disease names cannot be decoded to strs. See logfile ./tcrd7logs/load-Diseases.py.log for details.
  No target found for 372 stringids/symbols. See logfile ./tcrd7logs/load-Diseases.py.log for details.
Done with eRAM. Elapsed time: 0:02:30.343

load-Diseases.py: Done.

mysql> ALTER TABLE disease DROP COLUMN O2S;
mysql> ALTER TABLE disease DROP COLUMN S2O;
mysql> DROP TABLE ortholog_disease;
mysql> UPDATE dbinfo SET schema_ver = '7.1.0';

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-20.sql


##
## Phenotypes
##
- Manually download GWAS Catalog file from https://www.ebi.ac.uk/gwas/api/search/downloads/
- Download files from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-11.0/csv/:
[smathias@juniper IMPC]$ wget ftp://ftp.ebi.ac.uk/pub/databases/impc/release-11.0/csv/IMPC_genotype_phenotype.csv.gz
[smathias@juniper IMPC]$ wget ftp://ftp.ebi.ac.uk/pub/databases/impc/release-11.0/csv/IMPC_ALL_statistical_results.csv.gz
- Produce input files for RGD:
[smathias@juniper RGD]$ ../R/process-RGD.R

[smathias@juniper loaders]$ ./load-Phenotypes.py --dbname tcrd7

load-Phenotypes.py (v1.0.0) [Wed Jul 29 11:03:56 2020]:

Connected to TCRD database tcrd7 (schema ver 7.1.0; data ver 0.0.0)

Working on OMIM...
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/genemap2.txt
         to  ../data/OMIM/genemap2.txt
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/mimTitles.txt
         to  ../data/OMIM/mimTitles.txt
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/phenotypicSeries.txt
         to  ../data/OMIM/phenotypicSeries.txt
Done.
Processing 26835 lines from input file ../data/OMIM/mimTitles.txt
Progress: 100% [######################################################################] Time: 0:00:25
26835 lines processed
Loaded 26819 new omim rows
  Skipped 16 commented lines.
Processing 4745 lines from input file ../data/OMIM/phenotypicSeries.txt
Progress: 100% [######################################################################] Time: 0:00:04
4745 lines processed
Loaded 4742 new omim_ps rows
  Skipped 3 commented lines.
Processing 17233 lines from input file ../data/OMIM/genemap2.txt
Progress: 100% [######################################################################] Time: 0:02:41
17233 lines processed
Loaded 15128 OMIM phenotypes for 15101 proteins
  Skipped 68 commented lines.
  Skipped 108 provisional phenotype rows.
  No target found for 1972 good lines. See logfile ./tcrd7logs/load-Phenotypes.py.log for details.
Done with OMIM. Elapsed time: 0:03:10.922

Working on GWAS Catalog...
Processing 189812 lines GWAS Catalog file ../data/EBI/gwas_catalog_v1.0.2-associations_e100_r2020-07-14.tsv
Progress: 100% [######################################################################] Time: 0:31:58
189812 lines processed.
Inserted 181389 new gwas rows for 14271 proteins
  No target found for 15063 symbols. See logfile ./tcrd7logs/load-Phenotypes.py.log for details.
WARNING: 1 DB errors occurred. See logfile ./tcrd7logs/load-Phenotypes.py.log for details.
Done with GWAS Catalog. Elapsed time: 0:31:58.832

Working on IMPC...
Processing 28115 lines from input file ../data/IMPC/IMPC_genotype_phenotype.csv
Progress: 100% [######################################################################] Time: 0:01:55
28115 lines processed.
Loaded 124588 IMPC phenotypes for 16989 nhproteins
No nhprotein found for 78 gene symbols. See logfile ./tcrd7logs/load-Phenotypes.py.log for details.
Skipped 403 lines with no term_id or term_name.
Processing 1867835 lines from input file ../data/IMPC/IMPC_ALL_statistical_results.csv
Progress: 100% [######################################################################] Time: 1:46:23
1867835 lines processed.
Loaded 7285906 IMPC phenotypes for 28205 nhproteins
  No nhprotein found for 103 gene symbols. See logfile ./tcrd7logs/load-Phenotypes.py.log for details.
  Skipped 84665 lines with no term_id/term_name or no p-value.
Done with IMPC. Elapsed time: 1:48:19.832

Working on JAX...

Downloading  http://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt
         to  ../data/JAX/HMD_HumanPhenotype.rpt
Done.
Parsing Mammalian Phenotype Ontology file ../data/MPO/mp.owl
Got 13542 MP terms
Processing 18775 lines from JAX file ../data/JAX/HMD_HumanPhenotype.rpt
Progress: 100% [######################################################################] Time: 0:02:45
18775 lines processed.
Loaded 62676 new phenotype rows for 10878 proteins
  Skipped 7719 lines with no MP terms
  No target found for 140 gene symbols/ids. See logfile ./tcrd7logs/load-Phenotypes.py.log for details.
Done with JAX. Elapsed time: 0:02:55.731

Working on RGD...
Processing 2019 lines in processed RGD file ../data/RGD/rat_qtls.tsv
Progress: 100% [######################################################################] Time: 0:00:02
Processed 2019 lines
Inserted 2018 new rat_qtl rows for 1009 nhproteins.
Processing 87289 lines in processed RGD file ../data/RGD/rat_terms.tsv
Progress: 100% [######################################################################] Time: 0:01:23
Processed 87289 lines
Inserted 87288 new rat_term rows.
Done with RGD. Elapsed time: 0:01:25.395

load-Phenotypes.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd7 > dumps7/tcrd7-21.sql


##
## Expression
##
# JensenLab TISSUES
# GTEx
# HPA
# HPM
# HCA
# Cell Surface Protein Atlas
# CCLE
# Consensus
# Uberon IDs (for UniProt Tissue etype)


# JensenLab COMPARTMETS



##
## Pathways
##
# KEGG
# PathwayCommons
# Reactome
# WikiPathways



##
## PPIs
##
# BioPlex
# Reactome
# STRINGDB


# TIN-X

# EBI Patent Counts

# KEGG Distances

# KEGG Nearest Tclins

# LINCS L1000 Xrefs

# LocSigDB

# PANTHER protein classes

# PubChem CIDs

# Transcription Factor Flags

# TMHMM Predictions

# PubMed

# GeneRIF Years

# DRGC Resources

# Harmonizome & Harmonogram CDFs

# LINCS

# HGram CDFs (forgot to do this)

# IMPC Mouse Clones

