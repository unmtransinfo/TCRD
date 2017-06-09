mysql> select d.id, d.name, p.table_name, p.column_name, p.where_clause from dataset d, provenance p where d.id = p.dataset_id and d.name like '%Jensen%';
+----+-------------------------------------+-------------+-------------+----------------------------------+
| id | name                                | table_name  | column_name | where_clause                     |
+----+-------------------------------------+-------------+-------------+----------------------------------+
|  9 | JensenLab STRING IDs                | protein     | stringid    | NULL                             |
| 12 | JensenLab PubMed Text-mining Scores | pmscore     | NULL        | NULL                             |
| 12 | JensenLab PubMed Text-mining Scores | tdl_info    | NULL        | itype = 'JensenLab PubMed Score' |
| 19 | Jensen Lab DISEASES                 | disease     | NULL        | dtype LIKE 'JensenLab %'         |
| 28 | Jensen Lab TISSUES                  | expression  | NULL        | etype LIKE 'JensenLab %'          |
| 36 | Jensen Lab COMPARTMENTS             | compartment | NULL        | NULL                             |
+----+-------------------------------------+-------------+-------------+----------------------------------+

# STRING IDs
delete from provenance where dataset_id = 9;
delete from dataset where id = 9;
update protein set stringid = NULL;

[smathias@juniper loaders]$ ./load-STRINGIDs.py --dbname tcrd4

load-STRINGIDs.py (v2.2.0) [Wed Feb 22 09:48:01 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.2.1)

Processing 20499 input lines in file ../data/JensenLab/9606_reviewed_uniprot_2_string.04_2015.tsv
Progress: 100% [#################################################################] Time: 0:00:00
20499 input lines processed. Elapsed time: 0:00:00.082
  Skipped 2397 non-identity lines
  Got 35046 uniprot/name to STRING ID mappings

Processing 2449433 input lines in file ../data/JensenLab/9606.protein.aliases.v10.txt
Progress: 100% [#################################################################] Time: 0:00:06
2449433 input lines processed. Elapsed time: 0:00:07.000
  Got 2166722 alias to STRING ID mappings
  Skipped 248752 aliases that would override reviewed mappings . See logfile load-STRINGIDs.py.log for details.

Loading STRING IDs for 20120 TCRD targets
Progress: 100% [######################################################################] Time: 0:24:04
Updated 19267 STRING ID values

load-STRINGIDs.py: Done.

mysql> update protein set stringid = 'ENSP00000366005' where sym = 'HLA-A';


# PubMed Scores
delete from provenance where dataset_id = 12;
delete from dataset where id = 12;
delete from pmscore;
ALTER TABLE pmscore AUTO_INCREMENT = 1;
delete from tdl_info where itype = 'JensenLab PubMed Score';

[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd4

load-JensenLabPubMedScores.py (v2.0.0) [Wed Feb 22 11:51:16 2017]:

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:06.163

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.3.0)

Processing 356729 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [######################################################################] Time: 0:04:36
356729 input lines processed. Elapsed time: 0:04:36.353
  17607 targets have JensenLab PubMed Scores
  Inserted 345579 new pmscore rows
No target found for 337 STRING IDs. Saved to file: tcrd4logs/protein_counts_not-found.db

Loading 17607 JensenLab PubMed Score tdl_infos
  17607 processed
  Inserted 17607 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done.

mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/tmp/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';
Edit that to create InsMissingJLPMSs_TCRDv4.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /tmp/nojlpms.csv > InsZeroJLPMSs_TCRDv4.sql
Edit InsZeroJLPMSs_TCRDv4.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv4.sql


# TDLs
update target set tdl = NULL;
 
[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd4

load-TDLs.py (v2.0.0) [Wed Feb 22 11:59:46 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.3.0)

Processing 20120 TCRD targets
Progress: 100% [######################################################################] Time: 0:24:09
20120 TCRD targets processed. Elapsed time: 0:24:09.317
Set TDL values for 20120 targets
  598 targets are Tclin
  1405 targets are Tchem
  11086 targets are Tbio (836 bumped from Tdark)
  7031 targets are Tdark

load-TDLs.py: Done.


# DISEASES
delete from provenance where dataset_id = 19;
delete from dataset where id = 19;
delete from disease where dtype LIKE 'JensenLab %';

[smathias@juniper loaders]$ ./load-JensenLab-DISEASES.py --dbname tcrd4

load-JensenLab-DISEASES.py (v2.0.0) [Wed Feb 22 12:36:32 2017]:

Downloading  http://download.jensenlab.org/human_disease_knowledge_filtered.tsv
         to  ../data/JensenLab/human_disease_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_experiments_filtered.tsv
         to  ../data/JensenLab/human_disease_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_disease_textmining_filtered.tsv
         to  ../data/JensenLab/human_disease_textmining_filtered.tsv

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.3.0)

Processing 4680 lines in file ../data/JensenLab/human_disease_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:00:49
4680 lines processed. Elapsed time: 0:00:49.485
  2743 targets have disease association(s)
  Inserted 4952 new disease rows
No target found for 6 disease association rows. See shelve file: tcrd4logs/load-JensenLab-DISEASES.db

Processing 23987 line in file ../data/JensenLab/human_disease_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 0:01:25
23987 lines processed. Elapsed time: 0:01:25.421
  Skipped 16106 zero confidence rows
  4695 targets have disease association(s)
  Inserted 7476 new disease rows
No target found for 171 disease association rows. See shelve file: tcrd4logs/load-JensenLab-DISEASES.db

Processing 44513 lines in file ../data/JensenLab/human_disease_textmining_filtered.tsv
Progress: 100% [######################################################################] Time: 0:07:52
44513 lines processed. Elapsed time: 0:07:52.783
  11835 targets have disease association(s)
  Inserted 44413 new disease rows
No target found for 890 disease association rows. See shelve file: tcrd4logs/load-JensenLab-DISEASES.db

load-JensenLab-DISEASES.py: Done.


# TISSUES
delete from provenance where dataset_id = 28;
delete from dataset where id = 28;
delete from expression where etype LIKE 'JensenLab %';

[smathias@juniper loaders]$ ./load-JensenLabTISSUES.py --dbname tcrd4

load-JensenLabTISSUES.py (v2.0.0) [Wed Feb 22 12:56:20 2017]:

Downloading  http://download.jensenlab.org/human_tissue_knowledge_filtered.tsv
         to  ../data/JensenLab/human_tissue_knowledge_filtered.tsv
Downloading  http://download.jensenlab.org/human_tissue_experiments_filtered.tsv
         to  ../data/JensenLab/human_tissue_experiments_filtered.tsv
Downloading  http://download.jensenlab.org/human_tissue_textmining_filtered.tsv
         to  ../data/JensenLab/human_tissue_textmining_filtered.tsv

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.3.0)

Processing 63895 lines in input file ../data/JensenLab/human_tissue_knowledge_filtered.tsv
Progress: 100% [######################################################################] Time: 0:03:18
63895 rows processed. Elapsed time: 0:03:18.803
  16668 proteins have expression(s)
  Inserted 64843 new expression rows
No target found for 106 rows - keys saved to file: tcrd4logs/TISSUESk_not-found.db

Processing 1610815 lines in input file ../data/JensenLab/human_tissue_experiments_filtered.tsv
Progress: 100% [######################################################################] Time: 0:06:08
1610815 rows processed. Elapsed time: 0:06:09.040
  Skipped 1126329 zero confidence rows
  17445 proteins have expression(s)
  Inserted 491884 new expression rows
No target found for 243 rows. Saved to file: tcrd4logs/TISSUESe_not-found.db

Processing 57875 lines in input file ../data/JensenLab/human_tissue_textmining_filtered.tsv
Progress: 100% [######################################################################] Time: 0:00:45
57875 rows processed. Elapsed time: 0:00:45.293
  12254 proteins have expression(s)
  Inserted 57543 new expression rows
No target found for 1027 rows. Saved to file: tcrd4logs/TISSUEStm_not-found.db

load-JensenLabTISSUES.py: Done.

# COMPARTMENTS
delete from provenance where dataset_id = 29;
delete from dataset where id = 29;
delete from compartment;
ALTER TABLE compartment AUTO_INCREMENT = 1;

[smathias@juniper loaders]$ ./load-JensenLabCOMPARTMNTS.py --dbname tcrd4

load-JensenLabCOMPARTMNTS.py (v2.0.0) [Wed Feb 22 14:40:24 2017]:

Downloading  http://download.jensenlab.org/human_compartment_knowledge_full.tsv
         to  ../data/JensenLab/human_compartment_knowledge_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_experiments_full.tsv
         to  ../data/JensenLab/human_compartment_experiments_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_textmining_full.tsv
         to  ../data/JensenLab/human_compartment_textmining_full.tsv
Downloading  http://download.jensenlab.org/human_compartment_predictions_full.tsv
         to  ../data/JensenLab/human_compartment_predictions_full.tsv

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.3.0)

Processing 640195 lines in input file ../data/JensenLab/human_compartment_knowledge_full.tsv
Progress: 100% [######################################################################] Time: 0:07:21
640195 rows processed. Elapsed time: 0:07:22.018
  Skipped 61507 rows with conf < 3
  17224 proteins have compartment(s)
  Inserted 609797 new compartment rows
No target found for 111 rows. See file: tcrd4logs/COMPARTMENTS_NotFound.db

Processing 119761 lines in input file ../data/JensenLab/human_compartment_experiments_full.tsv
Progress: 100% [######################################################################] Time: 0:00:01
119761 rows processed. Elapsed time: 0:00:01.286
  Skipped 117697 rows with conf < 3
  197 proteins have compartment(s)
  Inserted 2112 new compartment rows

Processing 623865 lines in input file ../data/JensenLab/human_compartment_textmining_full.tsv
Progress: 100% [######################################################################] Time: 0:01:33
623865 rows processed. Elapsed time: 0:01:33.927
  Skipped 528978 rows with zscore < 3.0
  9623 proteins have compartment(s)
  Inserted 94487 new compartment rows
No target found for 331 rows. Saved to file: tcrd4logs/COMPARTMENTS_NotFound.db

Processing 414034 lines in input file ../data/JensenLab/human_compartment_predictions_full.tsv
Progress: 100% [######################################################################] Time: 0:00:28
414034 rows processed. Elapsed time: 0:00:28.125
  Skipped 387715 rows with conf < 3
  10079 proteins have compartment(s)
  Inserted 26127 new compartment rows
No target found for 233 rows. Saved to file: tcrd4logs/COMPARTMENTS_NotFound.db

load-JensenLabCOMPARTMNTS.py: Done.


# Grant Info
grant_tagger.py (v2.0.0) [Wed Feb 15 15:15:25 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.1; data ver 4.2.0)

Loading project info from pickle file ../data/NIHExporter/ProjectInfo2000-2015.p

Creating Tagger...

Tagging 83500 projects from 2000
Progress: 100% [######################################################################] Time: 0:05:11
83500 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 81265 projects from 2001
Progress: 100% [######################################################################] Time: 0:05:03
81265 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 83423 projects from 2002
Progress: 100% [######################################################################] Time: 0:05:25
83423 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 61612 projects from 2003
Progress: 100% [######################################################################] Time: 0:05:17
61612 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 78778 projects from 2004
Progress: 100% [######################################################################] Time: 0:05:34
78778 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 82209 projects from 2005
Progress: 100% [######################################################################] Time: 0:05:53
82209 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 81670 projects from 2006
Progress: 100% [######################################################################] Time: 0:05:59
81670 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 88886 projects from 2007
Progress: 100% [######################################################################] Time: 0:06:56
88886 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 87922 projects from 2008
Progress: 100% [######################################################################] Time: 0:06:59
87922 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 98942 projects from 2009
Progress: 100% [######################################################################] Time: 0:08:38
98942 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 93841 projects from 2010
Progress: 100% [######################################################################] Time: 0:08:32
93841 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 83643 projects from 2011
Progress: 100% [######################################################################] Time: 0:08:07
83643 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 78989 projects from 2012
Progress: 100% [######################################################################] Time: 0:08:07
78989 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 77036 projects from 2013
Progress: 100% [######################################################################] Time: 0:07:32
77036 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 76167 projects from 2014
Progress: 100% [######################################################################] Time: 0:07:32
76167 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 73356 projects from 2015
Progress: 100% [######################################################################] Time: 0:07:55
73356 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

grant_tagger.py: Done.

# | 51 | NIH Grant Info                           |
delete from provenance where dataset_id = 51;
delete from dataset where id = 51;
delete from `grant`;
ALTER TABLE `grant` AUTO_INCREMENT = 1;
delete from tdl_info where itype = 'NIHRePORTER 2000-2015 R01 Count';

[smathias@juniper loaders]$ ./load-GrantInfo.py --dbname tcrd4

load-GrantInfo.py (v2.0.0) [Thu Feb 16 09:20:55 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.1; data ver 4.2.0)

Loading project info from pickle file ../data/NIHExporter/ProjectInfo2000-2015.p

Loading tagging results in ../data/NIHExporter/TCRDv4/

Processing tagging results for 2000: 5471 targets
Progress: 100% [######################################################################] Time: 0:00:49
Processed 5471 target tagging records. Elapsed time: 0:00:49.493
  Inserted 69578 new target2grant rows

Processing tagging results for 2001: 5763 targets
Progress: 100% [######################################################################] Time: 0:00:48
Processed 5763 target tagging records. Elapsed time: 0:00:48.961
  Inserted 69734 new target2grant rows

Processing tagging results for 2002: 6060 targets
Progress: 100% [######################################################################] Time: 0:00:52
Processed 6060 target tagging records. Elapsed time: 0:00:53.127
  Inserted 75158 new target2grant rows

Processing tagging results for 2003: 6248 targets
Progress: 100% [######################################################################] Time: 0:00:50
Processed 6248 target tagging records. Elapsed time: 0:00:51.274
  Inserted 72747 new target2grant rows

Processing tagging results for 2004: 6457 targets
Progress: 100% [######################################################################] Time: 0:00:54
Processed 6457 target tagging records. Elapsed time: 0:00:54.813
  Inserted 78203 new target2grant rows

Processing tagging results for 2005: 6660 targets
Progress: 100% [######################################################################] Time: 0:00:57
Processed 6660 target tagging records. Elapsed time: 0:00:58.298
  Inserted 83483 new target2grant rows

Processing tagging results for 2006: 6831 targets
Progress: 100% [######################################################################] Time: 0:01:00
Processed 6831 target tagging records. Elapsed time: 0:01:01.256
  Inserted 87361 new target2grant rows

Processing tagging results for 2007: 7496 targets
Progress: 100% [######################################################################] Time: 0:01:07
Processed 7496 target tagging records. Elapsed time: 0:01:08.231
  Inserted 98635 new target2grant rows

Processing tagging results for 2008: 7590 targets
Progress: 100% [######################################################################] Time: 0:01:09
Processed 7590 target tagging records. Elapsed time: 0:01:10.233
  Inserted 100639 new target2grant rows

Processing tagging results for 2009: 8069 targets
Progress: 100% [######################################################################] Time: 0:01:28
Processed 8069 target tagging records. Elapsed time: 0:01:29.228
  Inserted 129547 new target2grant rows

Processing tagging results for 2010: 8148 targets
Progress: 100% [######################################################################] Time: 0:01:27
Processed 8148 target tagging records. Elapsed time: 0:01:28.098
  Inserted 124662 new target2grant rows

Processing tagging results for 2011: 8058 targets
Progress: 100% [######################################################################] Time: 0:01:15
Processed 8058 target tagging records. Elapsed time: 0:01:16.565
  Inserted 109710 new target2grant rows

Processing tagging results for 2012: 7989 targets
Progress: 100% [######################################################################] Time: 0:01:13
Processed 7989 target tagging records. Elapsed time: 0:01:14.433
  Inserted 107000 new target2grant rows

Processing tagging results for 2013: 7900 targets
Progress: 100% [######################################################################] Time: 0:01:11
Processed 7900 target tagging records. Elapsed time: 0:01:12.097
  Inserted 103410 new target2grant rows

Processing tagging results for 2014: 7957 targets
Progress: 100% [######################################################################] Time: 0:01:11
Processed 7957 target tagging records. Elapsed time: 0:01:11.773
  Inserted 101767 new target2grant rows

Processing tagging results for 2015: 8002 targets
Progress: 100% [######################################################################] Time: 0:01:12
Processed 8002 target tagging records. Elapsed time: 0:01:12.703
  Inserted 103577 new target2grant rows

Loading 'NIHRePORTER 2010-2015 R01 Count' tdl_infos for 9409 targets
  Inserted 9409 new tdl_info rows

load-GrantInfo.py: Done.

mysql> update dbinfo set schema_ver = '4.0.2', data_ver = '4.3.0';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.3.0.sql


# IDG Families
delete from provenance where dataset_id = 49;
delete from dataset where id = 49;
alter table target drop idgfam;
alter table target drop tiofam;
alter table target add column fam enum('Enzyme', 'Epigenetic', 'GPCR', 'IC', 'Kinase', 'NR', 'oGPCR', 'TF', 'TF; Epigenetic', 'Transporter') NULL;
alter table target add column famext VARCHAR(255) NULL;

[smathias@juniper loaders]$ ./load-IDGFamsExt.py --dbname tcrd4

load-IDGFamsExt.py (v1.0.0) [Wed Feb 22 15:57:00 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.2; data ver 4.3.0)

Processing 20187 lines in inut file ../data/TCRD_3.1.4_TDL_families_Updated.txt
Progress: 100% [######################################################################] Time: 0:00:24
20186 rows processed. Elapsed time: 0:00:24.172
8149 IDG family designations loaded into TCRD.
5621 IDG extended family designations loaded into TCRD.
  No target found for 2 UniProt accessions: Q8NFS9, Q06430

load-IDGFamsExt.py: Done.

mysql> update dbinfo set schema_ver = '4.0.3', data_ver = '4.3.1';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.3.1.sql

After reload of DISEASES to get dids:
mysql> update dbinfo set data_ver = '4.3.2';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.3.2.sql


[smathias@juniper loaders]$ ./load-PANTHERClasses.py --dbname tcrd4

load-PANTHERClasses.py (v2.0.0) [Thu Feb 23 12:31:08 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.3; data ver 4.3.2)

Processing 291 lines in input file /home/app/TCRD/data/PANTHER/Protein_class_relationship
291 input lines processed.
  Got 244 PANTHER Class relationships

Processing 291 lines in input file /home/app/TCRD/data/PANTHER/Protein_Class_7.0
291 input lines processed. Elapsed time: 0:00:00.195
  Inserted 244 new panther_class rows

Processing 19184 lines in input file /home/app/TCRD/data/PANTHER/PTHR10.0_human
Progress: 100% [######################################################################] Time: 0:00:52
19184 input lines processed. Elapsed time: 0:00:52.821
  Inserted 35510 new p2pc rows for 10982 distinct proteins
  Skipped 7955 rows without PCs
No target found for 163 rows:

mysql> update dbinfo set data_ver = '4.3.3';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.3.3.sql


# expression.qual value is set to NOT NULL which means rows entered
  without a qual_value are set to Not detected. NOT GOOD!
Need to fix this for sources that do not get qual_value explicitly set.
mysql> select etype, count(*) from expression group by etype;
+----------------------------------+----------+
| etype                            | count(*) |
+----------------------------------+----------+
| Consensus                        |   200294 |
| GTEx                             | 12287320 |
| HPA Protein                      |   406355 |
| HPA RNA                          |   594622 |
| HPM Gene                         |   485550 |
| HPM Protein                      |   837600 |
| JensenLab Experiment Exon array  |    52370 |
| JensenLab Experiment GNF         |    45569 |
| JensenLab Experiment HPA         |   104983 |
| JensenLab Experiment HPA-RNA     |   140405 |
| JensenLab Experiment HPM         |    37623 |
| JensenLab Experiment RNA-seq     |    53609 |
| JensenLab Experiment UniGene     |    57325 |
| JensenLab Knowledge UniProtKB-RC |    64843 |
| JensenLab Text Mining            |    57543 |
| UniProt Tissue                   |    69883 |
+----------------------------------+----------+
That would be JensenLab TISSUES and UniProt Tissue.

mysql> alter table expression modify qual_value enum('Not detected','Low','Medium','High');
mysql> update expression set qual_value = NULL where etype like 'JensenLab%';
mysql> update expression set qual_value = NULL where etype = 'UniProt Tissue';

mysql> update dbinfo set schema_ver = '4.0.4', data_ver = '4.3.4';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.3.4.sql


mysql> delete from disease where dtype = 'DrugCentral Indication';
mysql> delete from provenance where dataset_id = 61;
mysql> delete from dataset where id = 61;
mysql> update target set tdl = NULL;

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd4

load-DrugCentral.py (v2.0.1) [Mon Mar  6 10:18:02 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.3.4)

Processing 1776 input lines in file ../data/DrugCentral/drug_info_03032017.tsv
1776 input lines processed.
Saved 1776 keys in infos map

Processing 3144 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_03032017.tsv
/home/app/TCRD4/loaders/TCRD.py:653: Warning: Data truncated for column 'act_value' at row 1
  curs.execute(sql, tuple(params))
3144 DrugCentral Tclin rows processed.
  Inserted 3144 new drug_activity rows

Processing 600 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_03032017.tsv
600 DrugCentral Tchem rows processed.
  Inserted 600 new drug_activity rows

Processing 10852 lines from indications file ../data/DrugCentral/drug_indications_03032017.tsv
10852 DrugCentral indication rows processed.
  Inserted 12108 new target2disease rows
WARNNING: 994 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done.


[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd4

load-TDLs.py (v2.0.0) [Mon Mar  6 10:19:53 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.3.4)

Processing 20120 TCRD targets
Progress: 100% [######################################################################] Time: 0:24:38
20120 TCRD targets processed. Elapsed time: 0:24:38.333
Set TDL values for 20120 targets
  601 targets are Tclin
  1402 targets are Tchem
  11086 targets are Tbio (836 bumped from Tdark)
  7031 targets are Tdark

load-TDLs.py: Done.

update dbinfo set data_ver = '4.4.0';


mysql> delete from provenance where dataset_id = 70;
mysql> delete from dataset where id = 70;
mysql> delete from `grant`;
mysql> ALTER TABLE `grant` AUTO_INCREMENT = 1;
mysql> delete from tdl_info where itype = 'NIHRePORTER 2000-2015 R01 Count';

[smathias@juniper python]$ ./pickle_grant_info.py

pickle_grant_info.py (v1.0.0) [Tue Mar  7 11:31:07 2017]:

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

Dumping info on projects to pickle ../data/NIHExporter/ProjectInfo2000-2015.p

pickle_grant_info.py: Done.

[smathias@juniper python]$ ./grant_tagger.py --dbname tcrd4

grant_tagger.py (v2.0.0) [Tue Mar  7 11:39:02 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.4.0)

Loading project info from pickle file ../data/NIHExporter/ProjectInfo2000-2015.p

Creating Tagger...

Tagging 83500 projects from 2000
Progress: 100% [######################################################################] Time: 0:03:16
83500 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 81265 projects from 2001
Progress: 100% [######################################################################] Time: 0:03:21
81265 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 83423 projects from 2002
Progress: 100% [######################################################################] Time: 0:03:35
83423 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 61612 projects from 2003
Progress: 100% [######################################################################] Time: 0:03:24
61612 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 78778 projects from 2004
Progress: 100% [######################################################################] Time: 0:03:37
78778 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 82209 projects from 2005
Progress: 100% [######################################################################] Time: 0:03:51
82209 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 81670 projects from 2006
Progress: 100% [######################################################################] Time: 0:03:56
81670 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 88886 projects from 2007
Progress: 100% [######################################################################] Time: 0:04:38
88886 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 87922 projects from 2008
Progress: 100% [######################################################################] Time: 0:05:35
87922 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 98942 projects from 2009
Progress: 100% [######################################################################] Time: 0:05:50
98942 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 93841 projects from 2010
Progress: 100% [######################################################################] Time: 0:06:05
93841 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 83643 projects from 2011
Progress: 100% [######################################################################] Time: 0:05:46
83643 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 78989 projects from 2012
Progress: 100% [######################################################################] Time: 0:05:34
78989 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 77036 projects from 2013
Progress: 100% [######################################################################] Time: 0:05:12
77036 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 76167 projects from 2014
Progress: 100% [######################################################################] Time: 0:05:07
76167 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 73356 projects from 2015
Progress: 100% [######################################################################] Time: 0:05:08
73356 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

grant_tagger.py: Done.

[smathias@juniper loaders]$ ./load-GrantInfo.py --dbname tcrd4

load-GrantInfo.py (v2.0.0) [Tue Mar  7 12:57:00 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.4.0)

Loading project info from pickle file ../data/NIHExporter/ProjectInfo2000-2015.p

Loading tagging results in ../data/NIHExporter/TCRDv4/

Processing tagging results for 2000: 5544 targets
Progress: 100% [######################################################################] Time: 0:00:36
Processed 5544 target tagging records. Elapsed time: 0:00:36.632
  Inserted 62239 new target2grant rows

Processing tagging results for 2001: 5842 targets
Progress: 100% [######################################################################] Time: 0:00:36
Processed 5842 target tagging records. Elapsed time: 0:00:37.028
  Inserted 61874 new target2grant rows

Processing tagging results for 2002: 6142 targets
Progress: 100% [######################################################################] Time: 0:00:38
Processed 6142 target tagging records. Elapsed time: 0:00:39.258
  Inserted 66017 new target2grant rows

Processing tagging results for 2003: 6331 targets
Progress: 100% [######################################################################] Time: 0:00:38
Processed 6331 target tagging records. Elapsed time: 0:00:38.353
  Inserted 62622 new target2grant rows

Processing tagging results for 2004: 6541 targets
Progress: 100% [######################################################################] Time: 0:00:44
Processed 6541 target tagging records. Elapsed time: 0:00:44.585
  Inserted 66519 new target2grant rows

Processing tagging results for 2005: 6744 targets
Progress: 100% [######################################################################] Time: 0:00:46
Processed 6744 target tagging records. Elapsed time: 0:00:46.461
  Inserted 69822 new target2grant rows

Processing tagging results for 2006: 6923 targets
Progress: 100% [######################################################################] Time: 0:00:45
Processed 6923 target tagging records. Elapsed time: 0:00:46.138
  Inserted 72183 new target2grant rows

Processing tagging results for 2007: 7594 targets
Progress: 100% [######################################################################] Time: 0:00:52
Processed 7594 target tagging records. Elapsed time: 0:00:52.883
  Inserted 81602 new target2grant rows

Processing tagging results for 2008: 7695 targets
Progress: 100% [######################################################################] Time: 0:00:51
Processed 7695 target tagging records. Elapsed time: 0:00:52.127
  Inserted 81832 new target2grant rows

Processing tagging results for 2009: 8184 targets
Progress: 100% [######################################################################] Time: 0:01:08
Processed 8184 target tagging records. Elapsed time: 0:01:08.847
  Inserted 103702 new target2grant rows

Processing tagging results for 2010: 8265 targets
Progress: 100% [######################################################################] Time: 0:01:03
Processed 8265 target tagging records. Elapsed time: 0:01:03.717
  Inserted 98793 new target2grant rows

Processing tagging results for 2011: 8166 targets
Progress: 100% [######################################################################] Time: 0:00:56
Processed 8166 target tagging records. Elapsed time: 0:00:56.630
  Inserted 85822 new target2grant rows

Processing tagging results for 2012: 8101 targets
Progress: 100% [######################################################################] Time: 0:00:54
Processed 8101 target tagging records. Elapsed time: 0:00:55.079
  Inserted 82726 new target2grant rows
Processing tagging results for 2013: 8014 targets
Progress: 100% [######################################################################] Time: 0:00:51
Processed 8014 target tagging records. Elapsed time: 0:00:52.295
  Inserted 78597 new target2grant rows

Processing tagging results for 2014: 8072 targets
Progress: 100% [######################################################################] Time: 0:00:49
Processed 8072 target tagging records. Elapsed time: 0:00:49.965
  Inserted 76052 new target2grant rows

Processing tagging results for 2015: 8117 targets
Progress: 100% [######################################################################] Time: 0:00:49
Processed 8117 target tagging records. Elapsed time: 0:00:50.238
  Inserted 76020 new target2grant rows

Loading 'NIHRePORTER 2010-2015 R01 Count' tdl_infos for 9588 targets
  Inserted 9588 new tdl_info rows

load-GrantInfo.py: Done.

update dbinfo set data_ver = '4.4.1';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.4.1.sql


Re-do tagging again...

update dbinfo set data_ver = '4.4.2';
[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd_v4.4.2.sql


mysql> delete from provenance where dataset_id in (65, 67);
mysql> delete from dataset where id in (65, 67);
mysql> update dbinfo set data_ver = '4.4.3';
[smathias@juniper SQL]$ mysqldump tcrd > dumps/tcrd_v4.4.3.sql


mysql> delete from disease where dtype = 'DrugCentral Indication';
mysql> select id from dataset where name = 'Drug Central';
mysql> delete from provenance where dataset_id = 75;
mysql> delete from dataset where id = 75;
mysql> update target set tdl = NULL;
mysql> select id from dataset where name = 'TDLs';
mysql> delete from provenance where dataset_id = 76;
mysql> delete from dataset where id = 76;



[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd4

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd4

load-DrugCentral.py (v2.0.1) [Mon May  8 10:53:40 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.4.3)

Processing 1815 input lines in file ../data/DrugCentral/drug_info_04252017.tsv
1815 input lines processed.
Saved 1815 keys in infos map

Processing 3164 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_04252017.tsv
3164 DrugCentral Tclin rows processed.
  Inserted 3164 new drug_activity rows

Processing 643 lines from Non-MOA activities file ../data/DrugCentral/tchem_drugs_04252017.tsv
643 DrugCentral Tchem rows processed.
  Inserted 643 new drug_activity rows

Processing 10875 lines from indications file ../data/DrugCentral/drug_indications_04252017.tsv
10875 DrugCentral indication rows processed.
  Inserted 12644 new target2disease rows
WARNNING: 994 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done.

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd4

load-TDLs.py (v2.0.0) [Mon May  8 11:31:45 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.5.0)

Processing 20120 TCRD targets
Progress: 100% [######################################################################] Time: 0:23:22
20120 TCRD targets processed. Elapsed time: 0:23:22.696
Set TDL values for 20120 targets
  602 targets are Tclin
  1406 targets are Tchem
  11081 targets are Tbio (836 bumped from Tdark)
  7031 targets are Tdark

load-TDLs.py: Done.

mysql> update dbinfo set data_ver = '4.5.0';
[smathias@juniper SQL]$ mysqldump tcrd > dumps/tcrd_v4.5.0.sql

#
# LocSigDB
#
delete from provenance where dataset_id > 80;
delete from dataset where id > 80;
alter table dataset AUTO_INCREMENT = 81;
drop table locsig;
CREATE TABLE `locsig` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `location` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `signal` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `pmids` text COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `compartment_idx1` (`protein_id`),
  CONSTRAINT `fk_locsig_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

[smathias@juniper loaders]$ ./load-LocSigDB.py --dbname tcrd4

load-LocSigDB.py (v1.0.0) [Mon May  8 12:01:32 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.4; data ver 4.5.0)

Processing 534 lines in input file ../data/LocSigDB/LocSigDB.csv
Progress: 100% [######################################################################] Time: 0:10:53
534 rows processed. Elapsed time: 0:10:54.020
  Skipped 234 non-human rows
  18956 proteins have locsig(s)
  Inserted 106671 new locsig rows
No target found for 1 input lines. See logfile load-LocSigDB.py.log for details

load-LocSigDB.py: Done.

[smathias@juniper loaders]$ cat load-LocSigDB.py.log
2017-05-08 12:12:26 - __main__ - WARNING: No target found for Protein(s): PR-M (Progesterone Receptor)

mysql> update dbinfo set schema_ver = '4.0.5', data_ver = '4.5.1';
[smathias@juniper SQL]$ mysqldump tcrd > dumps/tcrd_v4.5.1.sql


mysql> select count(distinct `signal`) from locsig;
+--------------------------+
| count(distinct `signal`) |
+--------------------------+
|                      299 |
+--------------------------+
mysql> select distinct location from locsig;
+------------------------------------------------+
| location                                       |
+------------------------------------------------+
| Lysosome                                       |
| Lysosome|Melanosome                            |
| Lysosome|Endosome                              |
| Nucleus                                        |
| Peroxisomes                                    |
| Endoplasmic Reticulum                          |
| Endoplasmic Reticulum (pre-golgi compartments) |
| Golgi (early post -Golgi comparments)          |
| Golgi                                          |
| Plasma membrane                                |
| Plasma membrane|basolateral cell surface       |
| Plasma membrane |periplasm                     |
| Secretory Pathway                              |
| Mitochondria                                   |
+------------------------------------------------+
mysql> select location, count(*) from locsig group by location;
+------------------------------------------------+----------+
| location                                       | count(*) |
+------------------------------------------------+----------+
| Endoplasmic Reticulum                          |    19285 |
| Endoplasmic Reticulum (pre-golgi compartments) |      312 |
| Golgi                                          |      385 |
| Golgi (early post -Golgi comparments)          |     2156 |
| Lysosome                                       |    18061 |
| Lysosome|Endosome                              |        2 |
| Lysosome|Melanosome                            |     9734 |
| Mitochondria                                   |       17 |
| Nucleus                                        |    19318 |
| Peroxisomes                                    |    35924 |
| Plasma membrane                                |     1464 |
| Plasma membrane |periplasm                     |        9 |
| Plasma membrane|basolateral cell surface       |        1 |
| Secretory Pathway                              |        3 |
+------------------------------------------------+----------+
mysql> select location, count(distinct protein_id) from locsig group by location;
+------------------------------------------------+----------------------------+
| location                                       | count(distinct protein_id) |
+------------------------------------------------+----------------------------+
| Endoplasmic Reticulum                          |                      15489 |
| Endoplasmic Reticulum (pre-golgi compartments) |                        312 |
| Golgi                                          |                        378 |
| Golgi (early post -Golgi comparments)          |                       2156 |
| Lysosome                                       |                      13581 |
| Lysosome|Endosome                              |                          2 |
| Lysosome|Melanosome                            |                       9732 |
| Mitochondria                                   |                         17 |
| Nucleus                                        |                      10437 |
| Peroxisomes                                    |                      14680 |
| Plasma membrane                                |                       1426 |
| Plasma membrane |periplasm                     |                          9 |
| Plasma membrane|basolateral cell surface       |                          1 |
| Secretory Pathway                              |                          3 |
+------------------------------------------------+----------------------------+


# ChEMBL_23
mysql> SELECT count(*) FROM activities acts, compound_records cr, assays a, target_dictionary t, compound_structures cs, molecule_dictionary md WHERE acts.record_id = cr.record_id AND cs.molregno = md.molregno AND cs.molregno = acts.molregno AND acts.assay_id = a.assay_id AND a.tid = t.tid AND acts.molregno = md.molregno AND cr.src_id = 38;
+----------+
| count(*) |
+----------+
|    20941 |
+----------+
mysql> SELECT count(*) FROM activities acts, compound_records cr, assays a, target_dictionary t, compound_structures cs, molecule_dictionary md WHERE acts.record_id = cr.record_id AND cs.molregno = md.molregno AND cs.molregno = acts.molregno AND acts.assay_id = a.assay_id AND a.tid = t.tid AND acts.molregno = md.molregno AND a.assay_type = 'B' AND md.structure_type = 'MOL' AND acts.standard_flag = 1 AND acts.standard_relation = '=' AND t.target_type = 'SINGLE PROTEIN' AND acts.pchembl_value IS NOT NULL AND cr.src_id = 38;
+----------+
| count(*) |
+----------+
|     3893 |
+----------+

delete from chembl_activity;
alter table chembl_activity AUTO_INCREMENT = 1;
delete from tdl_info where itype = 'ChEMBL First Reference Year';
delete from tdl_info where itype = 'ChEMBL Selective Compound';
delete from provenance where dataset_id in (14, 43);
delete from dataset where id in (14, 43);
update target set tdl = NULL;
select id from dataset where name = 'TDLs';
delete from provenance where dataset_id = 80;
delete from dataset where id = 80;

[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd4

load-ChEMBL.py (v2.1.0) [Fri May 19 11:52:58 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.5; data ver 4.5.1)

Processing 9494 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
9494 input lines processed.

Processing 7754 UniProt to ChEMBL ID(s) mappings
Progress: 100% [######################################################################] Time: 0:12:12
7754 UniProt accessions processed.
  0 targets not found in ChEMBL
  936 targets have no good activities in ChEMBL
Inserted 362281 new chembl_activity rows
Inserted 2374 new ChEMBL First Reference Year tdl_infos
WARNING: 5 database errors occured. See logfile load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 16638 selective compounds
Inserted 775 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 0:12:50.926

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd4

load-TDLs.py (v2.0.0) [Fri May 19 12:13:37 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.5; data ver 4.5.1)

Processing 20120 TCRD targets
Progress: 100% [######################################################################] Time: 0:24:26
20120 TCRD targets processed. Elapsed time: 0:24:26.493
Set TDL values for 20120 targets
  602 targets are Tclin
  1890 targets are Tchem
  10625 targets are Tbio (821 bumped from Tdark)
  7003 targets are Tdark

load-TDLs.py: Done.

mysql> update dbinfo set data_ver = '4.6.0';
[smathias@juniper SQL]$ mysqldump tcrd > dumps/tcrd_v4.6.0.sql



Next load of UniProt needs to manually fix this:
mysql> select id, name, description, sym, uniprot, geneid, stringid from protein where id in (9170, 9+------+-------------+-------------------------------+---------+---------+--------+----------+
| id   | name        | description                   | sym     | uniprot | geneid | stringid |
+------+-------------+-------------------------------+---------+---------+--------+----------+
| 9170 | OPSG2_HUMAN | Medium-wave-sensitive opsin 2 | OPN1MW2 | P0DN77  | 728458 | NULL     |
| 9171 | OPSG3_HUMAN | Medium-wave-sensitive opsin 3 | OPN1MW2 | P0DN78  | 728458 | NULL     |
+------+-------------+-------------------------------+---------+---------+--------+----------+


P0DN77 -> OPN1MW2 728458

P0DN78 -> OPN1MW3 101060233

But for now, theses need to be set as GPCRs:
mysql> UPDATE target set fam = 'GPCR' WHERE id in (9170, 9171);
mysql> update dbinfo set data_ver = '4.6.1';
[smathias@juniper SQL]$ mysqldump tcrd > dumps/tcrd_v4.6.1.sql


#
# Redo TIN-X
#
select id from dataset where name = 'TIN-X Data';
DELETE FROM provenance WHERE dataset_id = 52;
DELETE FROM dataset WHERE id = 52;

mysql> delete from tinx_novelty;
mysql> alter table tinx_novelty AUTO_INCREMENT = 1;
mysql> delete from tinx_importance;
mysql> alter table tinx_importance AUTO_INCREMENT = 1;
mysql> delete from tinx_disease;
mysql> alter table tinx_disease AUTO_INCREMENT = 1;
mysql> delete from tinx_articlerank;
mysql> alter table tinx_articlerank AUTO_INCREMENT = 1;

[smathias@juniper python]$ ./TIN-X.py --dbname tcrd4

TIN-X.py (v2.1.0) [Thu Jun  8 14:04:21 2017]:

Downloading https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/master/src/ontology/doid.obo
         to ../data/DiseaseOntology/doid.obo

Downloading http://download.jensenlab.org/disease_textmining_mentions.tsv
         to ../data/JensenLab/disease_textmining_mentions.tsv
Downloading http://download.jensenlab.org/human_textmining_mentions.tsv
         to ../data/JensenLab/human_textmining_mentions.tsv

Connected to TCRD database tcrd4 (schema ver 4.0.5; data ver 4.6.1)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 10892 Disease Ontology terms

Processing 20201 input lines in protein file ../data/JensenLab/human_textmining_mentions.tsv
Progress: 100% [########################################################################] Time: 0:03:55
20201 input lines processed. Elapsed time: 0:03:55.517
  Skipped 2463 non-ENSP lines
  Saved 17718 protein to PMIDs mappings
  Saved 4592908 PMID to protein count mappings
WARNING: No target found for 179 ENSPs. See logfile TIN-X.py.log for details.

Processing 8532 input lines in file ../data/JensenLab/disease_textmining_mentions.tsv
Progress: 100% [######################################################################] Time: 0:01:12
8532 input lines processed. Elapsed time: 0:01:13.526
  Skipped 1668 non-DOID lines
  Saved 6864 DOID to PMIDs mappings
  Saved 9300760 PMID to disease count mappings

Computing protein novely scores
  Wrote 17718 novelty scores to file ../data/TIN-X/TCRDv4/ProteinNovelty.csv
  Elapsed time: 0:00:02.986

Computing disease novely scores
  Wrote 6864 novelty scores to file ../data/TIN-X/TCRDv4/DiseaseNovelty.csv
  Elapsed time: 0:00:22.975

Computing importance scores
  Wrote 2307334 importance scores to file ../data/TIN-X/TCRDv4/Importance.csv
  Elapsed time: 0:47:41.067

Computing PubMed rankings
  Wrote 35835016 PubMed trankings to file ../data/TIN-X/TCRDv4/PMIDRanking.csv
  Elapsed time: 1:04:48.343

TIN-X.py: Done.

[smathias@juniper loaders]$ ./load-TIN-X.py --dbname tcrd4

load-TIN-X.py (v2.0.1) [Thu Jun  8 16:22:31 2017]:

Connected to TCRD database tcrd4 (schema ver 4.0.5; data ver 4.6.1)

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 10892 Disease Ontology terms

Processing 6865 input lines in file ../data/TIN-X/TCRDv4/DiseaseNovelty.csv
Progress: 100% [########################################################################] Time: 0:00:04
6864 input lines processed. Elapsed time: 0:00:04.501
  Inserted 6864 new tinx_disease rows
  Saved 6864 keys in dmap

Processing 17719 input lines in file ../data/TIN-X/TCRDv4/ProteinNovelty.csv
Progress: 100% [########################################################################] Time: 0:00:11
17718 input lines processed. Elapsed time: 0:00:11.250
  Inserted 17718 new tinx_novelty rows

Processing 2307335 input lines in file ../data/TIN-X/TCRDv4/Importance.csv
Progress: 100% [########################################################################] Time: 0:26:28
2307334 input lines processed. Elapsed time: 0:26:28.554
  Inserted 2307334 new tinx_importance rows
  Saved 2307334 keys in imap

Processing 35835017 input lines in file ../data/TIN-X/TCRDv4/PMIDRanking.csv
Progress: 100% [########################################################################] Time: 5:49:24
35835016 input lines processed. Elapsed time: 5:49:27.504
  Inserted 35835016 new tinx_articlerank rows

load-TIN-X.py: Done.

mysql> update dbinfo set schema_ver = '4.0.6', data_ver = '4.6.2';
[smathias@juniper SQL]$ mysqldump tcrd > dumps/tcrd_v4.6.2.sql
