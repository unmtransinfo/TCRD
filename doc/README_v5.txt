Create empty schema with types
------------------------------
[smathias@juniper SQL]$ mysqldump --no-data tcrd4 | sed 's/ AUTO_INCREMENT=[0-9]*\b//g' > create-TCRD.sql
[smathias@juniper SQL]$ mysqldump --no-create-db --no-create-info tcrd4 compartment_type data_type disease_type expression_type info_type pathway_type phenotype_type ppi_type xref_type > types_v5.sql
mysql> create database tcrd5;
mysql> use tcrd5
mysql> \. create-TCRD.sql
mysql> \. types_v5.sql
Check that everything is good:
mysql> SHOW TABLE STATUS FROM `tcrd5`;
mysql> INSERT INTO dbinfo (dbname, schema_ver, data_ver, owner) VALUES ('tcrd5', '5.0.0', '5.0.0', 'smathias');
[smathias@juniper SQL]$ mysqldump tcrd5 > create-TCRDv5.sql
[smathias@juniper SQL]$ rm create-TCRD.sql types_v5.sql

This rest of this README includes all commands (and most output) run to build TCRD v5.

[smathias@juniper loaders]$ ./load-UniProt.py --dbname tcrd5 --loglevel 20

load-UniProt.py (v2.1.0) [Thu Jan 18 11:03:49 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 20244 records in UniProt file ../data/UniProt/uniprot-human-reviewed_20180118.tab

Loading data for 20244 proteins
Progress: 100% [#############################################################] Time: 1 day, 7:46:32
Processed 20244 UniProt records.
  Total loaded targets/proteins: 20243
  Total targets/proteins remaining for retries: 1 

Retry loop 1: Trying to load data for 1 proteins
Progress: 100% [####################################################################] Time: 0:00:06
Processed 1 UniProt records.
  Loaded 1 new targets/proteins
  Total loaded targets/proteins: 20244

load-UniProt.py: Done. Elapsed time: 31:46:38.685

Fix the GPR89s:
GPR89A/B each have two Gene IDs in UniProt. According to NCBI, GPR89B is 51463. Fix this manually:
mysql> UPDATE protein SET geneid = 51463 WHERE sym = 'GPR89B';

Fix the Medium-wave-sensitive opsins:
mysql> select id, name, description, sym, uniprot, geneid from protein where name like 'OPSG%';
+-------+-------------+-------------------------------+---------+---------+--------+
| id    | name        | description                   | sym     | uniprot | geneid |
+-------+-------------+-------------------------------+---------+---------+--------+
| 12007 | OPSG_HUMAN  | Medium-wave-sensitive opsin 1 | OPN1MW2 | P04001  | 728458 |
| 12190 | OPSG2_HUMAN | Medium-wave-sensitive opsin 2 | OPN1MW2 | P0DN77  | 728458 |
| 12191 | OPSG3_HUMAN | Medium-wave-sensitive opsin 3 | OPN1MW2 | P0DN78  | 728458 |
+-------+-------------+-------------------------------+---------+---------+--------+
mysql> select id, name, idg2, fam, famext from target where id in (12007, 12190, 12191);
+-------+-------------------------------+------+------+--------+
| id    | name                          | idg2 | fam  | famext |
+-------+-------------------------------+------+------+--------+
| 12007 | Medium-wave-sensitive opsin 1 |    0 | GPCR | GPCR   |
| 12190 | Medium-wave-sensitive opsin 2 |    1 | NULL | NULL   |
| 12191 | Medium-wave-sensitive opsin 3 |    0 | NULL | NULL   |
+-------+-------------------------------+------+------+--------+

UPDATE protein SET geneid = 2652, sym = 'OPN1MW' WHERE id = 12007;
UPDATE protein set geneid = 101060233, sym = 'OPN1MW3' WHERE id = 12191;
UPDATE target set fam = 'GPCR', famext = 'GPCR' WHERE id = 12007; // NB: This was WRONG!!! 
UPDATE target set fam = 'GPCR', famext = 'GPCR' WHERE id = 12191;

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-1.sql


[smathias@juniper loaders]$ ./load-IDG2Flags.py --dbname tcrd5

load-IDG2Flags.py (v2.1.0) [Tue Jan 23 11:13:20 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Loading IDG Phase 2 flags for 394 gene symbols
Progress: 100% [####################################################################] Time: 0:00:02
394 symbols processed
394 targets updated with IDG2 flags

load-IDG2Flags.py: Done. Elapsed time: 0:00:02.813

[smathias@juniper loaders]$ ./load-IDGFams.py --dbname tcrd5

load-IDGFams.py (v1.1.0) [Tue Jan 23 11:13:50 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 8150 lines in inut file ../data/IDG_Families_UNM_UMiami_v1.csv
Progress: 100% [####################################################################] Time: 0:00:24
8149 rows processed.
8149 IDG family designations loaded into TCRD.
5622 IDG extended family designations loaded into TCRD.

load-IDGFams.py: Done. Elapsed time: 0:00:24.217

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-2.sql


[smathias@juniper loaders]$ ./load-GIs.py --dbname tcrd5

load-GIs.py (v2.1.0) [Tue Jan 23 11:14:39 2018]:

Downloading  ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping_selected.tab.gz
         to  ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Uncompressing ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Done. Elapsed time: 0:02:40.960

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 161521 rows in file ../data/UniProt/HUMAN_9606_idmapping_selected.tab
Progress: 100% [####################################################################] Time: 0:03:57

161521 rows processed
20243 targets annotated with GI xref(s)
  Skipped 141278 rows
  Inserted 257313 new GI xref rows

load-GIs.py: Done. Elapsed time: 0:03:58.050

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-3.sql


[smathias@juniper loaders]$ ./load-HGNC.py --dbname tcrd5

load-HGNC.py (v2.1.0) [Tue Jan 23 11:26:39 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Loading HGNC annotations for 20244 TCRD targets
Progress: 100% [#############################################################] Time: 1 day, 6:22:17
Processed 20244 targets.
Loaded HGNC annotations for 20021 targets
Total targets remaining for retries: 4 

Retry loop 1: Loading HGNC annotations for 4 TCRD targets
Progress: 100% [####################################################################] Time: 0:00:23
Processed 4 targets.
  Annotated 4 additional targets
  Total annotated targets: 20025

Updated/Inserted 20025 HGNC ID xrefs
Inserted 4 new protein.sym values
Updated 221 discrepant protein.sym values
Updated/Inserted 20025 protein.chr values
Updated/Inserted 1106 protein.geneid values
Updated/Inserted 17508 MGI ID xrefs
WARNNING: 219 targets did not find an HGNC record.

load-HGNC.py: Done. Elapsed time: 30:22:41.683

Add provenance rows for xref:
INSERT INTO provenance (dataset_id, table_name, where_clause) VALUES (1, 'xref', 'dataset_id = 1');
INSERT INTO provenance (dataset_id, table_name, where_clause) VALUES (1, 'alias', 'dataset_id = 1');
INSERT INTO provenance (dataset_id, table_name, where_clause) VALUES (4, 'xref', 'dataset_id = 4');
INSERT INTO provenance (dataset_id, table_name, where_clause) VALUES (5, 'xref', 'dataset_id = 5');

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-4.sql


[smathias@juniper loaders]$ ./load-NCBIGene.py --dbname tcrd5 --loglevel 20

load-NCBIGene.py (v2.1.1) [Mon Jan 29 11:57:24 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Loading NCBI Gene annotations for 20244 TCRD targets
Progress: 100% [########################################################] Time: 1 day, 5:38:37
Processed 20244 targets.
Skipped 199 targets with no geneid
Loaded NCBI annotations for 20036 targets
Total targets remaining for retries: 9 

Retry loop 1: Loading NCBI Gene annotations for 9 TCRD targets
Progress: 100% [###############################################################] Time: 0:00:12
Processed 9 targets.
  Annotated 9 additional targets
  Total annotated targets: 20045

Inserted 52522 aliases
Inserted 12840 NCBI Gene Summary tdl_infos
Inserted 20045 NCBI Gene PubMed Count tdl_infos
Inserted 687109 GeneRIFs
Inserted 1135146 PubMed xrefs
Inserted 70159 other xrefs

load-NCBIGene.py: Done. Elapsed time: 29:38:50.765

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-5.sql


[smathias@juniper loaders]$ ./load-STRINGIDs.py --dbname tcrd5 --loglevel 20

load-STRINGIDs.py (v2.4.0) [Wed Jan 31 10:22:14 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 20499 input lines in file ../data/JensenLab/9606_reviewed_uniprot_2_string.04_2015.tsv
Progress: 100% [###############################################################] Time: 0:00:00
20499 input lines processed.
  Skipped 2397 non-identity lines
  Got 35046 uniprot/name to STRING ID mappings

Processing 2449433 input lines in file ../data/JensenLab/9606.protein.aliases.v10.txt
Progress: 100% [###############################################################] Time: 0:00:16
2449433 input lines processed.
  Got 2166722 alias to STRING ID mappings
  Skipped 248752 aliases that would override reviewed mappings . See logfile tcrd5logs/load-STRINGIDs.py.log for details.

Loading STRING IDs for 20244 TCRD targets
Progress: 100% [###############################################################] Time: 0:33:57
Updated 19277 STRING ID values

load-STRINGIDs.py: Done. Elapsed time: 0:34:15.093

update protein set stringid = 'ENSP00000366005' where sym = 'HLA-A';

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-6.sql


[smathias@juniper loaders]$ ./load-Antibodypedia.py --dbname tcrd5

load-Antibodypedia.py (v2.1.0) [Wed Jan 31 12:02:34 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Loading Antibodypedia annotations for 20244 TCRD targets
Progress: 100% [######################################################] Time: 2 days, 11:10:43
20244 TCRD targets processed.
  Inserted 20244 Ab Count tdl_info rows
  Inserted 20244 MAb Count tdl_info rows
  Inserted 20244 Antibodypedia.com URL tdl_info rows

load-Antibodypedia.py: Done. Elapsed time: 2 days, 11:10:43

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-7.sql


[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd5

load-JensenLabPubMedScores.py (v2.1.0) [Mon Feb  5 10:58:24 2018]:

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:08.424

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 371227 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [###############################################################] Time: 0:04:49
371227 input lines processed.
  17775 targets have JensenLab PubMed Scores
  Inserted 358196 new pmscore rows
No target found for 367 STRING IDs. Saved to file: ./tcrd5logs/load-JensenLabPubMedScores.py.db

Loading 17775 JensenLab PubMed Score tdl_infos
17775 processed
  Inserted 17775 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done. Elapsed time: 0:05:00.345

[smathias@juniper SQL]$ mysql tcrd5
mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/tmp/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';
Edit that to create InsMissingJLPMSs_TCRDv4.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /tmp/nojlpms.csv > InsZeroJLPMSs_TCRDv5.sql
Edit InsZeroJLPMSs_TCRDv5.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv5.sql

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-8.sql


# Drug Central
# Edit tclin file. Change:
P62158  CALM_HUMAN      aprindine       4.7447  ID50    INHIBITOR       SCIENTIFIC LITERATURE   http://www.ncbi.nlm.nih.gov/pubmed/6186851        CCN(CC)CCCN(C1CC2=C(C1)C=CC=C2)C1=CC=CC=C1      CHEMBL1213033
# to:
P0DP23  CALM1_HUMAN      aprindine       4.7447  ID50    INHIBITOR       SCIENTIFIC LITERATURE   http://www.ncbi.nlm.nih.gov/pubmed/6186851        CCN(CC)CCCN(C1CC2=C(C1)C=CC=C2)C1=CC=CC=C1      CHEMBL1213033

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd5

load-DrugCentral.py (v2.1.0) [Mon Feb  5 11:29:46 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 1830 input lines in file ../data/DrugCentral/drug_info_08302017.tsv
1830 input lines processed.
Saved 1830 keys in infos map

Processing 3185 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_08302017.tsv
/home/app/TCRD/loaders/TCRD.py:653: Warning: Data truncated for column 'act_value' at row 1
  curs.execute(sql, tuple(params))
3185 DrugCentral Tclin rows processed.
  Inserted 3185 new drug_activity rows

Processing 642 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_08302017.tsv
642 DrugCentral Tchem rows processed.
  Inserted 642 new drug_activity rows

Processing 10917 lines from indications file ../data/DrugCentral/drug_indications_08302017.tsv
10917 DrugCentral indication rows processed.
  Inserted 12677 new target2disease rows
WARNNING: 1005 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:17.038

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-9.sql


[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd5

load-ChEMBL.py (v2.2.0) [Mon Feb  5 11:43:40 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done. Elapsed time: 0:00:02.369

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 9494 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
9494 input lines processed.

Processing 7754 UniProt to ChEMBL ID(s) mappings
Progress: 100% [###############################################################] Time: 0:22:00
7754 UniProt accessions processed.
  0 targets not found in ChEMBL
  936 targets have no good activities in ChEMBL
Inserted 362276 new chembl_activity rows
Inserted 2373 new ChEMBL First Reference Year tdl_infos
WARNING: 5 database errors occured. See logfile ./tcrd5logs/load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 16640 selective compounds
Inserted 775 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 0:22:44.632

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-10.sql


[smathias@juniper loaders]$ ./load-GOExptFuncLeafTDLIs.py --dbname tcrd5

load-GOExptFuncLeafTDLIs.py (v2.1.0) [Mon Feb  5 12:28:30 2018]:

Downloading  http://www.geneontology.org/ontology/go.obo
         to  ../data/GO/go.obo
Done.
load obo file ../data/GO/go.obo
Progress: 100% [###############################################################] Time: 0:34:20
20244 TCRD targets processed.
  Inserted 6731 new  tdl_info rows

load-GOExptFuncLeafTDLIs.py: Done. Elapsed time: 0:34:24.301

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-11.sql


[smathias@juniper loaders]$ ./load-OMIM.py --dbname tcrd5

load-OMIM.py (v2.1.0) [Tue Feb  6 11:06:21 2018]:

Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/genemap.txt
         to  ../data/OMIM/genemap.txt
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

[smathias@juniper loaders]$ ./load-OMIM.py --dbname tcrd5

load-OMIM.py (v2.1.0) [Tue Feb  6 11:11:57 2018]:

Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/genemap.txt
         to  ../data/OMIM/genemap.txt
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 16723 lines from input file ../data/OMIM/genemap.txt
Progress: 100% [###############################################################] Time: 0:03:23
16724 lines processed
  Skipped 12866 lines (commented lines and lines with unconfirmed status).
Loaded 3765 OMIM phenotypes for 3731 targets
No target found for 6147 symbols. See logfile ./tcrd5logs/load-OMIM.py.log for details.

load-OMIM.py: Done. Elapsed time: 0:03:23.133

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-12.sql


[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd5

load-TDLs.py (v2.1.0) [Tue Feb  6 15:14:01 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.0; data ver 5.0.0)

Processing 20244 TCRD targets
Progress: 100% [###############################################################] Time: 0:34:11
20244 TCRD targets processed.
Set TDL values for 20244 targets:
  606 targets are Tclin
  1887 targets are Tchem
  11182 targets are Tbio - 857 bumped from Tdark
  6569 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:34:11.934

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-12.sql


##
## Phenotypes
##
ALTER TABLE phenotype ADD COLUMN sex varchar(8) NULL;
ALTER TABLE phenotype CHANGE snps snps text NULL;
UPDATE dbinfo SET schema_ver = '5.0.1';

# OMIM (already done above for TDL assignments)

# GWAS Catalog
[smathias@juniper loaders]$ ./load-GWASCatalogPhenotypes.py --dbname tcrd5

load-GWASCatalogPhenotypes.py (v2.1.0) [Wed Mar 21 14:15:29 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 67230 lines from input file ../data/EBI/gwas_catalog_v1.0.1-associations_e91_r2018-03-13.tsv
Progress: 100% [######################################################################] Time: 0:07:38
67230 lines processed.
Loaded 54652 GWAS phenotypes for 10255 targets
No target found for 10500 symbols. See logfile ./tcrd5logs/load-GWASCatalogPhenotypes.py.log for details.

load-GWASCatalogPhenotypes.py: Done. Elapsed time: 0:07:38.621

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-13.sql

# IMPC
[smathias@juniper loaders]$ ./load-IMPC-Phenotypes.py --dbname tcrd5

load-IMPC-Phenotypes.py (v2.3.0) [Wed Mar 21 14:57:35 2018]:

Downloading ftp://ftp.ebi.ac.uk/pub/databases/impc/release-6.1/csv/ALL_genotype_phenotype.csv.gz
         to ../data/IMPC/ALL_genotype_phenotype.csv.gz
Uncompressing ../data/IMPC/ALL_genotype_phenotype.csv.gz

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 37719 lines from input file ../data/IMPC/ALL_genotype_phenotype.csv
Progress: 100% [########################################################################] Time: 0:04:23
37718 lines processed.
Loaded 35525 IMPC phenotypes for 3485 targets
  Inserted 35525 new MGI ID xref rows
No target found for 301 gene symbols. See logfile ./tcrd5logs/load-IMPC-Phenotypes.py.log for details.
301 lines have no term_id or term_name. See logfile ./tcrd5logs/load-IMPC-Phenotypes.py.log for details.

load-IMPC-Phenotypes.py: Done. Elapsed time: 0:04:25.922

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-14.sql

# JAX/MGI Human Ortholog Phenotype
[smathias@juniper loaders]$ ./load-JAXPhenotypes.py --dbname tcrd5

load-JAXPhenotypes.py (v2.2.0) [Wed Mar 21 15:13:26 2018]:

Downloading http://www.informatics.jax.org/downloads/reports/VOC_MammalianPhenotype.rpt
         to ../data/JAX/VOC_MammalianPhenotype.rpt

Downloading http://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt
         to ../data/JAX/HMD_HumanPhenotype.rpt

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 12613 lines in MPO file ../data/JAX/VOC_MammalianPhenotype.rpt
  Saved 12612 MPO entries

Processing 18521 lines from input file ../data/JAX/HMD_HumanPhenotype.rpt
Progress: 100% [######################################################################] Time: 0:01:33
18521 lines processed.
Loaded 60458 new phenotype rows for 9720 targets
  Loaded/Skipped 9792 new MGI xrefs
No target found for 91 gene symbols/ids. See logfile ./tcrd5logs/load-JAXPhenotypes.py.log for details.

load-JAXPhenotypes.py: Done. Elapsed time: 0:01:45.723

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-15.sql


##
## Diseases
##
# JensenLab DISEASES
[smathias@juniper loaders]$ ./load-JensenLab-DISEASES.py --dbname tcrd5

load-JensenLab-DISEASES.py (v2.1.0) [Wed Mar 21 15:34:21 2018]:

Downloading  http://download.jensenlab.org/human_disease_knowledge_filtered.tsv
         to  ../data/JensenLab/human_disease_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_experiments_filtered.tsv
         to  ../data/JensenLab/human_disease_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_textmining_filtered.tsv
         to  ../data/JensenLab/human_disease_textmining_filtered.tsv

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 5931 lines in file ../data/JensenLab/human_disease_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:01:02
5931 lines processed.
Inserted 6287 new disease rows for 3215 targets
No target found for 25 stringids/symbols. See logfile ./tcrd5logs/load-JensenLab-DISEASES.py.log for details.

Processing 23987 lines in file ../data/JensenLab/human_disease_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 0:04:14
23987 lines processed.
Inserted 23715 new disease rows for 12468 targets
No target found for 221 stringids/symbols. See logfile ./tcrd5logs/load-JensenLab-DISEASES.py.log for details.

Processing 49156 lines in file ../data/JensenLab/human_disease_textmining_filtered.tsv
Progress: 100% [######################################################################] Time: 0:08:42
49156 lines processed.
Inserted 48893 new disease rows for 12503 targets
No target found for 1077 stringids/symbols. See logfile ./tcrd5logs/load-JensenLab-DISEASES.py.log for details.

load-JensenLab-DISEASES.py: Done. Elapsed time: 0:13:59.503

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-16.sql

# DisGeNET
[smathias@juniper loaders]$ ./load-DisGeNET.py --dbname tcrd5

load-DisGeNET.py (v2.1.0) [Thu Mar 22 10:57:22 2018]:

Downloading http://www.disgenet.org/ds/DisGeNET/results/curated_gene_disease_associations.tsv.gz
         to ../data/DisGeNET/curated_gene_disease_associations.tsv.gz
Uncompressing ../data/DisGeNET/curated_gene_disease_associations.tsv.gz

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 130822 lines in file ../data/DisGeNET/curated_gene_disease_associations.tsv
Progress: 100% [######################################################################] Time: 0:02:43
130822 lines processed.
Loaded 127453 new disease rows for 7631 targets.
No target found for 1316 symbols/geneids. See logfile ./tcrd5logs/load-DisGeNET.py.log for details.

load-DisGeNET.py: Done. Elapsed time: 0:02:51.249

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-17.sql

# Monarch
[smathias@juniper loaders]$ load-MonarchDiseases.py --dbname tcrd5

load-MonarchDiseases.py (v1.1.0) [Thu Mar 22 11:48:29 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Connecting to UMiami Monarch database.
  Got 9285 gene-disease records from Monarch database.

Loading 9285 Monarch diseases
Progress: 100% [######################################################################] Time: 0:01:11
9285 records processed.
Loaded 9509 new disease rows for 3826 targets
No target found for 246 symbols/geneids. See logfile ./tcrd5logs/load-MonarchDiseases.py.log for details.

load-MonarchDiseases.py: Done. Elapsed time: 0:01:12.329

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-18.sql

# Expression Atlas
[smathias@juniper loaders]$ ./load-ExpressionAtlas.py --dbname tcrd5

load-ExpressionAtlas.py (v2.1.0) [Thu Mar 22 14:53:37 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 171747 lines in file ../data/ExpressionAtlas/disease_assoc_human_do_uniq.tsv
Progress: 100% [######################################################################] Time: 0:14:04
171746 lines processed.
Loaded 158709 new disease rows for 16585 targets.
No target found for 5894 symbols/ensgs. See logfile load-ExpressionAtlas.py.log for details.

load-ExpressionAtlas.py: Done. Elapsed time: 0:14:04.506

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-19.sql

# CTD
INSERT INTO disease_type (name, description) VALUES ('CTD', 'Gene-Disease associations with direct evidence from the Comparative Toxicogenomics Database.');
[smathias@juniper loaders]$ ./load-CTD-Diseases.py --dbname tcrd5

load-CTD-Diseases.py (v1.0.0) [Thu Mar 22 16:30:06 2018]:

Downloading http://ctdbase.org/reports/CTD_genes_diseases.tsv.gz
         to ../data/CTD/CTD_genes_diseases.tsv.gz
Uncompressing ../data/CTD/CTD_genes_diseases.tsv.gz

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 61128497 lines in file ../data/CTD/CTD_genes_diseases.tsv
Progress: 100% [######################################################################] Time: 0:03:50
61128497 lines processed.
Loaded 27924 new disease rows for 7446 targets.
Skipped 61098823 with no direct evidence.
No target found for 778 symbols/geneids. See logfile ./tcrd5logs/load-CTD-Diseases.py.log for details.

load-CTD-Diseases.py: Done. Elapsed time: 0:03:58.363

# Fix for manual update error of UniProt load:
UPDATE target set fam = 'GPCR', famext = 'GPCR' WHERE id = 12190;

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-20.sql

##
## Pathways
##
# KEGG
[smathias@juniper loaders]$ ./load-KEGGPathways.py --dbname tcrd5

load-KEGGPathways.py (v2.1.0) [Wed Mar 28 16:07:40 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Mapping KEGG pathways to gene lists
Processing 327 KEGG Pathways
Progress: 100% [######################################################################] Time: 0:28:48
Processed 327 KEGG Pathways.
  Inserted 30346 pathway rows
WARNNING: 314 (of 7386) KEGG IDs did not find a TCRD target.

load-KEGGPathways.py: Done. Elapsed time: 0:28:56.492

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-21.sql

# PathwayCommons
[smathias@juniper loaders]$ ./load-PathwayCommons.py --dbname tcrd5

load-PathwayCommons.py (v2.1.0) [Wed Mar 28 16:58:24 2018]:
Downloading  http://www.pathwaycommons.org/archives/PC2/v9/PathwayCommons9.All.uniprot.gmt.gz
         to  ../data/PathwayCommons/PathwayCommons9.All.uniprot.gmt.gz
Uncompressing ../data/PathwayCommons/PathwayCommons9.All.uniprot.gmt.gz

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 3660 input lines from PathwayCommons file ../data/PathwayCommons/PathwayCommons9.All.uniprot.gmt
Progress: 100% [######################################################################] Time: 0:01:39
Processed 3660 Reactome Pathways.
  Inserted 38225 pathway rows
  Skipped 1720 rows from 'kegg', 'wikipathways', 'reactome'
WARNNING: 29 (of 5278) UniProt accession(s) did not find a TCRD target.

load-PathwayCommons.py: Done. Elapsed time: 0:01:44.753

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-22.sql

# Reactome
[smathias@juniper loaders]$ ./load-ReactomePathways.py --dbname tcrd5

load-ReactomePathways.py (v2.1.0) [Wed Mar 28 17:01:15 2018]:
Downloading  http://www.reactome.org/download/current/ReactomePathways.gmt.zip
         to  ../data/Reactome/ReactomePathways.gmt.zip
Unzipping ../data/Reactome/ReactomePathways.gmt.zip

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 2022 input line from Reactome Pathways file ../data/Reactome/ReactomePathways.gmt
Progress: 100% [######################################################################] Time: 0:12:22
Processed 2022 Reactome Pathways.
  Inserted 104072 pathway rows
WARNNING: 297 (of 10845) Gene symbols did not find a TCRD target.

load-ReactomePathways.py: Done. Elapsed time: 0:12:38.621

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-23.sql

# WikiPathways
[smathias@juniper loaders]$ ./load-WikiPathways.py --dbname tcrd5

load-WikiPathways.py (v2.1.0) [Thu Mar 29 10:17:00 2018]:
Downloading  http://www.pathvisio.org/data/bots/gmt/current/gmt_wp_Homo_sapiens.gmt
         to  ../data/WikiPathways/gmt_wp_Homo_sapiens.gmt

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 427 input line from WikiPathways file ../data/WikiPathways/gmt_wp_Homo_sapiens.gmt
Progress: 100% [######################################################################] Time: 0:01:55
Processed 427 WikiPathways.
  Inserted 17827 pathway rows
WARNNING: 405 (of 5955) Gene IDs did not find a TCRD target.

load-WikiPathways.py: Done. Elapsed time: 0:01:55.805

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-24.sql

##
## PPIs
##
# BioPlex
[smathias@juniper loaders]$ ./load-BioPlexPPIs.py --dbname tcrd5

load-BioPlexPPIs.py (v2.1.0) [Thu Mar 29 11:57:48 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 56553 lines from BioPlex PPI file ../data/BioPlex/BioPlex_interactionList_v4a.tsv
Progress: 100% [######################################################################] Time: 0:01:18
56553 BioPlex PPI rows processed.
  Inserted 56002 new ppi rows
WARNNING: 51 keys did not find a TCRD target. See logfile load-BioPlexPPIs.py.log for details.

Processing 4955 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_May2016.tsv
Progress: 100% [######################################################################] Time: 0:00:26
4955 BioPlex PPI rows processed.
  Inserted 4884 new ppi rows
WARNNING: 14 keys did not find a TCRD target. See logfile load-BioPlexPPIs.py.log for details.

Processing 4305 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Aug2016.tsv
Progress: 100% [######################################################################] Time: 0:00:23
4305 BioPlex PPI rows processed.
  Inserted 4275 new ppi rows
WARNNING: 11 keys did not find a TCRD target. See logfile load-BioPlexPPIs.py.log for details.

Processing 3160 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Dec2016.tsv
Progress: 100% [######################################################################] Time: 0:00:18
3160 BioPlex PPI rows processed.
  Inserted 3131 new ppi rows
WARNNING: 11 keys did not find a TCRD target. See logfile load-BioPlexPPIs.py.log for details.

Processing 4046 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_April2017.tsv
Progress: 100% [######################################################################] Time: 0:00:21
4046 BioPlex PPI rows processed.
  Inserted 4003 new ppi rows
WARNNING: 20 keys did not find a TCRD target. See logfile load-BioPlexPPIs.py.log for details.

Processing 4464 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Nov2017.tsv
Progress: 100% [######################################################################] Time: 0:00:23
4464 BioPlex PPI rows processed.
  Inserted 4320 new ppi rows
WARNNING: 16 keys did not find a TCRD target. See logfile load-BioPlexPPIs.py.log for details.

load-BioPlexPPIs.py: Done. Elapsed time: 0:03:11.854

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-25.sql

# Reactome
[smathias@juniper loaders]$ ./load-ReactomePPIs.py --dbname tcrd5

load-ReactomePPIs.py (v2.1.0) [Thu Mar 29 12:58:27 2018]:

Downloading  https://reactome.org/download/current/interactors/reactome.homo_sapiens.interactions.tab-delimited.txt
         to  ../data/Reactome/reactome.homo_sapiens.interactions.tab-delimited.txt
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 25092 lines from Reactome PPI file ../data/Reactome/reactome.homo_sapiens.interactions.tab-delimited.txt
Progress: 100% [######################################################################] Time: 0:00:09
25092 Reactome PPI rows processed.
  Skipped 7489 non-complex rows or rows without two UniProt interactors
  Skipped 2433 duplicate PPIs
  Inserted 4288 (4288) new ppi rows
WARNNING: 165 UniProt accessions did not find a TCRD target.

load-ReactomePPIs.py: Done. Elapsed time: 0:00:10.608

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-26.sql

#
## Harmonizome
##
[smathias@juniper loaders]$ ./load-Harmonizome.py --dbname ga5 --loglevel 20 --command map

load-Harmonizome.py (v2.0.0) [Wed Mar 28 11:46:21 2018]:

Connected to TCRD database ga5 (schema ver 5.0.1; data ver 5.0.0)

Mapping 20244 TCRD targets to Harmonizome genes
Progress: 100% [#####################################################################] Time: 22:34:44
  20244 targets processed.
  Dumping 19395 sym => TCRD protein_id mappings to file ./tcrd5logs/Sym2pidv4.p
  Skipped 176 targets with no sym
  7 errors encountered. See logfile ./tcrd5logs/load-Harmonizome.py.log for details.
  30 GeneID mismatches. See logfile ./tcrd5logs/load-Harmonizome.py.log for details.

load-Harmonizome.py: Done. Elapsed Time: 22:34:44.805

[smathias@juniper tcrd5logs]$ grep ERROR load-Harmonizome.py.log
2018-03-28 16:29:17 - __main__ - ERROR: No JSON for 3923:CT45A6 => http 500
2018-03-28 16:33:45 - __main__ - ERROR: No JSON for 3981:CT45A6
2018-03-28 16:55:37 - __main__ - ERROR: No JSON for 4281:CT45A6
2018-03-28 19:11:02 - __main__ - ERROR: No JSON for 5907:FAM231A => http 500
2018-03-28 19:17:08 - __main__ - ERROR: No JSON for 5990:FAM231C => http 500
2018-03-28 21:14:18 - __main__ - ERROR: No JSON for 7583:HSPA1B => http 500
2018-03-28 21:28:00 - __main__ - ERROR: No JSON for 7761:HSPA1B

Check possible geneid updates.
T means TCRD correct. H means Harmonizome correct. * Means neither correct
[smathias@juniper tcrd5logs]$ grep 'GeneID mismatch' load-Harmonizome.py.log
2018-03-28 11:52:16 - __main__ - WARNING: GeneID mismatch: Harmonizome: 171 vs TCRD: 4301 T
2018-03-28 14:33:25 - __main__ - WARNING: GeneID mismatch: Harmonizome: 642326 vs TCRD: 102724928 T
2018-03-28 15:34:47 - __main__ - WARNING: GeneID mismatch: Harmonizome: 389422 vs TCRD: 105377934 T
2018-03-28 16:14:09 - __main__ - WARNING: GeneID mismatch: Harmonizome: 414767 vs TCRD: 102724845 * -> 221262
2018-03-28 16:56:24 - __main__ - WARNING: GeneID mismatch: Harmonizome: 102723489 vs TCRD: 107985476 H
2018-03-28 16:56:29 - __main__ - WARNING: GeneID mismatch: Harmonizome: 101928147 vs TCRD: 102723451 H
2018-03-28 17:32:55 - __main__ - WARNING: GeneID mismatch: Harmonizome: 54869 vs TCRD: 83450 T
2018-03-28 17:39:32 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100288687 vs TCRD: 107987491 *
2018-03-28 18:03:36 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100862693 vs TCRD: 105377641 H
2018-03-28 18:07:29 - __main__ - WARNING: GeneID mismatch: Harmonizome: 1942 vs TCRD: 79631 T
2018-03-28 18:51:59 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100862694 vs TCRD: 105372315 H
2018-03-28 20:02:12 - __main__ - WARNING: GeneID mismatch: Harmonizome: 442117 vs TCRD: 64409 T
2018-03-28 20:37:35 - __main__ - WARNING: GeneID mismatch: Harmonizome: 54145 vs TCRD: 102724334 H
2018-03-28 20:58:02 - __main__ - WARNING: GeneID mismatch: Harmonizome: 728411 vs TCRD: 100653061 H
2018-03-28 21:06:05 - __main__ - WARNING: GeneID mismatch: Harmonizome: 55769 vs TCRD: 54969 T
2018-03-28 23:27:17 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100132476 vs TCRD: 100996750 H
2018-03-28 23:42:51 - __main__ - WARNING: GeneID mismatch: Harmonizome: 11025 vs TCRD: 107987462 H
2018-03-29 00:26:39 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100144878 vs TCRD: 105378803 T
2018-03-29 04:07:53 - __main__ - WARNING: GeneID mismatch: Harmonizome: 283970 vs TCRD: 109731405 T
2018-03-29 05:00:00 - __main__ - WARNING: GeneID mismatch: Harmonizome: 441263 vs TCRD: 107161145 T
2018-03-29 05:04:12 - __main__ - WARNING: GeneID mismatch: Harmonizome: 645414 vs TCRD: 391003 T
2018-03-29 05:08:18 - __main__ - WARNING: GeneID mismatch: Harmonizome: 729528 vs TCRD: 400736 T
2018-03-29 08:54:27 - __main__ - WARNING: GeneID mismatch: Harmonizome: 66004 vs TCRD: 432355 T
2018-03-29 09:51:15 - __main__ - WARNING: GeneID mismatch: Harmonizome: 414060 vs TCRD: 101060389 T
2018-03-29 09:51:26 - __main__ - WARNING: GeneID mismatch: Harmonizome: 84218 vs TCRD: 101060321 T
2018-03-29 09:58:38 - __main__ - WARNING: GeneID mismatch: Harmonizome: 414059 vs TCRD: 102724862 T
2018-03-29 10:17:52 - __main__ - WARNING: GeneID mismatch: Harmonizome: 80761 vs TCRD: 105375355 T
2018-03-29 10:19:25 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100506301 vs TCRD: 102724231 T
2018-03-29 10:20:42 - __main__ - WARNING: GeneID mismatch: Harmonizome: 100130863 vs TCRD: 100533646 T
2018-03-29 10:20:44 - __main__ - WARNING: GeneID mismatch: Harmonizome: 7624 vs TCRD: 105379427 T

UPDATE protein SET geneid = 221262 WHERE geneid = 102724845;
UPDATE protein SET geneid = 102724845 WHERE geneid = 107985476;
UPDATE protein SET geneid = 101928147 WHERE geneid = 102723451;
UPDATE protein SET geneid = 100288687 WHERE geneid = 107987491;
UPDATE protein SET geneid = 100862693 WHERE geneid = 105377641;
UPDATE protein SET geneid = 100862694 WHERE geneid = 105372315;
UPDATE protein SET geneid = 54145 WHERE geneid = 102724334;
UPDATE protein SET geneid = 100132476 WHERE geneid = 100996750;
UPDATE protein SET geneid = 11025 WHERE geneid = 107987462;
UPDATE protein SET geneid = 728411 WHERE geneid = 100653061;

[smathias@juniper tcrd5logs]$ mv load-Harmonizome.py.log load-HarmonizomeMap.py.log

[smathias@juniper loaders]$ ./load-Harmonizome.py --dbname ga5 --loglevel 20 --command load

load-Harmonizome.py (v2.0.0) [Thu Mar 29 11:25:40 2018]:

Connected to TCRD database ga5 (schema ver 5.0.1; data ver 5.0.0)

Loading mapping of TCRD targets to Harmonizome genes from pickle file ./tcrd5logs/Sym2pid.p
  Got 19395 symbol to protein_id mappings

Processing 114 Harmonizome datasets
  Processing dataset "Reactome Pathways" containing 1638 gene sets
  Processing dataset "Reactome Pathways" containing 1638 gene sets
  Processing dataset "MiRTarBase microRNA Targets" containing 596 gene sets
  Processing dataset "GAD High Level Gene-Disease Associations" containing 18 gene sets
  Processing dataset "Allen Brain Atlas Prenatal Human Brain Tissue Gene Expression Profiles" containing 516 gene sets
  Processing dataset "GTEx Tissue Gene Expression Profiles" containing 29 gene sets
  Processing dataset "DISEASES Text-mining Gene-Disease Assocation Evidence Scores" containing 4628 gene sets
  Processing dataset "Allen Brain Atlas Developing Human Brain Tissue Gene Expression Profiles by RNA-seq" containing 524 gene sets
  Processing dataset "Allen Brain Atlas Developing Human Brain Tissue Gene Expression Profiles by Microarray" containing 492 gene sets

mysql> delete from gene_attribute where gat_id = 8;
mysql> delete from gene_attribute_type where id = 8;
mysql> alter table gene_attribute_type AUTO_INCREMENT = 8;

smathias@juniper loaders]$ ./load-Harmonizome.py --dbname ga5 --loglevel 20 --command load

load-Harmonizome.py (v2.0.0) [Mon Apr  2 10:25:55 2018]:

Connected to TCRD database ga5 (schema ver 5.0.1; data ver 5.0.0)

Loading mapping of TCRD targets to Harmonizome genes from pickle file ./tcrd5logs/Sym2pid.p
  Got 19395 symbol to protein_id mappings

Processing 114 Harmonizome datasets
  Skipping previously loaded dataset "Reactome Pathways"
  ...
  Skipping previously loaded dataset "Allen Brain Atlas Developing Human Brain Tissue Gene Expression Profiles by RNA-seq"
  Processing dataset "Allen Brain Atlas Developing Human Brain Tissue Gene Expression Profiles by Microarray" containing 492 gene sets
  Processing dataset "DrugBank Drug Targets" containing 4928 gene sets
  Processing dataset "NURSA Protein Complexes" containing 1796 gene sets
  Processing dataset "JASPAR Predicted Transcription Factor Targets" containing 111 gene sets
  Processing dataset "TCGA Signatures of Differentially Expressed Genes for Tumors" containing 5904 gene sets
  Processing dataset "GWASdb SNP-Disease Associations" containing 585 gene sets
  Processing dataset "Biocarta Pathways" containing 254 gene sets
  Processing dataset "ENCODE Histone Modification Site Profiles" containing 435 gene sets
  Processing dataset "CHEA Transcription Factor Targets" containing 199 gene sets
  Processing dataset "GO Molecular Function Annotations" containing 4162 gene sets
  Processing dataset "Virus MINT Protein-Viral Protein Interactions" containing 185 gene sets
  Processing dataset "TRANSFAC Predicted Transcription Factor Targets" containing 158 gene sets
  Processing dataset "Virus MINT Protein-Virus Interactions" containing 68 gene sets
  Processing dataset "SILAC Phosphoproteomics Signatures of Differentially Phosphorylated Proteins for Gene Perturbations" containing 10 gene sets
  Processing dataset "TISSUES Experimental Tissue Protein Expression Evidence Scores" containing 243 gene sets
  Processing dataset "ENCODE Transcription Factor Targets" containing 181 gene sets
  Processing dataset "InterPro Predicted Protein Domain Annotations" containing 11015 gene sets
  Processing dataset "TRANSFAC Curated Transcription Factor Targets" containing 201 gene sets
  Processing dataset "MSigDB Cancer Gene Co-expression Modules" containing 356 gene sets
  Processing dataset "GTEx Tissue Sample Gene Expression Profiles" containing 2918 gene sets
  Processing dataset "Phosphosite Textmining Biological Term Annotations" containing 882 gene sets
  Processing dataset "PhosphoSitePlus Substrates of Kinases" containing 359 gene sets
  Processing dataset "Achilles Cell Line Gene Essentiality Profiles" containing 216 gene sets
  Processing dataset "PANTHER Pathways" containing 145 gene sets
  Processing dataset "COSMIC Cell Line Gene CNV Profiles" containing 950 gene sets
  Processing dataset "Wikipathways Pathways" containing 427 gene sets
  Processing dataset "CTD Gene-Chemical Interactions" containing 9516 gene sets
  Processing dataset "DEPOD Substrates of Phosphatases" containing 112 gene sets
  Processing dataset "GO Biological Process Annotations" containing 13212 gene sets
  Processing dataset "HPA Cell Line Gene Expression Profiles" containing 43 gene sets
  Processing dataset "TISSUES Text-mining Tissue Protein Expression Evidence Scores" containing 4187 gene sets
  Processing dataset "GTEx eQTL" containing 7815 gene sets
  Processing dataset "ESCAPE Omics Signatures of Genes and Proteins for Stem Cells" containing 228 gene sets
  Processing dataset "GO Cellular Component Annotations" containing 1547 gene sets
  Processing dataset "COMPARTMENTS Text-mining Protein Localization Evidence Scores" containing 2081 gene sets
  Processing dataset "OMIM Gene-Disease Associations" containing 6175 gene sets
  Processing dataset "Klijn et al., Nat. Biotechnol., 2015 Cell Line Gene Mutation Profiles" containing 676 gene sets
  Processing dataset "Heiser et al., PNAS, 2011 Cell Line Gene Expression Profiles" containing 56 gene sets
  Processing dataset "CCLE Cell Line Gene Mutation Profiles" containing 904 gene sets
  Processing dataset "Guide to Pharmacology Chemical Ligands of Receptors" containing 4893 gene sets
  Processing dataset "MotifMap Predicted Transcription Factor Targets" containing 329 gene sets
  Processing dataset "BioGPS Human Cell Type and Tissue Gene Expression Profiles" containing 84 gene sets
  Processing dataset "GEO Signatures of Differentially Expressed Genes for Diseases" containing 233 gene sets
  Processing dataset "HPA Tissue Gene Expression Profiles" containing 31 gene sets
  Processing dataset "ENCODE Transcription Factor Binding Site Profiles" containing 1679 gene sets
  Processing dataset "Roadmap Epigenomics Cell and Tissue DNA Accessibility Profiles" containing 0 gene sets
  Processing dataset "ClinVar Gene-Phenotype Associations" containing 3291 gene sets
  Processing dataset "GEO Signatures of Differentially Expressed Genes for Small Molecules" containing 415 gene sets
  Processing dataset "GEO Signatures of Differentially Expressed Genes for Gene Perturbations" containing 739 gene sets
  Processing dataset "GWAS Catalog SNP-Phenotype Associations" containing 1007 gene sets
  Processing dataset "CHEA Transcription Factor Binding Site Profiles" containing 353 gene sets
  Processing dataset "ProteomicsDB Cell Type and Tissue Protein Expression Profiles" containing 53 gene sets
  Processing dataset "DISEASES Curated Gene-Disease Assocation Evidence Scores" containing 770 gene sets
  Processing dataset "Guide to Pharmacology Protein Ligands of Receptors" containing 211 gene sets
  Processing dataset "BioGPS Mouse Cell Type and Tissue Gene Expression Profiles" containing 74 gene 
sets
  Processing dataset "LOCATE Curated Protein Localization Annotations" containing 78 gene sets
  Processing dataset "HPA Tissue Protein Expression Profiles" containing 44 gene sets
  Processing dataset "Roadmap Epigenomics Cell and Tissue DNA Methylation Profiles" containing 24 gen
e sets
  Processing dataset "HPA Tissue Sample Gene Expression Profiles" containing 121 gene sets
  Processing dataset "CCLE Cell Line Gene Expression Profiles" containing 1035 gene sets
  Processing dataset "Roadmap Epigenomics Histone Modification Site Profiles" containing 383 gene set
s
  Processing dataset "CTD Gene-Disease Associations" containing 5218 gene sets
  Processing dataset "Pathway Commons Protein-Protein Interactions" containing 15747 gene sets
  Processing dataset "LINCS KinomeScan Kinase Inhibitor Targets" containing 71 gene sets
  Processing dataset "COMPARTMENTS Experimental Protein Localization Evidence Scores" containing 59 gene sets
  Processing dataset "PID Pathways" containing 223 gene sets
  Processing dataset "GEO Signatures of Differentially Expressed Genes for Transcription Factor Perturbations" containing 154 gene sets
  Processing dataset "Allen Brain Atlas Adult Human Brain Tissue Gene Expression Profiles" containing 414 gene sets
  Processing dataset "NURSA Protein-Protein Interactions" containing 1127 gene sets
  Processing dataset "Klijn et al., Nat. Biotechnol., 2015 Cell Line Gene CNV Profiles" containing 668 gene sets
  Processing dataset "MSigDB Signatures of Differentially Expressed Genes for Cancer Gene Perturbations" containing 90 gene sets
  Processing dataset "CMAP Signatures of Differentially Expressed Genes for Small Molecules" containing 6100 gene sets
  Processing dataset "GEO Signatures of Differentially Expressed Genes for Viral Infections" containing 366 gene sets
  Processing dataset "SILAC Phosphoproteomics Signatures of Differentially Phosphorylated Proteins for Protein Ligands" containing 9 gene sets
  Processing dataset "Klijn et al., Nat. Biotechnol., 2015 Cell Line Gene Expression Profiles" containing 650 gene sets
  Processing dataset "HPO Gene-Disease Associations" containing 6842 gene sets
  Processing dataset "dbGAP Gene-Trait Associations" containing 510 gene sets
  Processing dataset "SILAC Phosphoproteomics Signatures of Differentially Phosphorylated Proteins for Drugs" containing 23 gene sets
  Processing dataset "HuGE Navigator Gene-Phenotype Associations" containing 2752 gene sets
  Processing dataset "TISSUES Curated Tissue Protein Expression Evidence Scores" containing 643 gene sets
  Processing dataset "Hub Proteins Protein-Protein Interactions" containing 289 gene sets
  Processing dataset "BioGPS Cell Line Gene Expression Profiles" containing 93 gene sets
  Processing dataset "LINCS L1000 CMAP Signatures of Differentially Expressed Genes for Small Molecules" containing 30970 gene sets
  
mysql> delete from gene_attribute where gat_id = 90;
mysql> delete from gene_attribute_type where id = 90;
mysql> alter table gene_attribute_type AUTO_INCREMENT = 90;


[smathias@juniper loaders]$ ./load-Harmonizome.py --dbname ga5 --loglevel 20 --command load

load-Harmonizome.py (v2.0.0) [Mon Apr 16 11:13:52 2018]:

Connected to TCRD database ga5 (schema ver 5.0.1; data ver 5.0.0)

Loading mapping of TCRD targets to Harmonizome genes from pickle file ./tcrd5logs/Sym2pid.p
  Got 19395 symbol to protein_id mappings

Processing 114 Harmonizome datasets
  Skipping previously loaded dataset "Reactome Pathways"
  ...
  Skipping previously loaded dataset "BioGPS Cell Line Gene Expression Profiles"
  Processing dataset "LINCS L1000 CMAP Signatures of Differentially Expressed Genes for Small Molecules" containing 30970 gene sets
  Processing dataset "GEO Signatures of Differentially Expressed Genes for Kinase Perturbations" containing 285 gene sets
  Processing dataset "GDSC Cell Line Gene Expression Profiles" containing 624 gene sets
  Processing dataset "GeneSigDB Published Gene Signatures" containing 3515 gene sets
  Processing dataset "MPO Gene-Phenotype Associations" containing 8579 gene sets
  Processing dataset "GAD Gene-Disease Associations" containing 12774 gene sets
  Processing dataset "GWASdb SNP-Phenotype Associations" containing 822 gene sets
  Processing dataset "Roadmap Epigenomics Cell and Tissue Gene Expression Profiles" containing 57 gene sets
  Processing dataset "TargetScan Predicted Nonconserved microRNA Targets" containing 1539 gene sets
  Processing dataset "TargetScan Predicted Conserved microRNA Targets" containing 1537 gene sets
  Processing dataset "PhosphoSitePlus Phosphosite-Disease Associations" containing 140 gene sets
  Processing dataset "CCLE Cell Line Gene CNV Profiles" containing 1040 gene sets
  Processing dataset "GeneRIF Biological Term Annotations" containing 91042 gene sets
  Processing dataset "KEGG Pathways" containing 200 gene sets
  Processing dataset "COMPARTMENTS Curated Protein Localization Evidence Scores" containing 1463 gene sets
  Processing dataset "HumanCyc Pathways" containing 286 gene sets
  Processing dataset "KEA Substrates of Kinases" containing 457 gene sets
  Processing dataset "LINCS Kinativ Kinase Inhibitor Bioactivity Profiles" containing 23 gene sets
  Processing dataset "COSMIC Cell Line Gene Mutation Profiles" containing 1026 gene sets
  Processing dataset "HPM Cell Type and Tissue Protein Expression Profiles" containing 4 gene sets
  Processing dataset "Allen Brain Atlas Adult Mouse Brain Tissue Gene Expression Profiles" containing 2170 gene sets
  Processing dataset "HMDB Metabolites of Enzymes" containing 22137 gene sets
  Processing dataset "CORUM Protein Complexes" containing 2075 gene sets
  Processing dataset "DISEASES Experimental Gene-Disease Assocation Evidence Scores" containing 350 gene sets
  Processing dataset "LOCATE Predicted Protein Localization Annotations" containing 24 gene sets

Processed 114 Ma'ayan Lab datasets.
Inserted 25 new gene_attribute_type rows
Inserted a total of 15241408 gene_attribute rows
WARNING: 3 errors occurred. See logfile ./tcrd5logs/load-Harmonizome.py.log for details.

load-Harmonizome.py: Done. Elapsed time: 291:14:24.519

mysql> delete from gene_attribute_type where id not in (select distinct gat_id from gene_attribute);
Query OK, 1 row affected (0.89 sec)
mysql> select count(*) from gene_attribute_type;
+----------+
| count(*) |
+----------+
|      113 |
+----------+

[smathias@juniper loaders]$ ./load-HGramCDFs.py --dbname ga5

load-HGramCDFs.py (v2.1.0) [Tue May  1 12:14:38 2018]:

Connected to TCRD database ga5 (schema ver 5.0.1; data ver 5.0.0)

Collecting counts for 113 gene attribute types on 20244 TCRD targets
Progress: 100% [######################################################################] Time: 1:00:26

Calculatig Gene Attribute stats. See logfile tcrd5logs/load-HGramCDFs.py.log.

Loading HGram CDFs for 20244 TCRD targets
Progress: 100% [######################################################################] Time: 1:16:20
Processed 20244 targets.
  Loaded 1168463 new hgram_cdf rows
  Skipped 19015 NaN CDFs

load-HGramCDFs.py: Done. Elapsed time: 2:16:46.970

[smathias@juniper SQL]$ mysqldump --no-create-db ga5 gene_attribute_type gene_attribute hgram_cdf > dumps5/harmonizome.sql


##
## Expression
##
# JensenLab TISSUES
[smathias@juniper loaders]$ ./load-JensenLabTISSUES.py --dbname tcrd5

load-JensenLabTISSUES.py (v2.1.0) [Thu Mar 29 13:13:49 2018]:

Downloading  http://download.jensenlab.org/human_tissue_knowledge_filtered.tsv
         to  ../data/JensenLab/human_tissue_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_tissue_experiments_filtered.tsv
         to  ../data/JensenLab/human_tissue_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_tissue_textmining_filtered.tsv
         to  ../data/JensenLab/human_tissue_textmining_filtered.tsv

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 64093 lines in input file ../data/JensenLab/human_tissue_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:03:30
64093 rows processed.
  Inserted 65240 new expression rows for 16759 proteins
No target found for 52 stringids/symbols. See logfile ./tcrd5logs/load-JensenLabTISSUES.py.log for details.

Processing 1610815 lines in input file ../data/JensenLab/human_tissue_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 0:22:06
1610815 rows processed.
  Inserted 1625001 new expression rows for 18494 proteins
  Skipped 0 zero confidence rows
No target found for 310 stringids/symbols. See logfile ./tcrd5logs/load-JensenLabTISSUES.py.log for details.

Processing 60196 lines in input file ../data/JensenLab/human_tissue_textmining_filtered.tsv
Progress: 100% [######################################################################] Time: 0:04:12
60196 rows processed.
  Inserted 59938 new expression rows for 12531 proteins
No target found for 1122 stringids/symbols. See logfile ./tcrd5logs/load-JensenLabTISSUES.py.log for details.

load-JensenLabTISSUES.py: Done. Elapsed time: 0:30:04.907

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-27.sql

# HPM
[smathias@juniper loaders]$ ./load-HPM.py --dbname tcrd5

load-HPM.py (v2.1.0) [Tue Apr  3 10:03:35 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 901681 lines in HPM file ../data/HPM/HPM.protein.qualitative.2015-09-10.tsv
/home/app/TCRD/loaders/TCRD.py:625: Warning: Data truncated for column 'number_value' at row 1-:--:--
  curs.execute(sql, params)
Progress: 100% [######################################################################] Time: 0:49:01
Processed 901681 lines.
  Inserted 836940 new expression rows for 16251 targets (27898 RefSeqs)
No target found for 2158 RefSeqs. See logfile tcrd5logs/load-HPM.py.log for details.

Processing 30057 lines in Tissue Specificity Index file ../data/HPM/HPM.protein.tau.2015-09-10.tsv
/home/app/TCRD/loaders/TCRD.py:586: Warning: Data truncated for column 'number_value' at row 1-:--:--
  curs.execute(sql, (xid, itype, value))
Progress: 100% [######################################################################] Time: 0:00:20
Processed 30057 lines.
  Inserted 27898 new HPM Protein Tissue Specificity Index tdl_info rows for 16251 targets
  2158 RefSeqs not in map from expression file

Processing 518821 lines in HPM file ../data/HPM/HPM.gene.qualitative.2015-09-10.tsv
Progress: 100% [######################################################################] Time: 0:05:12
Processed 518821 lines.
  Inserted 480780 new expression rows for 16026 targets (16026 Gene Symbols)
  No target found for 1268 symbols. See logfile tcrd5logs/load-HPM.py.log for details.

Processing 17295 lines in Tissue Specificity Index file ../data/HPM/HPM.gene.tau.2015-09-10.tsv
Progress: 100% [######################################################################] Time: 0:00:11
Processed 17295 lines.
  Inserted 16026 new HPM Gene Tissue Specificity Index tdl_info rows for 16026 targets
  1268 symbols not in map from expression file

load-HPM.py: Done. Elapsed time: 0:54:45.920

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-28.sql

# HPA
[smathias@juniper loaders]$ ./load-HPA.py --dbname tcrd5

load-HPA.py (v2.1.0) [Wed Apr  4 14:58:16 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 848428 lines in HPA file ../data/HPA/HPA.Protein.expression.qualitative.2018-04-03.tsv
Progress: 100% [######################################################################] Time: 0:27:27
Processed 848428 HPA lines.
  Inserted 840902 new expression rows for 10452 targets (10524 ENSGs)
No target found for 94 ENSGs. See logfile tcrd5logs/load-HPA.py.log for details.

Processing 10580 lines in Tissue Specificity Index file ../data/HPA/HPA.Protein.tau.2018-04-03.tsv
/home/app/TCRD/loaders/TCRD.py:586: Warning: Data truncated for column 'number_value' at row 1-:--:--
  curs.execute(sql, (xid, itype, value))
Progress: 100% [######################################################################] Time: 0:00:08
Processed 10580 lines.
  Inserted 10485 new HPA Protein Tissue Specificity Index tdl_info rows for 10414 targets
  94 ENSGs not in map from expression file

Processing 725682 lines in HPA file ../data/HPA/HPA.RNA.expression.qualitative.2018-04-03.tsv
Progress: 100% [######################################################################] Time: 0:39:53
Processed 725682 lines.
  Inserted 702556 new expression rows for 18869 targets (18988 ENSGs)
  No target found for 625 ENSGs. See logfile tcrd5logs/load-HPA.py.log for details.

Processing 19614 lines in Tissue Specificity Index file ../data/HPA/HPA.RNA.tau.2018-04-03.tsv
Progress: 100% [######################################################################] Time: 0:00:15
Processed 19614 lines.
  Inserted 18988 new HPA RNA Tissue Specificity Index tdl_info rows for 18869 targets
  625 ENSGs not in map from expression file

load-HPA.py: Done. Elapsed time: 1:07:46.234

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-29.sql

# GTEx
[smathias@juniper loaders]$ ./load-GTEx.py --dbname tcrd5

load-GTEx.py (v2.1.0) [Thu Apr  5 10:11:59 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.1; data ver 5.0.0)

Processing 32626637 lines in GTEx file ../data/GTEx/gtex.tpm.qualitative.2017-10-06.tsv
/home/app/TCRD/loaders/TCRD.py:625: Warning: Data truncated for column 'number_value' at row 1-:--:--
  curs.execute(sql, params)
Progress: 100% [######################################################################] Time: 4:23:50
Processed 32626637 lines
  Inserted 10916990 new expression rows for 18717 targets (18790 ENSGs)
  No target found for 37366 ENSGs. See logfile tcrd5logs/load-GTEx.py.log for details.

Processing 56157 lines in Tissue Specificity Index file ../data/GTEx/gtex.tau.2017-10-06.tsv
/home/app/TCRD/loaders/TCRD.py:586: Warning: Data truncated for column 'number_value' at row 1-:--:--
  curs.execute(sql, (xid, itype, value))
Progress: 100% [######################################################################] Time: 0:00:17
Processed 56157 lines
  Inserted 18790 new GTEx Tissue Specificity Index tdl_info rows for 18717 targets
  37366 ENSGs not in map from expression file

load-GTEx.py: Done. Elapsed time: 4:24:17.678

ALTER TABLE expression CHANGE gender sex varchar(8) NULL;
UPDATE dbinfo SET schema_ver = '5.0.2';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-29.sql

# Cell Surface Protein Atlas
[smathias@juniper loaders]$ ./load-CSPA.py --dbname tcrd5

load-CSPA.py (v1.1.0) [Fri Apr  6 11:55:44 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 1500 lines from CSPA file ../data/CSPA/S1_File.csv
Progress: 100% [######################################################################] Time: 0:00:09
Processed 1499 CSPA lines.
  Inserted 10104 new expression rows for 1038 targets
  Skipped 460 non-high confidence rows
  No target found for 1 UniProts/GeneIDs. See logfile tcrd5logs/load-CSPA.py.log for details

load-CSPA.py: Done. Elapsed time: 0:00:09.431

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-30.sql

# Human Cell Atlas

load-HumanCellAtlas.py (v1.1.0) [Fri Apr  6 11:59:19 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Calculating expression level percentiles

Processing 19629 lines from HCA file ../data/HCA/aal3321_Thul_SM_table_S1.csv
Progress: 100% [######################################################################] Time: 0:14:18
Processed 19628 lines.
  Inserted 1077944 new expression rows for 19060 proteins
  No target found for 547 Symbols/ENSGs. See logfile tcrd5logs/load-HumanCellAtlas.py.log for details

Processing 12004 lines from HCA file ../data/HCA/aal3321_Thul_SM_table_S6.csv
Progress: 100% [######################################################################] Time: 0:00:37
Processed 12003 lines.
  Inserted 18476 new compartment rows for 11790 proteins
  No target found for 188 UniProts/Symbols. See logfile tcrd5logs/load-HumanCellAtlas.py.log for details

load-HumanCellAtlas.py: Done. Elapsed time: 0:14:56.746

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-31.sql

# Consensus
[smathias@juniper loaders]$ ./load-ConsensusExpressions.py --dbname tcrd5

load-ConsensusExpressions.py (v2.1.0) [Mon Apr  9 12:31:15 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processiong 249 lines in tissue mapping file: ../data/Tissues_Typed_v2.1.csv
  Got 197 tissue name mappings

Calculating/Loading Consensus expressions for 20244 TCRD targets
Progress: 100% [######################################################################] Time: 0:25:35
Processed 20244 targets.
  Inserted 185947 new Consensus expression rows.

load-ConsensusExpressions.py: Done. Elapsed time: 0:25:35.197

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-32.sql

#
# Compartments
#
[smathias@juniper loaders]$ ./load-JensenLab-COMPARTMENTS.py --dbname tcrd5

load-JensenLab-COMPARTMENTS.py (v2.1.0) [Wed Apr 25 13:46:37 2018]:

Downloading  http://download.jensenlab.org/human_compartment_knowledge_full.tsv
         to  ../data/JensenLab/human_compartment_knowledge_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_experiments_full.tsv
         to  ../data/JensenLab/human_compartment_experiments_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_textmining_full.tsv
         to  ../data/JensenLab/human_compartment_textmining_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_predictions_full.tsv
         to  ../data/JensenLab/human_compartment_predictions_full.tsv

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 651883 lines in input file ../data/JensenLab/human_compartment_knowledge_full.tsv
Progress: 100% [######################################################################] Time: 0:10:45
651883 lines processed.
  Inserted 621010 new compartment rows for 17341 proteins
  Skipped 61863 lines with conf < 3
No target found for 102 stringids/symbols. See logfile tcrd5logs/load-JensenLab-COMPARTMENTS.py.log for details.

Processing 120765 lines in input file ../data/JensenLab/human_compartment_experiments_full.tsv
Progress: 100% [######################################################################] Time: 0:00:01
120765 lines processed.
  Inserted 2356 new compartment rows for 218 proteins
  Skipped 118457 lines with conf < 3

Processing 668438 lines in input file ../data/JensenLab/human_compartment_textmining_full.tsv
Progress: 100% [######################################################################] Time: 0:01:29
668438 lines processed.
  Inserted 102290 new compartment rows for 9963 proteins
  Skipped 566159 lines with conf < 3
No target found for 390 stringids/symbols. See logfile tcrd5logs/load-JensenLab-COMPARTMENTS.py.log for details.

Processing 414034 lines in input file ../data/JensenLab/human_compartment_predictions_full.tsv
Progress: 100% [######################################################################] Time: 0:00:44
414034 lines processed.
  Inserted 26114 new compartment rows for 10075 proteins
  Skipped 387715 lines with conf < 3
No target found for 237 stringids/symbols. See logfile tcrd5logs/load-JensenLab-COMPARTMENTS.py.log for details.

load-JensenLab-COMPARTMENTS.py: Done. Elapsed time: 0:13:43.159

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-33.sql


Update IDG2 List
Some symbols on DRGC lists have changed from v4 to v5:
FAM26F -> CALHM4
FAM26D -> CALHM5
FAM26E -> CALHM6
TAAR3 -> TAAR3P
mysql> select fam, idg2, count(*) from target where idg2 group by fam, idg2;
+--------+------+----------+
| fam    | idg2 | count(*) |
+--------+------+----------+
| GPCR   |    1 |      143 |
| IC     |    1 |      117 |
| Kinase |    1 |      134 |
+--------+------+----------+
Total is 394
mysql> update target set idg2 = 0;
mysql> delete from provenance where dataset_id = 2;
mysql> delete from dataset where id = 2;
mysql> update target set fam = 'IC' where id in (4260, 4261, 4262);

[smathias@juniper loaders]$ ./load-IDG2.py --dbname tcrd5

load-IDG2.py (v2.1.0) [Thu Apr 26 11:27:07 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 470 lines in input file ../data/DRGC_RevisedTargetLists.csv
Progress: 100% [######################################################################] Time: 0:00:02
470 lines processed
414 targets updated with IDG2 flags
Skipped 55 'removed' lines
Encountered 1 duplicate symbols: KCNT2

load-IDG2.py: Done. Elapsed time: 0:00:03.018

mysql> select fam, idg2, count(*) from target where idg2 group by fam, idg2;
+--------+------+----------+
| fam    | idg2 | count(*) |
+--------+------+----------+
| GPCR   |    1 |      129 |
| GPCR   |    2 |       15 |
| IC     |    1 |       85 |
| IC     |    2 |       26 |
| Kinase |    1 |      159 |
+--------+------+----------+
Total is 414
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-34.sql


## TIN-X
[smathias@juniper python]$ ./TIN-X.py 

TIN-X.py (v2.2.0) [Thu Apr 26 11:43:24 2018]:

Downloading https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/master/src/ontology/doid.obo
         to ../data/DiseaseOntology/doid.obo

Downloading http://download.jensenlab.org/disease_textmining_mentions.tsv
         to ../data/JensenLab/disease_textmining_mentions.tsv
Downloading http://download.jensenlab.org/human_textmining_mentions.tsv
         to ../data/JensenLab/human_textmining_mentions.tsv

Connected to TCRD database tcrd (schema ver 4.0.12; data ver 4.6.10)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11107 Disease Ontology terms

Processing 20724 lines in protein file ../data/JensenLab/human_textmining_mentions.tsv
Progress: 100% [######################################################################] Time: 0:08:05
20724 lines processed.
  Skipped 2846 non-ENSP lines
  Saved 17851 protein to PMIDs mappings
  Saved 4806201 PMID to protein count mappings
WARNING: No target found for 189 ENSPs. See logfile ../loaders/tcrd5logs/TIN-X.py.log for details.

Processing 8557 lines in file ../data/JensenLab/disease_textmining_mentions.tsv
Progress: 100% [######################################################################] Time: 0:01:15
8557 lines processed.
  Skipped 1668 non-DOID lines
  Saved 6889 DOID to PMIDs mappings
  Saved 9726499 PMID to disease count mappings

Computing protein novely scores
  Wrote 17851 novelty scores to file ../data/TIN-X/TCRDv5/ProteinNovelty.csv

Computing disease novely scores
  Wrote 6889 novelty scores to file ../data/TIN-X/TCRDv5/DiseaseNovelty.csv

Computing importance scores
  Wrote 2403557 importance scores to file ../data/TIN-X/TCRDv5/Importance.csv

Computing PubMed rankings
  Wrote 38089070 PubMed rankings to file ../data/TIN-X/TCRDv5/PMIDRanking.csv

TIN-X.py: Done. Elapsed time: 2:23:12.791

[smathias@juniper loaders]$ ./load-TIN-X.py --dbname tcrd5

load-TIN-X.py (v2.1.0) [Fri May  4 12:06:04 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11107 Disease Ontology terms

Processing 6865 lines in file ../data/TIN-X/TCRDv4/DiseaseNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:03
6864 lines processed.
  Inserted 6864 new tinx_disease rows
  Saved 6864 keys in dmap

Processing 17719 lines in file ../data/TIN-X/TCRDv4/ProteinNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:09
17718 lines processed.
  Inserted 17718 new tinx_novelty rows

Processing 2307335 lines in file ../data/TIN-X/TCRDv4/Importance.csv
Progress: 100% [######################################################################] Time: 0:23:25
2307334 lines processed.
  Inserted 2307334 new tinx_importance rows
  Saved 2307334 keys in imap

Processing 35835017 lines in file ../data/TIN-X/TCRDv4/PMIDRanking.csv
Progress: 100% [######################################################################] Time: 5:42:11
35835016 lines processed.
  Inserted 35835016 new tinx_articlerank rows

load-TIN-X.py: Done. Elapsed time: 6:05:56.479

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-35.sql


## DO
[smathias@juniper loaders]$ ./load-DiseaseOntology.py --dbname tcrd5

load-DiseaseOntology.py (v2.1.0) [Mon May 14 09:56:40 2018]:

Downloading  http://purl.obolibrary.org/obo/doid.obo
         to  ../data/DiseaseOntology/doid.obo
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
Got 11107 Disease Ontology terms

Loading 11107 Disease Ontology terms
Progress: 100% [######################################################################] Time: 0:00:08
11107 terms processed.
  Inserted 8699 new do rows
  Skipped 14 non-DOID terms
  Skipped 2394 obsolete terms

load-DiseaseOntology.py: Done. Elapsed time: 0:00:20.805

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-36.sql


## DTO
[smathias@juniper loaders]$ ./load-DTO.py --dbname tcrd5

load-DTO.py (v2.1.0) [Mon May 14 12:14:40 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 1807 lines in file ../data/UMiami/UniPids_DTOids2.csv
Progress: 100% [######################################################################] Time: 0:00:04
1807 lines processed.
  Updated 1801 protein.dtoid values
1800 DTO to UniProt mappings for TCRD targets
1795 UniProt to DTO mappings for TCRD targets

Parsing DTO JSON file ../data/UMiami/dto.json
Got 571 classifications.

Loading 571 classifications
Progress: 100% [######################################################################] Time: 0:00:01
571 classifications processed.
Inserted 2426 new dto rows

load-DTO.py: Done. Elapsed time: 0:00:05.994

mysql> UPDATE dto SET parent = NULL WHERE name IN ('GPCR', 'Kinase', 'Nuclear hormone receptor', 'Ion channel');
mysql> ALTER TABLE dto ADD CONSTRAINT fk_dto_dto FOREIGN KEY dto_idx1(parent) REFERENCES dto(id) ON DELETE RESTRICT;

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-37.sql


## Grant Tagging
## NB. Done on yucca
[smathias@yucca ~]$ cd TCRD/data/NIHExporter
[smathias@yucca NIHExporter]$ ./get_abstracts.sh
[smathias@yucca NIHExporter]$ ./get_projects.sh
[smathias@yucca NIHExporter]$ rm wget-log*
[smathias@yucca NIHExporter]$ unzip 'RePORTER_PRJ*.zip'
[smathias@yucca NIHExporter]$ rm RePORTER_PRJ*.zip

[smathias@yucca ~]$ cd TCRD
[smathias@yucca TCRD]$ ./python/pickle_grant_info.py 

pickle_grant_info.py (v1.1.0) [Thu May 10 12:26:47 2018]:

Gathering project info for 2000
Gathering project info for 2001
Gathering project info for 2002
Gathering project info for 2003
Gathering project info for 2004
Gathering project info for 2005
Gathering project info for 2006
Gathering project info for 2007
Gathering project info for 2008
Gathering project info for 2009
Gathering project info for 2010
Gathering project info for 2011
Gathering project info for 2012
Gathering project info for 2013
Gathering project info for 2014
Gathering project info for 2015
Gathering project info for 2016
Gathering project info for 2017

Dumping info on projects to pickle ./data/NIHExporter/ProjectInfo2000-2017.p

pickle_grant_info.py: Done. Elapsed time: 13:15:22.698

[smathias@yucca TCRD]$ ./python/grant_tagger.py 

grant_tagger.py (v2.1.0) [Tue May 15 09:35:49 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0) on juniper.health.unm.edu

Loading project info from pickle file ./data/NIHExporter/ProjectInfo2000-2017.p

Creating Tagger...

Tagging 83500 projects from 2000
Progress: 100% [###########################################################################] Time: 0:09:50
83500 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 81265 projects from 2001
Progress: 100% [###########################################################################] Time: 0:07:13
81265 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 83423 projects from 2002
Progress: 100% [###########################################################################] Time: 0:07:47
83423 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 61612 projects from 2003
Progress: 100% [###########################################################################] Time: 0:07:17
61612 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 78778 projects from 2004
Progress: 100% [###########################################################################] Time: 0:08:31
78778 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 82209 projects from 2005
Progress: 100% [###########################################################################] Time: 0:09:24
82209 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 81670 projects from 2006
Progress: 100% [###########################################################################] Time: 0:10:12
81670 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 88886 projects from 2007
Progress: 100% [###########################################################################] Time: 0:11:15
88886 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 87922 projects from 2008
Progress: 100% [###########################################################################] Time: 0:11:57
87922 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 98942 projects from 2009
Progress: 100% [###########################################################################] Time: 0:15:30
98942 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 93841 projects from 2010
Progress: 100% [###########################################################################] Time: 0:14:14
93841 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 83643 projects from 2011
Progress: 100% [###########################################################################] Time: 0:16:38
83643 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 78989 projects from 2012
Progress: 100% [###########################################################################] Time: 0:09:46
78989 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 77036 projects from 2013
Progress: 100% [###########################################################################] Time: 0:11:10
77036 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 76183 projects from 2014
Progress: 100% [###########################################################################] Time: 0:17:26
76183 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 73414 projects from 2015
Progress: 100% [###########################################################################] Time: 0:18:10
73414 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 72363 projects from 2016
Progress: 100% [###########################################################################] Time: 0:19:11
72363 projects processed. See logfile .grant_tagger.py.log for details.

Tagging 72495 projects from 2017
Progress: 100% [###########################################################################] Time: 0:20:02
72495 projects processed. See logfile .grant_tagger.py.log for details.

grant_tagger.py: Done. Elapsed time: 10:14:47.751

mysql> update info_type set name = 'NIHRePORTER 2000-2017 R01 Count' where name = 'NIHRePORTER 2000-2015 R01 Count';

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-38.sql

## Orthologs
[smathias@juniper loaders]$ ./load-Orthologs.py --dbname tcrd5

load-Orthologs.py (v1.3.0) [Thu May 17 11:08:53 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/genenames/hcop/human_all_hcop_sixteen_column.txt.gz
         to  ../data/HGNC/human_all_hcop_sixteen_column.txt.gz
Uncompressing ../data/HGNC/human_all_hcop_sixteen_column.txt.gz
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Loading ortholog data for 20244 TCRD targets

[smathias@juniper loaders]$ ./load-Orthologs.py --dbname tcrd5

load-Orthologs.py (v1.3.0) [Thu May 17 11:08:53 2018]:

Processing 1044735 lines in input file ../data/HGNC/human_all_hcop_sixteen_column.txt
  Generated ortholog dataframe with 182956 entries

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Loading ortholog data for 20244 TCRD targets
Progress: 100% [######################################################################] Time: 0:17:03
Processed 20244 targets.
Loaded 178754 new ortholog rows
  Skipped 3665 empty ortholog entries
  Skipped 169 targets with no sym/geneid

load-Orthologs.py: Done. Elapsed time: 0:17:11.416

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-39.sql


## Ortholog Diseases
[smathias@juniper loaders]$ ./load-MonarchOrthologDiseases.py --dbname tcrd5

load-MonarchOrthologDiseases.py (v1.1.0) [Fri May 18 10:47:17 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Got 113854 orthologs from TCRD

Connecting to UMiami Monarch database.
  Got 39426 ortholog disease records from Monarch database.

Loading 39426 Monarch ortholog diseases
Progress: 100% [######################################################################] Time: 0:12:48
39426 records processed.
  Inserted 37962 new ortholog_disease rows for 3838 targets
WARNING: 80 orthologs not found in TCRD. See logfile tcrd5logs/load-MonarchOrthologDiseases.py.log for details.

load-MonarchOrthologDiseases.py: Done. Elapsed time: 0:12:54.045

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-40.sql


## TFs
[smathias@juniper loaders]$ ./load-TFs.py --dbname tcrd5

load-TFs.py (v1.0.0) [Tue May 22 11:57:29 2018]:

Downloading  http://humantfs.ccbr.utoronto.ca/download/v_1.01/DatabaseExtract_v_1.01.csv
         to  ../data/UToronto/DatabaseExtract_v_1.01.csv
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 2766 lines in input file ../data/UToronto/DatabaseExtract_v_1.01.csv
Progress: 100% [######################################################################] Time: 0:00:45

2765 lines processed.
  Inserted 1634 new 'Is Transcription Factor' tdl_infos
  Skipped 1126 non-TF lines
No target found for 5 symbols/geneids/ENSGs. See logfile tcrd5logs/load-TFs.py.log for details.
Tclin: 19
Tchem: 78
Tbio: 982
Tdark: 555

load-TFs.py: Done. Elapsed time: 0:00:51.736

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-41.sql

## IMPC
[smathias@juniper loaders]$ ./load-IMPCMiceTDLInfos.py --dbname tcrd5

load-IMPCMiceTDLInfos.py (v2.1.0) [Wed May 23 10:51:25 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 385 rows from input file ../data/IMPC/IDG summary-1.csv
Progress: 100% [######################################################################] Time: 0:00:08
384 rows processed.
Inserted 312 new 'IMPC Status' tdl_info rows
Inserted 272 new 'IMPC Clones' tdl_info rows
Skipped 35 rows with no relevant info
No target found for 38 rows. See logfile ./tcrd5logs/load-IMPCMiceTDLInfos.py.log for details.

load-IMPCMiceTDLInfos.py: Done. Elapsed time: 0:00:08.963

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-42.sql


## Drugable Epigenome Domains
[smathias@juniper loaders]$ ./load-DrugableEpigenomeTDLInfos.py --dbname tcrd5

load-DrugableEpigenomeTDLInfos.py (v2.1.0) [Wed May 23 11:54:42 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing Epigenetic Writers
Processing 63 lines from Protein methyltransferase input file /home/smathias/TCRD/data/Epigenetic-RWE
/nrd3674-s8.csv
  62 lines processed. Found 62, skipped 0
  Inserted 62 new tdl_info rows
Processing 19 lines from Histone acetyltransferase input file /home/smathias/TCRD/data/Epigenetic-RWE
/nrd3674-s3.csv
  18 lines processed. Found 18, skipped 0
  Inserted 18 new tdl_info rows

Processing Epigenetic Erasers
Processing 25 lines from Histone deacetylase input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s4.csv
  24 lines processed. Found 24, skipped 0
  Inserted 24 new tdl_info rows
Processing 28 lines from Lysine demethylase input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s5.csv
  27 lines processed. Found 27, skipped 0
  Inserted 27 new tdl_info rows

Processing Epigenetic Readers
Processing 44 lines from Chromodomain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s2.csv
  43 lines processed. Found 43, skipped 0
  Inserted 43 new tdl_info rows
Processing 27 lines from PWWP domain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s9.csv
  26 lines processed. Found 26, skipped 0
  Inserted 26 new tdl_info rows
Processing 171 lines from PHD-containing protein input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s7.csv
  170 lines processed. Found 170, skipped 0
  Inserted 170 new tdl_info rows
Processing 63 lines from Bromodomain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s1.cs
v
  62 lines processed. Found 62, skipped 0
  Inserted 62 new tdl_info rows
Processing 72 lines from Tudor domain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s10.
csv
  71 lines processed. Found 71, skipped 0
  Inserted 71 new tdl_info rows
Processing 30 lines from Methyl-*-binding domain input file /home/smathias/TCRD/data/Epigenetic-RWE/n
rd3674-s6.csv
  29 lines processed. Found 29, skipped 0
  Inserted 29 new tdl_info rows

Inserted a total of 532 new Drugable Epigenome Class tdl_infos

load-DrugableEpigenomeTDLInfos.py: Done. Elapsed time: 0:00:05.287

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-43.sql


## EBI Patent Counts
[smathias@juniper loaders]$ ./load-EBI-PatentCounts.py --dbname tcrd5

load-EBI-PatentCounts.py (v2.2.0) [Wed May 23 12:21:24 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/IDG/patent_counts/latest
         to  ../data/EBI/patent_counts/latest
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 41281 lines in file ../data/EBI/patent_counts/latest
Progress: 100% [######################################################################] Time: 0:01:40
41280 lines processed.
Inserted 41280 new patent_count rows for 1710 targets

Loading 1710 Patent Count tdl_infos
  1710 processed
  Inserted 1710 new EBI Total Patent Count tdl_info rows

load-EBI-PatentCounts.py: Done. Elapsed time: 0:01:44.336

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-44.sql


## PubMed
[smathias@juniper loaders]$ ./load-PubMed.py --dbname tcrd5 --loglevel 20

load-PubMed.py (v2.1.0) [Wed May 23 13:01:45 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Loading pubmeds for 20244 TCRD targets
Progress: 100% [##############################################################] Time: 3 days, 4:35:45
Processed 20244 targets.
  Successfully loaded all PubMeds for 20221 targets
  Inserted 552264 new pubmed rows
  Inserted 1213194 new protein2pubmed rows
WARNING: 1 DB errors occurred. See logfile ./tcrd5logs/load-PubMed.py.log for details.

Hung during TIN-X load. Restarted:
[smathias@juniper loaders]$ ./load-PubMed.py --dbname tcrd5 --loglevel 20

load-PubMed.py (v2.1.0) [Tue May 29 10:36:04 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 2150174 TIN-X PubMed IDs
Processed 2144306 TIN-X PubMed IDs.
  Inserted 1835539 new pubmed rows
  Skiped 308763 existing PubMed IDs
WARNING: 4 DB errors occurred. See logfile ./tcrd5logs/load-PubMed.py.log for details.

load-PubMed.py: Done. Elapsed time: 44:16:26.485

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-45.sql


## KEGG derived stuff
smathias@juniper loaders]$ ./load-KEGGDistances.py --dbname tcrd5

load-KEGGDistances.py (v2.1.0) [Thu May 31 10:08:11 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 292 KGML files in ../data/KEGG/pathways
Progress: 100% [######################################################################] Time: 0:00:02
  Got 204569 total unique non-zero shortest path lengths

Processing 204569 KEGG Distances
Progress: 100% [######################################################################] Time: 0:02:42
204569 KEGG Distances processed.
  Inserted 208538 new kegg_distance rows
  201 KEGG IDs not found in TCRD - Skipped 7922 rows. See logfile ./tcrd5logs/load-KEGGDistances.py.log for details.

load-KEGGDistances.py: Done. Elapsed time: 0:02:45.134

[smathias@juniper loaders]$ ./load-KEGGNearestTclins.py --dbname tcrd5

load-KEGGNearestTclins.py (v2.1.0) [Thu May 31 10:16:36 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 20244 TCRD targets
Progress: 100% [######################################################################] Time: 0:01:03

20244 targets processed.
  1870 non-Tclin targets have upstream Tclin targets
    Inserted 7265 upstream kegg_nearest_tclin rows
  1914 non-Tclin targets have downstream Tclin targets
    Inserted 8029 upstream kegg_nearest_tclin rows

load-KEGGNearestTclins.py: Done. Elapsed time: 0:01:03.573

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-46.sql


## L1000s and LocSig
[smathias@juniper loaders]$ ./load-L1000XRefs.py --dbname tcrd5

load-L1000XRefs.py (v2.1.0) [Fri Jun  1 10:36:52 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 978 rows in file ../data/CMap_LandmarkGenes_n978.csv
Progress: 100% [######################################################################] Time: 0:00:08

978 rows processed.
  Inserted 977 new L1000 ID xref rows for 977 targets
No target found for 1 symbols/geneids. See logfile ./tcrd5logs/load-L1000XRefs.py.log for details.

load-L1000XRefs.py: Done. Elapsed time: 0:00:08.284

[smathias@juniper loaders]$ ./load-LocSigDB.py --dbname tcrd5

load-LocSigDB.py (v1.1.0) [Fri Jun  1 10:41:45 2018]:
Downloading  http://genome.unmc.edu/LocSigDB/doc/LocSigDB.csv
         to  ../data/LocSigDB/LocSigDB.csv

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 534 lines in input file ../data/LocSigDB/LocSigDB.csv
Progress: 100% [######################################################################] Time: 0:10:57
534 lines processed.
  Skipped 234 non-human rows
  Inserted 106632 new locsig rows for 18941 proteins
No target found for 1 input lines. See logfile ./tcrd5logs/load-LocSigDB.py.log for details

load-LocSigDB.py: Done. Elapsed time: 0:11:04.740

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-47.sql


[smathias@juniper loaders]$ ./load-PANTHERClasses.py --dbname tcrd5

load-PANTHERClasses.py (v2.1.0) [Fri Jun  1 10:58:15 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 301 lines in relationships file ../data/PANTHER/Protein_class_relationship
301 input lines processed.
  Got 255 PANTHER Class relationships

Processing 302 lines in class file ../data/PANTHER/Protein_Class_13.0
302 lines processed.
  Inserted 256 new panther_class rows

Processing 19846 lines in classification file ../data/PANTHER/PTHR13.1_human
Progress: 100% [######################################################################] Time: 0:00:35
19846 lines processed.
  Inserted 22722 new p2pc rows for 8149 distinct proteins
  Skipped 11480 rows without PCs
No target found for 219 UniProt/HGNCs. See logfile ./tcrd5logs/load-PANTHERClasses.py.log for details.

load-PANTHERClasses.py: Done. Elapsed time: 0:00:36.153

[smathias@juniper loaders]$ ./load-PubTatorScores.py --dbname tcrd5

load-PubTatorScores.py (v2.1.0) [Fri Jun  1 11:00:26 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 758636 lines in file ../data/JensenLab/pubtator_counts.tsv
Progress: 100% [######################################################################] Time: 0:10:09
758636 lines processed.
  Inserted 292776 new ptscore rows for 17403 targets.
No target found for 82003 NCBI Gene IDs. See logfile ./tcrd5logs/load-PubTatorScores.py.log for details.

Loading 17403 PubTator Score tdl_infos
  17403 processed
  Inserted 17403 new PubTator PubMed Score tdl_info rows

load-PubTatorScores.py: Done. Elapsed time: 0:10:22.200

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-48.sql

[smathias@juniper loaders]$ ./load-PubChemCIDs.py --dbname tcrd5

load-PubChemCIDs.py (v1.1.0) [Fri Jun  1 11:18:39 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/wholeSourceMapping/src_id1/src1src22.txt.gz
         to  ../data/ChEMBL/UniChem/src1src22.txt.gz
Uncompressing ../data/ChEMBL/UniChem/src1src22.txt.gz
Done. Elapsed time: 0:00:09.534

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 1675561 lines in file ../data/ChEMBL/UniChem/src1src22.txt
Got 1654618 ChEMBL to PubChem mappings

Loading PubChem CIDs for 362276 ChEMBL activities
Progress: 100% [######################################################################] Time: 0:04:07
362276 ChEMBL activities processed.
  Inserted 344272 new PubChem CIDs
  11469 ChEMBL IDs not found. See logfile load-PubChemCIDs.py.log for details.

Loading PubChem CIDs for 3827 drug activities
Progress: 100% [######################################################################] Time: 0:00:01
3827 drug activities processed.
  Inserted 2859 new PubChem CIDs
  Skipped 688 drug activities with no ChEMBL ID
  163 ChEMBL IDs not found. See logfile load-PubChemCIDs.py.log for details.

load-PubChemCIDs.py: Done. Elapsed time: 0:04:18.654

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-49.sql


# TMHMM
[smathias@juniper loaders]$ ./load-TMHMM_Predictions.py --dbname tcrd5

load-TMHMM_Predictions.py (v2.1.0) [Fri Jun  1 11:25:16 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)
Processing 20244 TCRD targets
Progress: 100% [######################################################################] Time: 0:34:59
20244 targets processed.
  Inserted 5325 new TMHMM Prediction tdl_info rows

load-TMHMM_Predictions.py: Done. Elapsed time: 0:34:59.936

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-50.sql


## GeneRIF Years
[smathias@juniper python]$ ./mk-PubMed2DateMap.py --dbname tcrd5

mk-PubMed2DateMap.py (v1.1.0) [Fri Jun  1 11:25:47 2018]:
[smathias@juniper python]$ ./mk-PubMed2DateMap.py --dbname tcrd5

mk-PubMed2DateMap.py (v1.1.0) [Fri Jun  1 11:37:09 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Processing 687109 GeneRIFs
Progress: 100% [################################################################] Time: 0:02:41
687109 GeneRIFs processed.
Got date mapping for 439681 PubMeds in TCRD

Getting 4912 missing PubMeds from E-Utils
  Processing chunk 1
...
  Processing chunk 25
687109 PubMed IDs processed.
Got date mapping for 4850 PubMeds not in TCRD
No date for 59 PubMeds
Dumping map to file: ../data/TCRDv5_PubMed2Date.p

mk-PubMed2DateMap.py: Done. Elapsed time: 0:08:25.981

[smathias@juniper loaders]$ ./load-GeneRIF_Years.py --dbname tcrd5

load-GeneRIF_Years.py (v1.1.0) [Fri Jun  1 12:05:37 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Got 444531 PubMed date mappings from file ../data/TCRDv5_PubMed2Date.p

Processing 687109 GeneRIFs
Progress: 100% [######################################################################] Time: 0:08:20
687109 GeneRIFs processed.
  Updated 669375 genefifs with years
  Skipped 17734 generifs with no years.

load-GeneRIF_Years.py: Done. Elapsed time: 0:08:26.019

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5-51.sql


# Harmonizome
# Harmonogram CDFs
mysql> \. dumps5/harmonizome.sql
INSERT INTO `dataset` (name, source, app, app_version, datetime, url, comments) VALUES ('Harmonizome','API at http://amp.pharm.mssm.edu/Harmonizome/','load-Harmonizome.py','2.0.0','2018-04-28 20:28:16','http://amp.pharm.mssm.edu/Harmonizome/',NULL);
INSERT INTO `dataset` (name, source, app, app_version, datetime, url, comments) VALUES ('Harmonogram CDFs','IDG-KMC generated data by Steve Mathias at UNM.','load-HGramCDFs.py','2.1.0','2018-05-01 18:14:38',NULL,'CDFs are calculated by the loader app based on gene_attribute data in TCRD.');

INSERT INTO `provenance` (dataset_id, table_name) VALUES (63,'gene_attribute');
INSERT INTO `provenance` (dataset_id, table_name) VALUES (63,'gene_attribute_type');
INSERT INTO `provenance` (dataset_id, table_name) VALUES (64,'hgram_cdf');

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5.0.0.sql


## fix TIN-X
[smathias@juniper SQL]$ mysql tcrd5
mysql> \. create-TINX.sql
mysql> delete from provenance where dataset_id = 42;
mysql> delete from dataset where id = 42;

[smathias@juniper python]$ ./TIN-X.py --dbname tcrd5

TIN-X.py (v2.2.0) [Wed Jun  6 09:01:10 2018]:

Downloading https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/master/src/ontology/doid.obo
         to ../data/DiseaseOntology/doid.obo

Downloading http://download.jensenlab.org/disease_textmining_mentions.tsv
         to ../data/JensenLab/disease_textmining_mentions.tsv
Downloading http://download.jensenlab.org/human_textmining_mentions.tsv
         to ../data/JensenLab/human_textmining_mentions.tsv

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11210 Disease Ontology terms

Processing 20804 lines in protein file ../data/JensenLab/human_textmining_mentions.tsv
Progress: 100% [######################################################################] Time: 0:03:56
20804 lines processed.
  Skipped 2909 non-ENSP lines
  Saved 17878 protein to PMIDs mappings
  Saved 4837556 PMID to protein count mappings
WARNING: No target found for 189 ENSPs. See logfile ../loaders/tcrd5logs/TIN-X.py.log for details.

Processing 8560 lines in file ../data/JensenLab/disease_textmining_mentions.tsv
Progress: 100% [######################################################################] Time: 0:01:17
8560 lines processed.
  Skipped 1668 non-DOID lines
  Saved 6892 DOID to PMIDs mappings
  Saved 9788367 PMID to disease count mappings

Computing protein novely scores
  Wrote 17878 novelty scores to file ../data/TIN-X/TCRDv5/ProteinNovelty.csv

Computing disease novely scores
  Wrote 6892 novelty scores to file ../data/TIN-X/TCRDv5/DiseaseNovelty.csv

Computing importance scores
  Wrote 2420170 importance scores to file ../data/TIN-X/TCRDv5/Importance.csv

Computing PubMed rankings
  Wrote 38467556 PubMed rankings to file ../data/TIN-X/TCRDv5/PMIDRanking.csv

TIN-X.py: Done. Elapsed time: 2:04:51.172

[smathias@juniper loaders]$ ./load-TIN-X.py --dbname tcrd5

load-TIN-X.py (v2.1.0) [Wed Jun  6 11:15:09 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.0)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11210 Disease Ontology terms

Processing 6865 lines in file ../data/TIN-X/TCRDv4/DiseaseNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:03
6864 lines processed.
  Inserted 6864 new tinx_disease rows
  Saved 6864 keys in dmap

Processing 17719 lines in file ../data/TIN-X/TCRDv4/ProteinNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:10
17718 lines processed.
  Inserted 17718 new tinx_novelty rows

Processing 2307335 lines in file ../data/TIN-X/TCRDv4/Importance.csv
Progress: 100% [######################################################################] Time: 0:23:44
2307334 lines processed.
  Inserted 2307334 new tinx_importance rows
  Saved 2307334 keys in imap

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd5.0.0.sql

Removed on duplicate dataset/provenance row.
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.0.1.sql


## fix TIN-X
## loaded the v4 files last time
[smathias@juniper SQL]$ mysql tcrd5
mysql> \. create-TINX.sql
mysql> delete from provenance where dataset_id = 65;
mysql> delete from dataset where id = 65;

[smathias@juniper loaders]$ ./load-TIN-X.py --dbname tcrd5

load-TIN-X.py (v2.1.0) [Mon Jun 11 10:45:46 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.1)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 11210 Disease Ontology terms

Processing 6893 lines in file ../data/TIN-X/TCRDv5/DiseaseNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:03
6892 lines processed.
  Inserted 6892 new tinx_disease rows
  Saved 6892 keys in dmap

Processing 17879 lines in file ../data/TIN-X/TCRDv5/ProteinNovelty.csv
Progress: 100% [######################################################################] Time: 0:00:11
17878 lines processed.
  Inserted 17878 new tinx_novelty rows

Processing 2420171 lines in file ../data/TIN-X/TCRDv5/Importance.csv
Progress: 100% [######################################################################] Time: 0:24:21
2420170 lines processed.
  Inserted 2420170 new tinx_importance rows
  Saved 2420170 keys in imap

Processing 38467557 lines in file ../data/TIN-X/TCRDv5/PMIDRanking.csv
Progress: 100% [######################################################################] Time: 6:11:12
38467556 lines processed.
  Inserted 38467556 new tinx_articlerank rows

load-TIN-X.py: Done. Elapsed time: 6:35:54.536

mysql> update dbinfo set data_ver = '5.0.2';

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.0.2.sql

Comment out xrefs part of load-PubMed.py and run just TIN-X part:
[smathias@juniper loaders]$ ./load-PubMed.py --dbname tcrd5

load-PubMed.py (v2.1.0) [Tue Jun 12 13:21:01 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.2)

Checking for 2297443 TIN-X PubMed IDs in TCRD

Processing 155205 TIN-X PubMed IDs not in TCRD
Processed 155205 TIN-X PubMed IDs.
  Inserted 155197 new pubmed rows
WARNING: 8 DB errors occurred. See logfile ./tcrd5logs/load-PubMed.py.log for details.

load-PubMed.py: Done. Elapsed time: 3:14:38.332

mysql> update dbinfo set data_ver = '5.0.3';

[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.0.3.sql

## New DrugCentral
Drop and recreate drug_activity table.
mysql> delete from disease where dtype = 'DrugCentral Indication';
mysql> delete from provenance where dataset_id = 11;
mysql> delete from dataset where id = 11;

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd5

load-DrugCentral.py (v2.1.0) [Wed Jun 13 15:58:17 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.3)

Processing 1857 input lines in file ../data/DrugCentral/drug_info_06132018.tsv
1857 input lines processed.
Saved 1857 keys in infos map

Processing 3208 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_06132018.tsv
/home/app/TCRD/loaders/TCRD.py:653: Warning: Data truncated for column 'act_value' at row 1
  curs.execute(sql, tuple(params))
3208 DrugCentral Tclin rows processed.
  Inserted 3208 new drug_activity rows

Processing 678 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_06132018.tsv
678 DrugCentral Tchem rows processed.
  Inserted 678 new drug_activity rows

Processing 10935 lines from indications file ../data/DrugCentral/drug_indications_06132018.tsv
10935 DrugCentral indication rows processed.
  Inserted 12754 new target2disease rows
WARNNING: 1014 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:18.905

mysql> update target set tdl = NULL;
mysql> delete from provenance where dataset_id = 16;
mysql> delete from dataset where id = 16;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd5

load-TDLs.py (v2.1.0) [Wed Jun 13 16:05:53 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.2; data ver 5.0.3)

Processing 20244 TCRD targets
Progress: 100% [#####################################################################] Time: 0:24:32
20244 TCRD targets processed.
Set TDL values for 20244 targets:
  612 targets are Tclin
  1885 targets are Tchem
  11178 targets are Tbio - 857 bumped from Tdark
  6569 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:24:32.119

## Get rid of Grant Info
mysql> drop table `grant`;
mysql> delete from tdl_info where itype = "NIHRePORTER 2000-2017 R01 Count";
mysql> delete from info_type where name = "NIHRePORTER 2000-2017 R01 Count";

mysql> update dbinfo set schema_ver = '5.0.3', data_ver = '5.1.0';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.1.0.sql


## ChEMBL 24.1
drop and recreate chembl_activity table
mysql> delete from tdl_info where itype = 'ChEMBL First Reference Year';
mysql> delete from tdl_info where itype = 'ChEMBL Selective Compound';
mysql> delete from provenance where dataset_id in (12, 13);
mysql> delete from dataset where id in (12, 13);

[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd5 --loglevel 20

load-ChEMBL.py (v2.2.0) [Tue Jun 19 11:27:58 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.3; data ver 5.1.0)

Processing 10446 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
10446 input lines processed.

Processing 8286 UniProt to ChEMBL ID(s) mappings
Progress: 100% [#####################################################################] Time: 0:37:30
8286 UniProt accessions processed.
  0 targets not found in ChEMBL
  1808 targets have no good activities in ChEMBL
Inserted 360968 new chembl_activity rows
Inserted 1743 new ChEMBL First Reference Year tdl_infos
WARNING: 5 database errors occured. See logfile ./tcrd5logs/load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 16636 selective compounds
Inserted 730 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 0:38:10.191

mysql> update target set tdl = NULL;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd5

load-TDLs.py (v2.1.0) [Wed Jun 20 09:50:34 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.3; data ver 5.1.0)

Processing 20244 TCRD targets
Progress: 100% [#####################################################################] Time: 0:25:19
20244 TCRD targets processed.
Set TDL values for 20244 targets:
  612 targets are Tclin
  1388 targets are Tchem
  11651 targets are Tbio - 871 bumped from Tdark
  6593 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:25:19.892

mysql> update dbinfo set data_ver = '5.2.0';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.2.0.sql


#
# New DrugCentral
# Add drug ids for lookup from Pharos
mysql> delete from drug_activity;
mysql> ALTER TABLE drug_activity AUTO_INCREMENT = 1;
mysql> delete from disease where dtype = 'DrugCentral Indication';
mysql> delete from provenance where dataset_id = 67;
mysql> delete from dataset where id = 67;
mysql> ALTER TABLE drug_activity ADD COLUMN dcid int(11) NOT NULL DEFAULT 0;

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd5

load-DrugCentral.py (v2.2.0) [Thu Oct 18 09:59:43 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.3; data ver 5.2.0)

Processing 4531 input lines in file ../data/DrugCentral/drug_name_id_10122018.tsv
4531 input lines processed.
Saved 4531 keys in infos map

Processing 1866 input lines in file ../data/DrugCentral/drug_info_10122018.tsv
1866 input lines processed.
Saved 1866 keys in infos map

Processing 3219 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_10122018.tsv
/home/app/TCRD/loaders/TCRD.py:653: Warning: Data truncated for column 'act_value' at row 1
  curs.execute(sql, tuple(params))
3219 DrugCentral Tclin rows processed.
  Inserted 3205 new drug_activity rows
WARNNING: DrugCentral ID not found for 14 drug names. See logfile ./tcrd5logs/load-DrugCentral.py.log for details.

Processing 663 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_10122018.tsv
663 DrugCentral Tchem rows processed.
  Inserted 662 new drug_activity rows
WARNNING: DrugCentral ID not found for 1 drug names. See logfile ./tcrd5logs/load-DrugCentral.py.log for details.

Processing 10958 lines from indications file ../data/DrugCentral/drug_indications_10122018.tsv
10958 DrugCentral indication rows processed.
  Inserted 12671 new target2disease rows
WARNNING: 1036 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:59.475

mysql> update target set tdl = NULL;
mysql> delete from provenance where dataset_id = 75;
mysql> delete from dataset where id = 75;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd5

load-TDLs.py (v2.1.0) [Thu Oct 18 10:22:43 2018]:

Connected to TCRD database tcrd5 (schema ver 5.0.3; data ver 5.2.0)

Processing 20244 TCRD targets
Progress: 100% [######################################################################] Time: 3:22:49
20244 TCRD targets processed.
Set TDL values for 20244 targets:
  613 targets are Tclin
  1386 targets are Tchem
  11652 targets are Tbio - 871 bumped from Tdark
  6593 targets are Tdark

load-TDLs.py: Done. Elapsed time: 3:22:50.068

mysql> UPDATE dbinfo SET schema_ver = '5.0.4', data_ver = '5.3.0';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.3.0.sql



CREATE TABLE `cmpd_activity_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
INSERT INTO cmpd_activity_type (name, description) VALUES ('ChEMBL', 'A manually curated chemical database of bioactive molecules with drug-like properties. It is maintained by the European Bioinformatics Institute (EBI), of the European Molecular Biology Laboratory (EMBL), based at the Wellcome Trust Genome Campus, Hinxton, UK.');
INSERT INTO cmpd_activity_type (name, description) VALUES ('Guide to Pharmacology', 'The IUPHAR/BPS Guide to PHARMACOLOGY');
DROP TABLE IF EXISTS `chembl_activity`;
CREATE TABLE `cmpd_activity` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) DEFAULT NULL,
  `catype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `cmpd_id_in_src` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `cmpd_name_in_src` text COLLATE utf8_unicode_ci,
  `smiles` text COLLATE utf8_unicode_ci,
  `act_value` decimal(10,8) DEFAULT NULL,
  `act_type` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `reference` text COLLATE utf8_unicode_ci,
  `pubmed_ids` text DEFAULT NULL,
  `cmpd_pubchem_cid` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cmpd_activity_idx1` (`catype`),
  CONSTRAINT `fk_cmpd_activity__cmpd_activity_type` FOREIGN KEY (`catype`) REFERENCES `cmpd_activity_type` (`name`),
  KEY `cmpd_activity_idx2` (`target_id`),
  CONSTRAINT `fk_chembl_activity__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

mysql> delete from tdl_info where itype = 'ChEMBL First Reference Year';
mysql> delete from tdl_info where itype = 'ChEMBL Selective Compound';
mysql> delete from provenance where dataset_id in (72, 73);
mysql> delete from dataset where id in (72, 73);

[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd5 --loglevel 20

load-ChEMBL.py (v3.0.0) [Thu Oct 25 11:13:22 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done.

Connected to TCRD database tcrd5 (schema ver 5.0.4; data ver 5.3.0)

Processing 10446 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
10446 input lines processed.

Processing 8286 UniProt to ChEMBL ID(s) mappings
Progress: 100% [########################################################################] Time: 1:22:02
8286 UniProt accessions processed.
  0 targets not found in ChEMBL
  1808 targets have no good activities in ChEMBL
Inserted 360968 new chembl_activity rows
Inserted 1743 new ChEMBL First Reference Year tdl_infos
WARNING: 5 database errors occured. See logfile ./tcrd5logs/load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 16636 selective compounds
Inserted 730 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 1:27:38.025

mysql> UPDATE dbinfo SET schema_ver = '5.1.0', data_ver = '5.3.1';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.3.1.sql

mysql> delete from provenance where dataset_id = 59;
mysql> delete from dataset where id = 59;

[smathias@juniper loaders]$ ./load-PubChemCIDs.py --dbname tcrd5

load-PubChemCIDs.py (v1.1.0) [Fri Oct 26 12:06:55 2018]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/wholeSourceMapping/src_id1/src1src22.txt.gz
         to  ../data/ChEMBL/UniChem/src1src22.txt.gz
Uncompressing ../data/ChEMBL/UniChem/src1src22.txt.gz
Done. Elapsed time: 0:00:06.498

Connected to TCRD database tcrd5 (schema ver 5.1.0; data ver 5.3.1)

Processing 1763296 lines in file ../data/ChEMBL/UniChem/src1src22.txt
Got 1742944 ChEMBL to PubChem mappings

Loading PubChem CIDs for 360968 ChEMBL activities
Progress: 100% [########################################################################] Time: 0:09:46
360968 ChEMBL activities processed.
  Inserted 337599 new PubChem CIDs
  15629 ChEMBL IDs not found. See logfile ./tcrd5logs/load-PubChemCIDs.py.log for details.

Loading PubChem CIDs for 3867 drug activities
Progress: 100% [########################################################################] Time: 0:00:05
3867 drug activities processed.
  Inserted 2893 new PubChem CIDs
  Skipped 687 drug activities with no ChEMBL ID
  172 ChEMBL IDs not found. See logfile ./tcrd5logs/load-PubChemCIDs.py.log for details.

load-PubChemCIDs.py: Done. Elapsed time: 0:11:27.355

mysql> UPDATE dbinfo SET data_ver = '5.3.2';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.3.2.sql

[smathias@juniper loaders]$ ./load-GuideToPharmacology.py --dbname tcrd5

load-GuideToPharmacology.py (v1.0.0) [Mon Oct 29 13:01:01 2018]:

Downloading  http://www.guidetopharmacology.org/DATA/ligands.csv
         to  ../data/GuideToPharmacology/ligands.csv
Downloading  http://www.guidetopharmacology.org/DATA/interactions.csv
         to  ../data/GuideToPharmacology/interactions.csv

Connected to TCRD database tcrd5 (schema ver 5.1.0; data ver 5.3.2)

Processing 9406 lines in input file ../data/GuideToPharmacology/ligands.csv
  Got info for 7057 ligands
  Skipped 2348 antibodies/peptides

Processing 18177 lines in input file ../data/GuideToPharmacology/interactions.csv
Progress: 100% [########################################################################] Time: 0:00:59
18177 rows processed.
  Inserted 10705 new cmpd_activity rows for 1297 targets
  Skipped 0 with below cutoff activity values
  Skipped 2421 activities with multiple targets
  Skipped 3727 antibody/peptide activities
  Skipped 3648 activities with missing data
No target found for 17 uniprots/symbols. See logfile ./tcrd5logs/load-GuideToPharmacology.py.log for details.

load-GuideToPharmacology.py: Done. Elapsed time: 0:01:17.164

mysql> select count(*) from target where tdl IN ('Tbio', 'Tdark') and id IN (select distinct target_id from cmpd_activity where catype = 'Guide to Pharmacology');
+----------+
| count(*) |
+----------+
|      212 |
+----------+
mysql> select p.name, p.description, t.tdl, p.sym, p.uniprot from target t, protein p where t.id = p.id and t. tdl IN ('Tbio', 'Tdark') and t.id IN (select distinct target_id from cmpd_activity where catype = 'Guide to Pharmacology') into outfile '/tmp/IUPHAR_Tchems.csv' FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';

mysql> UPDATE dbinfo SET data_ver = '5.3.3';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.3.3.sql

mysql> update target set tdl = NULL;
mysql> delete from provenance where dataset_id = 77;
mysql> delete from dataset where id = 77;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd5

load-TDLs.py (v2.1.0) [Tue Oct 30 11:08:53 2018]:

Connected to TCRD database tcrd5 (schema ver 5.1.0; data ver 5.3.3)

Processing 20244 TCRD targets
Progress: 100% [########################################################################] Time: 3:04:55
20244 TCRD targets processed.
Set TDL values for 20244 targets:
  613 targets are Tclin
  1598 targets are Tchem
  11445 targets are Tbio - 871 bumped from Tdark
  6588 targets are Tdark

load-TDLs.py: Done. Elapsed time: 3:04:55.420

mysql> UPDATE dbinfo SET data_ver = '5.4.0';
[smathias@juniper SQL]$ mysqldump tcrd5 > dumps5/tcrd_v5.4.0.sql




mysql> select tcrd5.dataset.name from tcrd5.dataset where tcrd5.dataset.name not in (select tcrd410.dataset.name from tcrd410.dataset);
+---------------------------------------+
| name                                  |
+---------------------------------------+
| Monarch Disease Associations          |
| CTD Disease Associations              |
| Cell Surface Protein Atlas            |
| Human Cell Atlas Expression           |
| Human Cell Atlas Compartments         |
| NIH Grant Textmining Info             |
| Orthologs                             |
| Monarch Ortholog Disease Associations |
| Transcription Factor Flags            |
| IMPC Mouse Clones                     |
| LocSigDB                              |
| PANTHER protein classes               |
| PubChem CIDs                          |
| GeneRIF Years                         |
+---------------------------------------+


mysql> select protein_id, name, count(*) from pathway where pwtype = 'Reactome' group by protein_id, name limit 10;
+------------+-----------------------------------------------------+----------+
| protein_id | name                                                | count(*) |
+------------+-----------------------------------------------------+----------+
|          1 | Activation of BAD and translocation to mitochondria |        1 |
|          1 | Activation of BH3-only proteins                     |        1 |
|          1 | Anchoring of the basal body to the plasma membrane  |        1 |
|          1 | Apoptosis                                           |        1 |
|          1 | AURKA Activation by TPX2                            |        1 |
|          1 | Cell Cycle                                          |        1 |
|          1 | Cell Cycle Checkpoints                              |        1 |
|          1 | Cell Cycle, Mitotic                                 |        1 |
|          1 | Cell death signalling via NRAGE, NRIF and NADE      |        1 |
|          1 | Cellular response to heat stress                    |        1 |
+------------+-----------------------------------------------------+----------+
10 rows in set (0.94 sec)

mysql> select protein_id, name, count(*) c from pathway where pwtype = 'Reactome' group by protein_id, name having c > 1;
Empty set (0.74 sec)

mysql> select count(distinct protein_id, name) from pathway where pwtype = 'Reactome';
+----------------------------------+
| count(distinct protein_id, name) |
+----------------------------------+
|                           104072 |
+----------------------------------+
