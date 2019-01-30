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
DELETE FROM xref_type where name NOT IN ('UniProt Keyword', 'NCBI GI', 'HGNC', 'MGI ID', 'Ensembl', 'STRING', 'DrugBank', 'BRENDA', 'ChEMBL', 'MIM', 'PANTHER', 'PDB', 'UniGene', 'InterPro', 'Pfam', 'PROSITE', 'SMART');
[smathias@juniper SQL]$ mysqldump tcrd6 > create-TCRDv6.sql

New tables and changes to support metapath are in SQL/tcrdmp.sql
mysql> \. tcrdmp.sql


[smathias@juniper loaders]$ ./load-UniProt.py --dbname tcrd6 --loglevel 20

load-UniProt.py (v3.1.0) [Thu Jan 10 10:43:02 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing Evidence Ontology file ../data/eco.obo

Parsing file ../data/UniProt/uniprot-reviewed-human_20190103.xml
Loading data for 20412 UniProt records
Progress: 100% [######################################################################] Time: 0:34:51
Processed 20412 UniProt records. Elapsed time: 0:36:49.152
  Loaded 20412 targets/proteins

Parsing file ../data/UniProt/uniprot-mouse_20190103.xml
Loading data for 85187 UniProt records
Progress: 100% [######################################################################] Time: 0:31:24
Processed 85187 UniProt records. Elapsed time: 0:34:16.119
  Loaded 85187 nhproteins

Parsing file ../data/UniProt/uniprot-rat_20190103.xml
Loading data for 36090 UniProt records
Progress: 100% [######################################################################] Time: 0:09:40
Processed 36090 UniProt records. Elapsed time: 0:11:15.685
  Loaded 36090 nhproteins

load-UniProt.py: Done. Total elapsed time: 1:23:06.699

Some UniProt records have multiple Gene IDs. The loader takes the first
one, but this is not always the right one. So manual fixes to Gene IDs:
mysql> \. update_geneids.sql

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-1.sql


# HGNC
[smathias@juniper loaders]$ ./load-HGNC.py --dbname tcrd6 --loglevel 20

load-HGNC.py (v3.0.0) [Thu Jan 10 12:08:07 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 41618 lines in file ../data/HGNC/HGNC_20190104.tsv
Progress: 100% [######################################################################] Time: 3:46:32
Processed 41618 lines - 20205 targets annotated.
No target found for 21397 lines.
  Inserted 20373 HGNC ID xrefs
  Inserted 20373 MGI ID xrefs
WARNING: 244 discrepant HGNC symbols. See logfile ./tcrd6logs/load-HGNC.py.log for details
  Added 1196 new NCBI Gene IDs
WARNING: 200 discrepant NCBI Gene IDs. See logfile ./tcrd6logs/load-HGNC.py.log for details

load-HGNC.py: Done. Elapsed time: 3:46:32.686


[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-2.sql


# GIs
[smathias@juniper loaders]$ ./load-GIs.py --dbname tcrd6

load-GIs.py (v2.2.0) [Fri Jan 11 09:40:20 2019]:

Downloading  ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping_selected.tab.gz
         to  ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Uncompressing ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Done. Elapsed time: 0:00:32.248

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 177579 rows in file ../data/UniProt/HUMAN_9606_idmapping_selected.tab
Progress: 100% [######################################################################] Time: 0:11:31

177579 rows processed
  Inserted 257166 new GI xref rows for 20408 targets
  Skipped 157171 rows with no GI

load-GIs.py: Done. Elapsed time: 0:11:32.255

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-3.sql


# ENSGs
[smathias@juniper loaders]$ ./load-ENSGs.py --dbname tcrd6

load-ENSGs.py (v1.0.0) [Mon Jan 14 17:18:27 2019]:

Parsing file ../data/UniProt/uniprot-rat_20190103.xml
Processing 36090 UniProt records
Progress: 100% [######################################################################] Time: 0:03:35
Parsing file ../data/UniProt/uniprot-mouse_20190103.xml
Processing 85187 UniProt records
Progress: 100% [######################################################################] Time: 0:17:47
Parsing file ../data/UniProt/uniprot-reviewed-human_20190103.xml
Processing 20412 UniProt records
Progress: 100% [######################################################################] Time: 0:01:21
Now have 98655 UniProt to ENSG mappings.

Processing 29366 lines in file ../data/Ensembl/Rattus_norvegicus.Rnor_6.0.94.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:00
Processing 68769 lines in file ../data/Ensembl/Mus_musculus.GRCm38.94.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:02
Processing 115384 lines in file ../data/Ensembl/Homo_sapiens.GRCh38.94.uniprot.tsv
Progress: 100% [######################################################################] Time: 0:00:03
Now have 146382 UniProt to ENSG mappings.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:01:57
20412 targets processed
  Inserted 21608 new ENSG xref rows for 19452 proteins
  No ENSG found for 960 UniProt accessions. See logfile ./tcrd6logs/load-ENSGs.py.log for details.

Processing 121277 TCRD nhproteins
Progress: 100% [######################################################################] Time: 0:02:31
121277 nhproteins processed
  Inserted 56226 new ENSG xref rows for 55313 nhproteins
  No ENSG found for 65964 UniProt accessions. See logfile ./tcrd6logs/load-ENSGs.py.log for details.

load-ENSGs.py: Done. Elapsed time: 0:33:36.063

[smathias@juniper SQL]$ mysqldump --opt tcrd6 > dumps6/tcrd6-5.sql


# NCBI Gene
mysql> INSERT INTO xref_type (name) VALUES ('PubMed');

[smathias@juniper loaders]$ ./load-NCBIGene.py --dbname tcrd6 --loglevel 20

load-NCBIGene.py (v2.2.0) [Tue Jan 15 11:06:40 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading NCBI Gene annotations for 20412 TCRD targets
Progress: 100% [###############################################################] Time: 1 day, 5:35:55
Processed 20412 targets.
Skipped 259 targets with no geneid
Loaded NCBI annotations for 20149 targets
Total targets remaining for retries: 4 

Retry loop 1: Loading NCBI Gene annotations for 4 TCRD targets
Progress: 100% [######################################################################] Time: 0:05:27
Processed 4 targets.
  Annotated 4 additional targets
  Total annotated targets: 20153

Inserted 53714 aliases
Inserted 12899 NCBI Gene Summary tdl_infos
Inserted 20153 NCBI Gene PubMed Count tdl_infos
Inserted 730862 GeneRIFs
Inserted 1194657 PubMed xrefs
WARNNING: 4 XML parsing errors occurred. See logfile ./tcrd6logs/load-NCBIGene.py.log for details.

load-NCBIGene.py: Done. Elapsed time: 29:41:22.865

fix for string ids:
mysql> update protein set stringid = 'ENSP00000366005' where sym = 'HLA-A';

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-6.sql


# DrugCentral
[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd6

load-DrugCentral.py (v2.3.0) [Thu Jan 17 14:25:18 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 4531 input lines in file ../data/DrugCentral/drug_name_id_10122018.tsv
4531 input lines processed.
Saved 4531 keys in infos map

Processing 1866 input lines in file ../data/DrugCentral/drug_info_10122018.tsv
1866 input lines processed.
Saved 1866 keys in infos map

Processing 3219 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_10122018.tsv
/home/app/TCRD/loaders/TCRDMP.py:683: Warning: Data truncated for column 'act_value' at row 1
  curs.execute(sql, tuple(params))
3219 DrugCentral Tclin rows processed.
  Inserted 3205 new drug_activity rows
WARNNING: DrugCentral ID not found for 14 drug names. See logfile ./tcrd6logs/load-DrugCentral.py.log for details.

Processing 663 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_10122018.tsv
663 DrugCentral Tchem rows processed.
  Inserted 662 new drug_activity rows
WARNNING: DrugCentral ID not found for 1 drug names. See logfile ./tcrd6logs/load-DrugCentral.py.log for details.

Processing 10958 lines from indications file ../data/DrugCentral/drug_indications_10122018.tsv
10958 DrugCentral indication rows processed.
  Inserted 12671 new target2disease rows
WARNNING: 1036 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:56.691

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-9.sql


# Antibodypedia
[smathias@juniper loaders]$ ./load-Antibodypedia.py --dbname tcrd6

load-Antibodypedia.py (v2.2.0) [Thu Jan 17 16:19:07 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Loading Antibodypedia annotations for 20412 TCRD targets
Progress: 100% [#####################################################################] Time: 18:09:38
20412 TCRD targets processed.
  Inserted 20321 Ab Count tdl_info rows
  Inserted 20321 MAb Count tdl_info rows
  Inserted 20321 Antibodypedia.com URL tdl_info rows
WARNING: Network error for 91 targets. See logfile ./tcrd6logs/load-Antibodypedia.py.log for details.

load-Antibodypedia.py: Done. Elapsed time: 18:09:38.366

There was an internet outage which caused the errors. So fix:
[smathias@juniper tcrd6logs]$ perl -ne '/uniprot=(.+) \[Target (\d+)/ && print "$1 $2\n"' load-Antibodypedia.py.log > Abp-Missing.txt

[smathias@juniper loaders]$ ./load-AntibodypediaList.py --dbname tcrd6

load-AntibodypediaList.py (v1.0.0) [Fri Jan 18 11:43:51 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Got 91 UniProt accessions from file tcrd6logs/Abp-Missing.txt

Loading Antibodypedia annotations for 91 targets
Progress: 100% [######################################################################] Time: 0:03:15
91 TCRD targets processed.
  Inserted 91 Ab Count tdl_info rows
  Inserted 91 MAb Count tdl_info rows
  Inserted 91 Antibodypedia.com URL tdl_info rows

load-AntibodypediaList.py: Done. Elapsed time: 0:03:15.270

mysql> select count(*) from tdl_info where itype = 'Ab Count';
+----------+
| count(*) |
+----------+
|    20412 |
+----------+

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-10.sql


# ChEMBL
[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd6 --loglevel 20

load-ChEMBL.py (v3.1.0) [Fri Jan 18 11:56:41 2019]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 10446 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
10446 input lines processed.

Processing 8286 UniProt to ChEMBL ID(s) mappings
Progress: 100% [######################################################################] Time: 1:00:53
8286 UniProt accessions processed.
  1760 targets have no qualifying TCRD activities in ChEMBL
Inserted 489802 new cmpd_activity rows
Inserted 1791 new ChEMBL First Reference Year tdl_infos
WARNING: 9 database errors occured. See logfile ./tcrd6logs/load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 17923 selective compounds
Inserted 755 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 1:08:56.095

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-11.sql


# GO Experimental and Functional Leaf terms
[smathias@juniper loaders]$ ./load-GOExptFuncLeafTDLIs.py --dbname tcrd6

load-GOExptFuncLeafTDLIs.py (v2.2.0) [Fri Jan 18 14:16:34 2019]:

Downloading  http://www.geneontology.org/ontology/go.obo
         to  ../data/GO/go.obo
Done.

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:38:33
20412 TCRD targets processed.
  Inserted 6976 new  tdl_info rows

load-GOExptFuncLeafTDLIs.py: Done. Elapsed time: 0:39:12.303

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-12.sql


# OMIM
[smathias@juniper loaders]$ ./load-OMIM.py --dbname tcrd6

load-OMIM.py (v2.2.0) [Tue Jan 22 12:36:50 2019]:

Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/genemap.txt
         to  ../data/OMIM/genemap.txt
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/mimTitles.txt
         to  ../data/OMIM/mimTitles.txt
Downloading  https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/phenotypicSeries.txt
         to  ../data/OMIM/phenotypicSeries.txt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 26125 lines from input file ../data/OMIM/mimTitles.txt
Progress: 100% [######################################################################] Time: 0:00:33
26125 lines processed
  Skipped 16 commented lines.
Loaded 26109 new omim rows

Processing 4235 lines from input file ../data/OMIM/phenotypicSeries.txt
Progress: 100% [######################################################################] Time: 0:00:05
4235 lines processed
  Skipped 3 commented lines.
Loaded 4232 new omim_ps rows

Processing 16997 lines from input file ../data/OMIM/genemap.txt
Progress: 100% [######################################################################] Time: 2:10:27
16997 lines processed
  Skipped 158 commented lines.
  Skipped 398 provisional phenotype rows.
  Skipped 140 deletion/duplication syndrome rows.
Loaded 14099 OMIM phenotypes for 13812 targets
No target found for 2735 good lines. See logfile ./tcrd6logs/load-OMIM.py.log for details.

load-OMIM.py: Done. Elapsed time: 2:11:07.114

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-13.sql


# GuideToPharmacology
[smathias@juniper loaders]$ ./load-GuideToPharmacology.py --dbname tcrd6

load-GuideToPharmacology.py (v1.0.0) [Thu Jan 24 11:16:42 2019]:

Downloading  http://www.guidetopharmacology.org/DATA/ligands.csv
         to  ../data/GuideToPharmacology/ligands.csv
Downloading  http://www.guidetopharmacology.org/DATA/interactions.csv
         to  ../data/GuideToPharmacology/interactions.csv

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 9406 lines in input file ../data/GuideToPharmacology/ligands.csv
  Got info for 7057 ligands
  Skipped 2348 antibodies/peptides

Processing 18177 lines in input file ../data/GuideToPharmacology/interactions.csv
Progress: 100% [######################################################################] Time: 0:01:03
18177 rows processed.
  Inserted 10706 new cmpd_activity rows for 1297 targets
  Skipped 0 with below cutoff activity values
  Skipped 2421 activities with multiple targets
  Skipped 3727 antibody/peptide activities
  Skipped 3648 activities with missing data
No target found for 16 uniprots/symbols. See logfile ./tcrd6logs/load-GuideToPharmacology.py.log for details.

load-GuideToPharmacology.py: Done. Elapsed time: 0:01:20.774

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-14.sql


# TDLs
[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v3.0.0) [Thu Jan 24 11:28:30 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:37:10
20412 TCRD targets processed.
Set TDL values for 20412 targets:
  613 targets are Tclin
  1627 targets are Tchem
  9894 targets are Tbio - 1219 bumped from Tdark
  8278 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:37:10.838

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-15.sql


# Check TCRD versus info in IDG list on GitHub
[smathias@juniper python]$ ./chk-TargetList.py --dbname tcrd6

chk-TargetList.py (v1.0.0) [Thu Jan 24 12:38:38 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Parsing input file ../data/IDG_TargetList_Y1.json

Processing 416 gene/family pairs
Progress: 100% [######################################################################] Time: 0:00:26
Processed 416
No target found for 5. See logfile ./chk-TargetList.py.log for details.
Family mismatch found for 4. See logfile ./chk-TargetList.py.log for details.

chk-TargetList.py: Done. Elapsed time: 0:00:26.723

[smathias@juniper python]$ cat chk-TargetList.py.log
2019-01-24 14:58:15 - __main__ - WARNING: No target found for ADGRE5
2019-01-24 14:58:23 - __main__ - WARNING: No target found for TAAR3
2019-01-24 14:58:27 - __main__ - WARNING: No target found for FAM26D
2019-01-24 14:58:27 - __main__ - WARNING: No target found for FAM26E
2019-01-24 14:58:27 - __main__ - WARNING: No target found for FAM26F
2019-01-24 14:58:31 - __main__ - WARNING: Family mismatch for target 2885: DB: None, List: IC
2019-01-24 14:58:31 - __main__ - WARNING: Family mismatch for target 2886: DB: None, List: IC
2019-01-24 14:58:31 - __main__ - WARNING: Family mismatch for target 1968: DB: None, List: IC
2019-01-24 14:58:34 - __main__ - WARNING: Family mismatch for target 5037: DB: Enzyme, List: Kinase

ADGRE5     CD97     P48960     CD97 is a previous symbol according to HGNC
TAAR3      TAAR3P   Q9P1P4     TAAR3 is a previous symbol according to HGNC
FAM26D     CALHM4   Q5JW98     FAM26D is no longer the approved symbol according to HGNC
FAM26E     CALHM5   Q8N5C1     FAM26E is no longer the approved symbol according to HGNC
FAM26F     CALHM6   Q5R3K3     FAM26F is no longer the approved symbol according to HGNC

target 2885: DB: None, List: IC       TMEM63A      O94886       IC
target 2886: DB: None, List: IC       TMEM63B      Q5T3F8       IC
target 1968: DB: None, List: IC       TMEM63C      Q9P1W3       IC
target 5037: DB: Enzyme, List: Kinase STK19        P49842       Kinase


# Redo IDG flags and fams
mysql> delete from provenance where dataset_id in (9,10);
mysql> delete from dataset where id in (9,10);
mysql> UPDATE target set idg2 = 0;
mysql> UPDATE target set fam = NULL, famext = NULL;

[smathias@juniper loaders]$ ./load-IDG2List.py --dbname tcrd6

load-IDG2List.py (v1.0.0) [Fri Jan 25 11:00:27 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 417 lines in list file ../data/IDG_TargetList_20190124.csv
Progress: 100% [######################################################################] Time: 0:00:30
417 lines processed
416 targets updated with IDG2 flags
416 targets updated with fams

load-IDG2List.py: Done. Elapsed time: 0:00:31.093

[smathias@juniper loaders]$ ./load-IDGFams.py --dbname tcrd6

# IDG Fams
File modified to v2 with following changes:
Q9NSE7 - obsolete; deleted
O60344 - obsolete; changed to P0DPD6
Q5T4J0 - obsolete; deleted
P0CW71 - obsolete; deleted
Q9NX53 - obsolete; changed to Q8N9H8

[smathias@juniper loaders]$ ./load-IDGFams.py --dbname tcrd6

load-IDGFams.py (v1.3.0) [Fri Jan 25 11:14:01 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 8147 lines in file ../data/IDG_Families_UNM_UMiami_v2.csv
Progress: 100% [######################################################################] Time: 0:01:04
8147 rows processed.
7731 IDG family designations loaded into TCRD.
5207 IDG extended family designations loaded into TCRD.
Skipped 415 IDG2 targets.

load-IDGFams.py: Done. Elapsed time: 0:01:04.690

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-16.sql


# STRING v11 released, so update stringids
mysql> delete from provenance where dataset_id = 6;
mysql> delete from dataset where id = 6;
mysql> update protein set stringid = NULL;

[smathias@juniper loaders]$ ./load-STRINGIDs.py --dbname tcrd6

load-STRINGIDs.py (v2.7.0) [Mon Jan 28 12:12:24 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 19184 input lines in file ../data/JensenLab/human.uniprot_2_string.2018.tsv
Progress: 100% [######################################################################] Time: 0:00:00
19184 input lines processed.
  Skipped 1877 non-identity lines
  Got 34612 uniprot/name to STRING ID mappings

Processing 2224813 input lines in file ../data/JensenLab/9606.protein.aliases.v11.0.txt
Progress: 100% [######################################################################] Time: 0:01:35
2224813 input lines processed.
  Added 2137567 alias to STRING ID mappings
  Skipped 52633 aliases that would override reviewed mappings. See logfile ./tcrd6logs/load-STRINGIDs.py.log for details.

Loading STRING IDs for 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:36:53
Updated 19121 STRING ID values
No stringid found for 1291 proteins. See logfile ./tcrd6logs/load-STRINGIDs.py.log for details.

load-STRINGIDs.py: Done. Elapsed time: 0:38:35.083

mysql> select p.id, p.name, p.sym, p.uniprot, p.stringid, x.value from protein p, xref x where p.id = x.protein_id and x.xtype = 'STRING' and concat('9606.', p.stringid) != x.value;
...
3182 rows

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-17.sql

# and PubMed Scores
mysql> delete from tdl_info where itype = 'JensenLab PubMed Score';
[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd6

load-JensenLabPubMedScores.py (v2.2.0) [Tue Jan 29 13:08:14 2019]:

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:03.954

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 386754 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [######################################################################] Time: 1:42:31
386754 input lines processed.
  Inserted 366587 new pmscore rows for 17559 targets
No target found for 515 STRING IDs. See logfile ./tcrd6logs/load-JensenLabPubMedScores.py.log for details.

Loading 17559 JensenLab PubMed Score tdl_infos
17559 processed
  Inserted 17559 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done. Elapsed time: 1:43:02.849

mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/tmp/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';
Edit that to create InsMissingJLPMSs_TCRDv6.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /tmp/nojlpms.csv > InsZeroJLPMSs_TCRDv6.sql
Edit InsZeroJLPMSs_TCRDv6.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv6.sql

[smathias@juniper SQL]$ mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-18.sql

# and TDLs
mysql> delete from provenance where dataset_id = 18;
mysql> delete from dataset where id = 18;
mysql> update target set TDL = NULL;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v3.0.0) [Tue Jan 29 15:36:16 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:36:51
20412 TCRD targets processed.
Set TDL values for 20412 targets:
  613 targets are Tclin
  1627 targets are Tchem
  11630 targets are Tbio - 622 bumped from Tdark
  6542 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:36:51.340

mysqldump --single-transaction --extended-insert tcrd6 > dumps6/tcrd6-19.sql





# PPIs
# STRINGDB
mysql> ALTER TABLE ppi ADD COLUMN score int() DEFAULT NULL;






