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
UPDATE target set fam = 'GPCR', famext = 'GPCR' WHERE id = 12007;
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
  Skipped 248752 aliases that would override reviewed mappings . See logfile load-STRINGIDs.py.log for details.

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


