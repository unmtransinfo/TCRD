# Fix DisGeNET
mysql> delete from disease where dtype = 'DisGeNET';
Query OK, 82875 rows affected (4.61 sec)

[smathias@juniper loaders]$ ./load-DisGeNET.py --dbname tcrd6

load-DisGeNET.py (v2.3.0) [Mon Oct 14 11:59:18 2019]:

Downloading http://www.disgenet.org/static/disgenet_ap1/files/downloads/curated_gene_disease_associations.tsv.gz
         to ../data/DisGeNET/curated_gene_disease_associations.tsv.gz
Uncompressing ../data/DisGeNET/curated_gene_disease_associations.tsv.gz

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 6.0.0)

Processing 81747 lines in file ../data/DisGeNET/curated_gene_disease_associations.tsv
Progress: 100% [######################################################################] Time: 0:01:58
81747 lines processed.
Loaded 82875 new disease rows for 9025 proteins.
No target found for 494 symbols/geneids. See logfile ./tcrd6logs/load-DisGeNET.py.log for details.

load-DisGeNET.py: Done. Elapsed time: 0:02:02.115


# Fix PPIs
# All sources have ppis involving the same protein:
mysql> select ppitype, count(*) from ppi where protein1_id = protein2_id group by ppitype;
+----------+----------+
| ppitype  | count(*) |
+----------+----------+
| BioPlex  |     1594 |
| Reactome |     5343 |
| STRINGDB |       42 |
+----------+----------+

mysql> delete from ppi;
mysql> alter table ppi AUTO_INCREMENT = 1;

[smathias@juniper loaders]$ ./load-BioPlexPPIs.py --dbname tcrd6

load-BioPlexPPIs.py (v3.0.0) [Tue Oct 15 09:15:41 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 6.1.0)

Processing 56553 lines from BioPlex PPI file ../data/BioPlex/BioPlex_interactionList_v4a.tsv
Progress: 100% [######################################################################] Time: 0:01:17
56553 BioPlex PPI rows processed.
  Inserted 56339 new ppi rows
  Skipped 14 PPIs involving the same protein
  No target found for 39 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4955 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_May2016.tsv
Progress: 100% [######################################################################] Time: 0:00:25
4955 BioPlex PPI rows processed.
  Inserted 4586 new ppi rows
  Skipped 317 PPIs involving the same protein
  No target found for 14 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4305 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Aug2016.tsv
Progress: 100% [######################################################################] Time: 0:00:22
4305 BioPlex PPI rows processed.
  Inserted 3922 new ppi rows
  Skipped 354 PPIs involving the same protein
  No target found for 10 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 3160 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Dec2016.tsv
Progress: 100% [######################################################################] Time: 0:00:18
3160 BioPlex PPI rows processed.
  Inserted 2831 new ppi rows
  Skipped 309 PPIs involving the same protein
  No target found for 12 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4046 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_April2017.tsv
Progress: 100% [######################################################################] Time: 0:00:21
4046 BioPlex PPI rows processed.
  Inserted 3696 new ppi rows
  Skipped 314 PPIs involving the same protein
  No target found for 19 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

Processing 4464 lines from BioPlex PPI update file ../data/BioPlex/interactome_update_Nov2017.tsv
Progress: 100% [######################################################################] Time: 0:00:22
4464 BioPlex PPI rows processed.
  Inserted 4145 new ppi rows
  Skipped 286 PPIs involving the same protein
  No target found for 16 UniProts/Syms/GeneIDs. See logfile ./tcrd6logs/load-BioPlexPPIs.py.log for details.

load-BioPlexPPIs.py: Done. Elapsed time: 0:03:08.648

[smathias@juniper loaders]$ ./load-ReactomePPIs.py --dbname tcrd6

load-ReactomePPIs.py (v3.0.0) [Tue Oct 15 09:28:56 2019]:

Downloading  https://reactome.org/download/current/interactors/reactome.homo_sapiens.interactions.tab-delimited.txt
         to  ../data/Reactome/reactome.homo_sapiens.interactions.tab-delimited.txt
Done.

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 6.1.0)

Processing 88685 lines from Reactome PPI file ../data/Reactome/reactome.homo_sapiens.interactions.tab-delimited.txt
Progress: 100% [######################################################################] Time: 0:00:24
88685 Reactome PPI rows processed.
  Inserted 21866 (21866) new ppi rows
  Skipped 32888 duplicate PPIs
  Skipped 5797 PPIs involving the same protein
  No target found for 272 UniProt accessions. See logfile ./tcrd6logs/load-ReactomePPIs.py.log for details.

load-ReactomePPIs.py: Done. Elapsed time: 0:00:27.318

[smathias@juniper loaders]$ ./load-STRINGDB.py --dbname tcrd6

load-STRINGDB.py (v1.0.0) [Tue Oct 15 09:32:14 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 6.1.0)

Processing 11759455 lines in file ../data/STRING/9606.protein.links.v11.0.txt
Progress: 100% [######################################################################] Time: 1:58:51
11759455 lines processed.
  Inserted 11638404 new ppi rows
  Skipped 42 PPIs involving the same protein
No target found for 424 ENSPs. See logfile ./tcrd6logs/load-STRINGDB.py.log for details.

load-STRINGDB.py: Done. Elapsed time: 1:58:52.278


#
# DTO IDs and Classifications
#
mysql> ALTER TABLE protein ADD COLUMN dtoclass varchar(255) DEFAULT NULL;

[smathias@juniper loaders]$ ./load-DTO_Classifications.py --dbname tcrd6

load-DTO_Classifications.py (v1.0.0) [Thu Oct 17 11:49:08 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.0; data ver 6.1.0)

Processing 9233 lines in file ../data/UMiami/DTO2UniProt_DTOv2.csv
Progress: 100% [######################################################################] Time: 0:00:17
9233 lines processed.
  Updated 9232 protein.dtoid values
Got 9232 UniProt to DTO mappings for TCRD targets
Got 9232 UniProt to Protein ID mappings for TCRD targets

Processing 9172 lines in file ../data/UMiami/Final_ProteomeClassification_Sep232019.csv
Progress: 100% [######################################################################] Time: 0:00:04
9172 lines processed.
  Updated 9171 protein.dtoclass values

load-DTO_Classifications.py: Done. Elapsed time: 0:00:21.837

mysql> update dbinfo set schema_ver = '6.1.0', data_ver = '6.1.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.1.0.sql


# DOIDs for DrugCentral Indication disease rows
mysql> delete from drug_activity;
mysql> ALTER TABLE drug_activity AUTO_INCREMENT = 1;
mysql> delete from disease where dtype = 'DrugCentral Indication';
mysql> delete from provenance where dataset_id = 9;
mysql> delete from dataset where id = 9;

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd6

load-DrugCentral.py (v2.5.0) [Tue Dec 10 10:43:46 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.1; data ver 6.2.0)

Processing 4531 input lines in file ../data/DrugCentral/drug_name_id_10122018.tsv
4531 input lines processed.
Saved 4531 keys in infos map

Processing 1866 input lines in file ../data/DrugCentral/drug_info_10122018.tsv
1866 input lines processed.
Saved 1866 keys in infos map

Processing 3219 lines from DrugDB MOA activities file ../data/DrugCentral/tclin_10122018.tsv
/home/app/TCRD/loaders/TCRDMP.py:711: Warning: Data truncated for column 'act_value' at row 1
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
  Inserted 12671 new disease rows
WARNNING: 1036 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done. Elapsed time: 0:00:14.538

# Scores for STRINGDB ppis
mysql> delete from ppi where ppitype = 'STRINGDB';

[smathias@juniper loaders]$ ./load-STRINGDB.py --dbname tcrd6

load-STRINGDB.py (v1.0.0) [Tue Dec 10 11:43:47 2019]:

Connected to TCRD database tcrd6 (schema ver 6.0.1; data ver 6.2.0)

Processing 11759455 lines in file ../data/STRING/9606.protein.links.v11.0.txt
Progress: 100% [##############################################################################] Time: 2:09:16
11759455 lines processed.
  Inserted 11638404 new ppi rows
  Skipped 42 PPIs involving the same protein
No target found for 424 ENSPs. See logfile ./tcrd6logs/load-STRINGDB.py.log for details.

load-STRINGDB.py: Done. Elapsed time: 2:09:17.551

mysql> update dbinfo set data_ver = '6.2.1';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.2.1.sql


# Add ClinVar
Run DDL in SQL/tcrdmp.sql to create clinvar tables

There are some issues splitting PhenotypeList field because of
semi-colons in names:
In [37]: with open(fn, 'rU') as tsv:
    ...:     tsvreader = csv.reader(tsv, delimiter='\t')
    ...:     header = tsvreader.next()
    ...:     ct += 1
    ...:     for row in tsvreader:
    ...:         ct += 1
    ...:         pts = row[13].split(';')
    ...:         ids = row[12].split(';')
    ...:         if len(pts) != len(ids):
    ...:             print "Mismatch on line %s:\n  %s\n%s"%(ct, row[12], row[13])
    ...:             
Mismatch on line 11176:
  MedGen:C2698314,SNOMED CT:450952005;MedGen:C0265308,OMIM:218600,Orphanet:ORPHA1225,SNOMED CT:77608001;MedGen:C1266165;MedGen:C1849453,OMIM:266280,Orphanet:ORPHA3021;MedGen:C0032339,Orphanet:ORPHA2909,SNOMED CT:69093006
  B lymphoblastic leukemia lymphoma with t(12;21)(p13;q22); TEL-AML1 (ETV6-RUNX1);Baller-Gerold syndrome;High Grade Surface Osteosarcoma;Rapadilino syndrome;Rothmund-Thomson syndrome
...
Mismatch on line 978990:
  MedGen:C2698317
  B Lymphoblastic Leukemia/Lymphoma with t(9;22)(q34.1;q11.2); BCR-ABL1

For now, these lines are skipped.

[smathias@juniper loaders]$ ./load-ClinVar.py --dbname tcrd6

load-ClinVar.py (v1.0.0) [Thu Jan  9 14:03:41 2020]:

Connected to TCRD database tcrd6 (schema ver 6.0.1; data ver 6.2.1)

Processing 1317566 lines in file ../data/ClinVar/variant_summary.txt
Progress:  99% [##################################################################### ] ETA:  0:00:00
Processed 1317566 lines. Got 12280 unique phenotypes/xrefs.
WARNING: Skipped 49 lines with mismatched PhenotypeIDS vs. PhenotypeList. See logfile ./tcrd6logs/load-ClinVar.py.log for details.

Loading 12280 clinvar_phenotype records
12280 records processed.
  Inserted 12280 new clinvar_phenotype rows
  Inserted 22373 new clinvar_phenotype_xref rows

Processing 1317566 lines in file ../data/ClinVar/variant_summary.txt
Progress: 100% [######################################################################] Time: 1:19:38
1317566 lines processed.
  Inserted 511408 new clinvar rows
No target found for 129 symbols/geneids. See logfile ./tcrd6logs/load-ClinVar.py.log for details.

load-ClinVar.py: Done.

mysql> update dbinfo set schema_ver = '6.2.0', data_ver = '6.3.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.3.0.sql


#
# Add DTO
#

mysql> drop table dto;
mysql> CREATE TABLE `dto` (
  `dtoid` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `parent_id` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `def` text COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`dtoid`),
  KEY `dto_idx1` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

[smathias@juniper loaders]$ ./load-DTO.py --dbname tcrd6

load-DTO.py (v3.0.0) [Fri Jan 17 13:51:22 2020]:

Connected to TCRD database tcrd6 (schema ver 6.3.0; data ver 6.3.1)

Parsing Drug Target Ontology file ../data/UMiami/dto_proteome_classification_only.owl
Got 17779 DTO terms

Loading 17779 Drug Target Ontology terms
Progress: 100% [#######################################################################] Time: 0:00:07
17779 terms processed.
  Inserted 17779 new dto rows

load-DTO.py: Done.

mysql> ALTER TABLE dto ADD CONSTRAINT `fk_dto_dto` FOREIGN KEY (`parent_id`) REFERENCES `dto` (`dtoid`);
mysql> update dbinfo set schema_ver = '6.4.0', data_ver = '6.4.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.4.0.sql


# Reload IMPC Phenotypes to include all p-values

mysql> delete from phenotype where ptype = 'IMPC';
Query OK, 570839 rows affected (56.30 sec)
mysql> delete from provenance where dataset_id = 35;
Query OK, 1 row affected (0.00 sec)
mysql> delete from dataset where id = 35;
Query OK, 1 row affected (0.07 sec)

[smathias@juniper loaders]$ ./load-IMPC-Phenotypes.py --dbname tcrd6

load-IMPC-Phenotypes.py (v2.5.0) [Thu May  7 12:13:06 2020]:

Connected to TCRD database tcrd6 (schema ver 6.4.0; data ver 6.4.0)

Processing 28115 lines from input file ../data/IMPC/IMPC_genotype_phenotype.csv
Progress: 100% [######################################################################] Time: 0:06:37
28114 lines processed.
Loaded 123440 IMPC phenotypes for 16782 nhproteins
No nhprotein found for 50 gene symbols. See logfile ./tcrd6logs/load-IMPC-Phenotypes.py.log for details.
Skipped 403 lines with no term_id or term_name.

Processing 1867835 lines from input file ../data/IMPC/IMPC_ALL_statistical_results.csv
Progress: 100% [######################################################################] Time: 1:23:59
1867834 lines processed.
Loaded 7122495 IMPC phenotypes for 27548 nhproteins
No nhprotein found for 152 gene symbols. See logfile ./tcrd6logs/load-IMPC-Phenotypes.py.log for details.
Skipped 84665 lines with no term_id/term_name or no p-value.

load-IMPC-Phenotypes.py: Done. Elapsed time: 1:30:37.595

mysql> update dbinfo set data_ver = '6.5.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.5.0.sql


# DrugCentral, new version
mysql> delete from drug_activity;
mysql> ALTER TABLE drug_activity AUTO_INCREMENT = 1;
mysql> delete from disease where dtype = 'DrugCentral Indication';
mysql> delete from provenance where dataset_id = 84;
mysql> delete from dataset where id = 84;

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd6

load-DrugCentral.py (v3.0.0) [Thu May 28 12:31:10 2020]:

Connected to TCRD database tcrd6 (schema ver 6.4.0; data ver 6.5.0)

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

load-DrugCentral.py: Done. Elapsed time: 0:00:12.664

[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd6

mysql> update dbinfo set data_ver = '6.6.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.6.0.sql


# TDLs
mysql> update target set tdl = NULL;
mysql> delete from provenance where dataset_id = 18;
mysql> delete from dataset where id = 18;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v3.0.0) [Thu May 28 12:42:33 2020]:

Connected to TCRD database tcrd6 (schema ver 6.4.0; data ver 6.6.0)

Processing 20412 TCRD targets
Progress: 100% [######################################################################] Time: 0:01:28
20412 TCRD targets processed.
Set TDL values for 20412 targets:
  659 targets are Tclin
  1607 targets are Tchem
  11778 targets are Tbio - 590 bumped from Tdark
  6368 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:01:28.418

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.6.0.sql


# Add indexes for IMPC queries for MetepML
mysql> CREATE INDEX nhprotein_idx2  ON nhprotein(sym);
mysql> CREATE INDEX ortholog_idx2  ON ortholog(symbol);
mysql> UPDATE dbinfo SET schema_ver = '6.4.1', data_ver = '6.6.1';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.6.1.sql


# Fixes for Keith's issues on github
mysql> UPDATE dto SET parent_id = REPLACE(parent_id, '_', ':');
mysql> UPDATE dto SET dtoid = REPLACE(dtoid, '_', ':');
mysql> ALTER TABLE disease MODIFY pvalue DECIMAL(20,19);

mysql> update dbinfo set schema_ver = '6.4.1', data_ver = '6.7.0';

[smathias@juniper loaders]$ python load-Phipster.py
Connected to MySQL database tcrd6
creating virus table
creating viral_protein table
creating viral_ppi table
done

mysql> INSERT INTO dataset (name, source, app, url) VALUES ('p-hipster viral PPIs', 'Files virProtein_name.txt, virProtein_ncbi.txt, virus_taxonomy.txt received from Gorka Lasso.', 'load-Phipster.py', 'http://phipster.org/');
mysql> INSERT INTO provenance (dataset_id, table_name) VALUES (94, 'virus');
mysql> INSERT INTO provenance (dataset_id, table_name) VALUES (94, 'viral_protein');
mysql> INSERT INTO provenance (dataset_id, table_name) VALUES (94, 'viral_ppi');

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.7.0.sql

# 6.8
mysql> delete from provenance where dataset_id = 10;
mysql> delete from dataset where id = 10;
mysql> delete from pmscore;
mysql> ALTER TABLE pmscore AUTO_INCREMENT = 1;

[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd6

load-JensenLabPubMedScores.py (v3.0.0) [Thu Nov 12 08:49:41 2020]:

Connected to TCRD database tcrd6 (schema ver 6.4.1; data ver 6.7.0)

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:03.459

Processing 389136 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [###############################################################] Time: 0:09:37
389136 input lines processed.
  Inserted 390341 new pmscore rows for 18045 targets
No target found for 234 STRING IDs. See logfile ./tcrd6logs/load-JensenLabPubMedScores.py.log for details.

Loading 18045 JensenLab PubMed Score tdl_infos
18045 processed
  Inserted 18045 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done. Elapsed time: 0:09:56.008

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.8.0.sql

mysql> delete from provenance where dataset_id = 93;
mysql> delete from dataset where id = 93;
mysql> select tdl, count(*) from target group by tdl;
mysql> UPDATE target SET tdl = NULL;

[smathias@juniper loaders]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v3.0.0) [Thu Nov 12 10:00:03 2020]:

Connected to TCRD database tcrd6 (schema ver 6.4.1; data ver 6.7.0)

Processing 20412 TCRD targets
Progress: 100% [##############################################################] Time: 0:02:36
20412 TCRD targets processed.
Set TDL values for 20412 targets:
  659 targets are Tclin
  1607 targets are Tchem
  11778 targets are Tbio - 590 bumped from Tdark
  6368 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:02:36.66

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.8.0.sql

[smathias@juniper loaders]$ python load-Phipster.py 
Connected to MySQL database tcrd6
creating virus table
creating viral_protein table
creating viral_ppi table
done

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.8.0.sql


# TIGA
mysql> CREATE TABLE tiga (
  id int(11) NOT NULL AUTO_INCREMENT,
  protein_id INT(11) NOT NULL,
  ensg VARCHAR(15) COLLATE utf8_unicode_ci NOT NULL,
  efoid VARCHAR(15) NOT NULL,
  trait VARCHAR(255) COLLATE utf8_unicode_ci NOT NULL,
  n_study INT(2) NULL,
  n_snp INT(2) NULL,
  n_snpw DECIMAL(5,3) NULL,
  geneNtrait INT(2) NULL,
  geneNstudy INT(2) NULL,
  traitNgene INT(2) NULL,
  traitNstudy INT(2) NULL,
  pvalue_mlog_median DECIMAL(7,3) NULL,
  pvalue_mlog_max DECIMAL(8,3) NULL,
  or_median DECIMAL(8,3) NULL,
  n_beta INT(2) NULL,
  study_N_mean INT(2) NULL,
  rcras DECIMAL(5,3) NULL,
  meanRank DECIMAL(18,12) NULL,
  meanRankScore  DECIMAL(18,14) NULL,
  PRIMARY KEY (id),
  KEY tiga_idx1 (protein_id),
  CONSTRAINT fk_tiga_protein FOREIGN KEY (protein_id) REFERENCES protein (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

mysql> CREATE TABLE tiga_provenance (
  id INT(11) NOT NULL AUTO_INCREMENT,
  ensg VARCHAR(15) COLLATE utf8_unicode_ci NOT NULL,
  efoid VARCHAR(15) NOT NULL,
  study_acc VARCHAR(20) NOT NULL,
  pubmedid INT(11) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

[smathias@juniper loaders]$ ./load-TIGA.py --dbname tcrd6

load-TIGA.py (v1.0.0) [Thu Dec  3 15:53:40 2020]:

Connected to TCRD database tcrd6 (schema ver 6.4.3; data ver 6.8.1)

Processing 101763 lines in TIGA file ../data/TIGA/tiga_gene-trait_stats.tsv
Progress: 100% [###################################################################] Time: 0:16:24
Processed 101763 lines
  Inserted 102407 new tiga rows for 11765 proteins

Processing 167812 lines in TIGA provenance file ../data/TIGA/tiga_gene-trait_provenance.tsv
Progress: 100% [###################################################################] Time: 0:02:30
Processed 167812 lines
  Inserted 167811 new tiga rows

load-TIGA.py: Done. Elapsed time: 0:18:54.995

mysql> update dbinfo set schema_ver = '6.5.0', data_ver = '6.8.2';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.8.2.sql


# New IMPC Phenotypes
mysql> delete from phenotype where ptype = 'IMPC';
mysql> delete from provenance where dataset_id = 91;
mysql> delete from dataset where id = 91;

(venv) [smathias@juniper python]$ ./load-IMPC-Phenotypes.py --dbname tcrd6

load-IMPC-Phenotypes.py (v3.0.0) [Mon Jan 11 08:06:36 2021]:

Connected to TCRD database tcrd6 (schema ver 6.5.0; data ver 6.8.2)

Downloading ftp://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/latest/results/genotype-phenotype-assertions-IMPC.csv.gz
         to genotype-phenotype-assertions-IMPC.csv.gz
Uncompressing ../data/IMPC/genotype-phenotype-assertions-IMPC.csv.gz

Downloading ftp://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/latest/results/statistical-results-ALL.csv.gz
         to statistical-results-ALL.csv.gz
Uncompressing ../data/IMPC/statistical-results-ALL.csv.gz

Processing 42531 lines in input file ../data/IMPC/genotype-phenotype-assertions-IMPC.csv
Progress: [##################################################] 100.0% Done.
42531 lines processed.
Loaded 182397 IMPC phenotypes for 24546 nhproteins
No nhprotein found for 151 gene symbols. See logfile ../log/tcrd6logs/load-IMPC-Phenotypes.py.log for details.

Processing 2117224 lines from input file ../data/IMPC/statistical-results-ALL.csv
Progress: [##################################################] 100.0% Done.
2117224 lines processed.
Loaded 168620 IMPC phenotypes for 25754 nhproteins
No nhprotein found for 158 gene symbols. See logfile ../log/tcrd6logs/load-IMPC-Phenotypes.py.log for details.
Skipped 2078173 lines with no term_id or term_name.

load-IMPC-Phenotypes.py: Done. Elapsed time: 0:15:24.829

mysql> update dbinfo set data_ver = '6.8.3';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.8.3.sql


# IDG List
v6.8.3:
mysql> select fam, count(*) from target where idg group by fam;
+--------+----------+
| fam    | count(*) |
+--------+----------+
| GPCR   |      117 |
| IC     |       62 |
| Kinase |      150 |
+--------+----------+
mysql> UPDATE target SET idg = 0;

In new file:
(venv) [smathias@juniper python]$ grep -c GPCR ../data/IDG_Lists/IDG_List_20210120_forv6.csv
116
(venv) [smathias@juniper python]$ grep -c IonChannel ../data/IDG_Lists/IDG_List_20210120_forv6.csv 
63
(venv) [smathias@juniper python]$ grep -c Kinase ../data/IDG_Lists/IDG_List_20210120_forv6.csv
144

# NB. Load script run with dataset/provenance commented out
(venv) [smathias@juniper python]$ ./load-IDGList.py --dbname tcrd6

load-IDGList.py (v4.0.0) [Thu Jan 21 11:22:50 2021]:

Connected to TCRD database tcrd6 (schema ver 6.5.0; data ver 6.8.3)

Processing 324 lines in file ../data/IDG_Lists/IDG_List_20210120_forv6.csv
Progress: [##################################################] 100.0% Done.
324 lines processed
323 target rows updated with IDG flags
323 target rows updated with fams

load-IDGList.py: Done. Elapsed time: 0:00:03.039

mysql> UPDATE dataset SET source = 'IDG generated data in file IDG_List_20210120_forv6.csv', app_version = '3.0.0', datetime = '2021-01-21 11:22:50' WHERE id = 38;
mysql> UPDATE dbinfo SET data_ver = '6.8.4';

v6.8.4:
mysql> select fam, count(*) from target where idg group by fam;
+--------+----------+
| fam    | count(*) |
+--------+----------+
| GPCR   |      116 |
| IC     |       63 |
| Kinase |      144 |
+--------+----------+


# DRGC Resources
mysql> DROP TABLE drgc_resources;
mysql> CREATE TABLE `drgc_resource` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `rssid` text NOT NULL,
  `resource_type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) NOT NULL,
  `json` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `drgc_resource_idx1` (`target_id`),
  CONSTRAINT `fk_drgc_resource__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

mysql> delete from provenance where dataset_id = 71;
mysql> delete from dataset where id = 71;

(venv) [smathias@juniper python]$ ./load-DRGC_Resources.py --dbname tcrd6 2> xxx

load-DRGC_Resources.py (v4.0.0) [Thu Jan 21 12:00:45 2021]:

Connected to TCRD database tcrd6 (schema ver 6.5.0; data ver 6.8.4)

Getting target resource data from RSS...
Processing 804 target resource records...
Progress: [##################################################] 100.0% Done.
804 RSS target resource records processed.
  Skipped 484 non-pharosReady resources.
Inserted 320 new drgc_resource rows for 149 targets

load-DRGC_Resources.py: Done. Elapsed time: 0:01:39.336


[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.8.4.sql


### "Auto Update" TIN-X
(venv) [smathias@juniper python]$ ./tin-x.py --dbname tcrd6

tin-x.py (v4.0.3) [Mon Mar 15 17:38:53 2021]:

Connected to TCRD database tcrd6 (schema ver 6.5.1; data ver 6.9.0)

Downloading http://download.jensenlab.org/disease_textmining_mentions.tsv
         to ../data/JensenLab/disease_textmining_mentions.tsv

Downloading http://download.jensenlab.org/human_textmining_mentions.tsv
         to ../data/JensenLab/human_textmining_mentions.tsv

Parsing Disease Ontology file ../data/DiseaseOntology/doid.obo
  Got 13109 Disease Ontology terms

Generating TIN-X TSV files. See logfile ../log/tcrd6logs/tin-x.py.log for details.

Protein mappings: 18982 protein to PMIDs ; 5629238 PMID to protein counts. Elapsed time: 0:03:27.682
Disease mappings: 8960 disease to PMIDs ; 11988736 PMID to disease counts. Elapsed time: 0:02:09.391
Wrote 18983 lines to file ../data/TIN-X/TCRDv6/ProteinNovelty.tsv. Elapsed time: 0:00:09.521
Wrote 8961 lines to file ../data/TIN-X/TCRDv6/DiseaseNovelty.tsv. Elapsed time: 0:00:52.832
Wrote 13800891 lines to file ../data/TIN-X/TCRDv6/Importance.tsv. Elapsed time: 0:30:49.986
Wrote 418949227 lines (3318131 total TIN-x PMIDs) to file ../data/TIN-X/TCRDv6/PMIDRanking.tsv. Elapsed time: 0:48:25.428
Fetching pubmed data for 11158 new TIN-X PMIDs
11108 lines written to file ../data/TIN-X/TCRDv6/TINX_Pubmed.tsv. Elapsed time: 0:04:47.331

tin-x.py: Done. Total time: 1:32:56.907


(venv) [smathias@juniper python]$ ./load-TIN-X.py --dbname tcrd6

load-TIN-X.py (v4.1.0) [Tue Mar 16 10:08:54 2021]:

Connected to TCRD database tcrd6

Deleting old dataset/provenance (if any): Done.

Dropping old tinx tables: Done.

Creating new tinx tables: Done.

Loading tinx tables...
  Loading tinx_novelty: OK - (18982 rows).  Elapsed time: 0:00:00.367
  Loading tinx_disease: OK - (8960 rows).  Elapsed time: 0:00:00.211
  Loading tinx_importance: OK - (13800890 rows).  Elapsed time: 0:15:13.936
  Loading tinx_articlerank: OK - (418949226 rows).  Elapsed time: 12:07:35.445
Done.

Loading TIN-X pubmeds from ../data/TIN-X/TCRDv6/TINX_Pubmed.tsv...
Progress: [##################################################] 99.5% 
  Processed 11058 lines. Inserted 11015 pubmed rows. Elapsed time: 0:00:09.514
  WARNING: 42 errors occurred. See logfile ../log/tcrd6logs/load-TIN-X.py.log for details.
Done.

Loading dataset and provenance: Done.

load-TIN-X.py: Done. Total time: 12:23:01.835

mysql> UPDATE dbinfo SET schema_ver = '6.5.1', data_ver = '6.9.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.9.0.sql


# GlyGen extlinks

CREATE TABLE `extlink` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `source` enum('GlyGen', 'Prokino', 'Dark Kinome', 'Reactome', 'ClinGen', 'GENEVA', 'TIGA') COLLATE utf8_unicode_ci NOT NULL,
  `url` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `extlink_idx1` (`protein_id`),
  CONSTRAINT `fk_extlink_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;


(venv) [smathias@juniper python]$ ./load-ExtLinks.py --dbname tcrd6 --loglevel 20 2> ../log/tcrd6logs/extlink_xx

load-ExtLinks.py (v1.1.0) [Fri Mar 19 14:45:34 2021]:

Connected to TCRD database tcrd6 (schema ver 6.5.1; data ver 6.9.0)

Checking/Loading GlyGen ExtLinks for 20412 TCRD proteins
Progress: [##################################################] 100.0% Done.
Processed 20412 TCRD proteins.
Inserted 20225 new GlyGen extlink rows.
No GlyGen record found for 187 TCRD UniProts. See logfile ../log/tcrd6logs//load-ExtLinks.py.log for details.

load-ExtLinks.py: Done. Elapsed time: 4:20:34.396


mysql> UPDATE dbinfo SET schema_ver = '6.6.0', data_ver = '6.9.1';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.9.1.sql


## Fix TIGA
## Files used previously (in ~/TCRD/data/TIGA/bad-old-files/) are junk

mysql> delete from provenance where dataset_id = (select id from dataset where name = 'TIGA');
Query OK, 2 rows affected (0.01 sec)
mysql> delete from dataset where name = 'TIGA';
Query OK, 1 row affected (0.04 sec)

mysql> delete from tiga_provenance;
Query OK, 167811 rows affected (0.39 sec)
mysql> delete from tiga;
Query OK, 102407 rows affected (0.45 sec)

mysql> alter table tiga AUTO_INCREMENT = 1;
mysql> alter table tiga_provenance AUTO_INCREMENT = 1;

(venv) [smathias@juniper python]$ ./load-TIGA.py --dbname tcrd6

load-TIGA.py (v2.0.0) [Thu Apr  1 16:50:28 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.0; data ver 6.9.1)

Downloading https://unmtid-shinyapps.net/download/TIGA/tiga_gene-trait_stats.tsv
         to ../data/TIGA/tiga_gene-trait_stats.tsv

Downloading https://unmtid-shinyapps.net/download/TIGA/tiga_gene-trait_provenance.tsv
         to ../data/TIGA/tiga_gene-trait_provenance.tsv

Processing 55463 lines in TIGA file ../data/TIGA/tiga_gene-trait_stats.tsv
Progress: [##################################################] 100.0% Done.
Processed 55463 lines
  Inserted 171464 new tiga rows for 9615 proteins

Processing 78517 lines in TIGA provenance file ../data/TIGA/tiga_gene-trait_provenance.tsv
Progress: [##################################################] 100.0% Done.
Processed 78517 lines
  Inserted 78516 new tiga_provenance rows

load-TIGA.py: Done. Elapsed time: 0:04:42.187

# Add TIGA extinks (not re-doing GlyGen ones) #
# output not shown #

mysql> UPDATE dbinfo SET schema_ver = '6.6.1', data_ver = '6.9.2';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.9.2.sql




### "Auto Update" Jensen Lab Resources ###

mysql> update dataset set name = 'JensenLab DISEASES' where name = 'Jensen Lab DISEASES';
mysql> update dataset set name = 'JensenLab TISSUES' where name = 'Jensen Lab TISSUES';
mysql> update dataset set name = 'JensenLab COMPARTMENTS' where name = 'Jensen Lab COMPARTMENTS';
mysql> INSERT INTO disease_type (name, description) VALUES ('JensenLab Knowledge AmyCo', 'JensenLab Knowledge channel using AmyCo');

(venv) [smathias@juniper python]$ ./update-JensenLab.py --dbname tcrd6

update-JensenLab.py (v1.0.0) [Tue Apr 13 12:47:48 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.1; data ver 6.9.2)

Downloading new JensenLab files...
Downloading http://download.jensenlab.org/KMC/protein_counts.tsv
         to ../data/JensenLab/protein_counts.tsv
Downloading http://download.jensenlab.org/human_disease_knowledge_filtered.tsv
         to ../data/JensenLab/human_disease_knowledge_filtered.tsv
Downloading http://download.jensenlab.org/human_disease_experiments_filtered.tsv
         to ../data/JensenLab/human_disease_experiments_filtered.tsv
Downloading http://download.jensenlab.org/human_disease_textmining_filtered.tsv
         to ../data/JensenLab/human_disease_textmining_filtered.tsv

Updating JensenLab PubMed Text-mining Scores...
  Deleted 415210 rows from pmscore
  Reset 18982 'JensenLab PubMed Score' tdl_info values to zero.
Processing 414728 lines in file ../data/JensenLab/protein_counts.tsv
Progress: [##################################################] 100.0% Done.
414728 input lines processed.
  Inserted 415210 new pmscore rows for 18982 proteins
  No protein found for 309 STRING IDs. See logfile ../log/tcrd6logs//update-JensenLab.py.log for details.
Loading 18982 JensenLab PubMed Score tdl_infos
  Inserted 18982 new JensenLab PubMed Score tdl_info rows

Updating JensenLab DISEASES...
  Deleted 12465 JensenLab rows from disease
Processing 7526 lines in DISEASES Knowledge file ../data/JensenLab/human_disease_knowledge_filtered.tsv
Progress: [##################################################] 100.0% Done.
7526 lines processed.
  Inserted 8020 new disease rows for 3805 proteins
  Skipped 38 rows w/o ENSP
  No target found for 10 stringids/symbols. See logfile ../log/tcrd6logs//update-JensenLab.py.log for details.
Processing 24102 lines in DISEASES Experiment file ../data/JensenLab/human_disease_experiments_filtered.tsv
Progress: [##################################################] 100.0% Done.
24102 lines processed.
  Inserted 17412 new disease rows for 11268 proteins
  No target found for 49 stringids/symbols. See logfile ../log/tcrd6logs//update-JensenLab.py.log for details.
WARNING: 7846 DB errors occurred. See logfile ../log/tcrd6logs//update-JensenLab.py.log for details.
Processing 179269 lines in DISEASES Textmining file ../data/JensenLab/human_disease_textmining_filtered.tsv
Progress: [##################################################] 100.0% Done.
179269 lines processed.
  Inserted 4432 new disease rows for 2211 proteins
  Skipped 174924 rows w/o ENSP or with confidence < 3
  No target found for 14 stringids/symbols. See logfile ../log/tcrd6logs//update-JensenLab.py.log for details.

update-JensenLab.py: Done. Elapsed time: 0:12:55.122


# TDLs
(venv) [smathias@juniper python]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v4.0.0) [Tue Apr 13 13:12:24 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.1; data ver 6.9.2)

Set target.tdl to NULL for 20412 rows

Deleted previous 'TDLs' dataset

Calculating/Loading TDLs for 20412 TCRD targets
Progress: [##################################################] 100.0% Done.
20412 TCRD targets processed.
Set TDL value for 20412 targets:
  659 targets are Tclin
  1607 targets are Tchem
  9938 targets are Tbio - 1211 bumped from Tdark
  8208 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:02:10.582

mysql> UPDATE dbinfo SET schema_ver = '6.6.2', data_ver = '6.10.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.10.0.sql

# New TDLs for this version, so export mapping file for UniProt
(venv) [smathias@juniper python]$ ./exp-UniProts.py 

exp-UniProts.py (v1.1.0) [Tue Apr 13 13:52:20 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.2; data ver 6.10.0)

Exporting UniProts/TDLs for 20412 TCRD targets
Progress: [##################################################] 100.0% Done.
Wrote 20412 lines to file /usr/local/apache2/htdocs/tcrd/download/PharosTCRD_UniProt_Mapping.tsv

exp-UniProts.py: Done. Elapsed time: 0:00:00.603


mysql> use tcrd
mysql> delete from tdl_info where itype = 'JensenLab PubMed Score' and number_value = 0.0;
Query OK, 57439 rows affected (4.77 sec)

mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/home/data/mysqlfiles/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';

Edit that to create InsMissingJLPMSs_TCRDv6.10.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /home/data/mysqlfiles/nojlpms.csv > InsZeroJLPMSs_TCRDv6.10.sql
Edit InsZeroJLPMSs_TCRDv6.10.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv6.10.sql

(venv) [smathias@juniper python]$ ./load-TDLs.py --dbname tcrd

load-TDLs.py (v4.0.0) [Thu Apr 22 12:17:02 2021]:

Connected to TCRD database tcrd (schema ver 6.6.2; data ver 6.10.0)

Set target.tdl to NULL for 20412 rows

Deleted previous 'TDLs' dataset

Calculating/Loading TDLs for 20412 TCRD targets
Progress: [##################################################] 100.0% Done.
20412 TCRD targets processed.
Set TDL value for 20412 targets:
  659 targets are Tclin
  1607 targets are Tchem
  12139 targets are Tbio - 491 bumped from Tdark
  6007 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:02:07.935


mysql> UPDATE dbinfo SET data_ver = '6.11.0';

[smathias@juniper SQL]$ mysqldump tcrd > dumps6/TCRDv6.11.0.sql


# ChEMBL 28

(venv) [smathias@juniper python]$ ./load-ChEMBL.py --dbname tcrd6

load-ChEMBL.py (v6.0.0) [Tue Apr 27 13:32:52 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.2; data ver 6.11.0)
Connected to ChEMBL database chembl_28

Deleting existing ChEMBL data...
  Deleted 489802 ChEMBL cmpd_activity rows
  Deleted 1791 'ChEMBL First Reference Year' tdl_info rows
  Deleted 755 'ChEMBL Selective Compound' tdl_info rows
  
Downloading ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to ../data/ChEMBL/chembl_uniprot_mapping.txt

Processing 12936 input lines in mapping file ../data/ChEMBL/chembl_uniprot_mapping.txt
Progress: [##################################################] 100.0% Done.
  Got 8520 UniProt to ChEMBL 'SINGLE PROTEIN' mappings

Processing 8520 UniProt accessions in up2chembl
Progress: [##################################################] 100.0% Done.
8520 UniProt accessions processed.
  No TCRD target found for 4588 UniProt accessions. See logfile ../log/tcrd6logs/load-ChEMBL.py.log for details.
  1829 targets have no qualifying activities in ChEMBL
Inserted 536695 new cmpd_activity rows
Inserted 2024 new 'ChEMBL First Reference Year' tdl_info rows

Running selective compound analysis...
  Found 20244 selective compounds
Inserted 896 new 'ChEMBL Selective Compound' tdl_info rows

load-ChEMBL.py: Done. Elapsed time: 0:19:37.262

# TDLs
(venv) [smathias@juniper python]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v4.1.0) [Tue Apr 27 15:16:34 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.2; data ver 6.11.0)

Set tdl to NULL for 0 target rows

Deleted previous 'TDLs' dataset

Calculating/Loading TDLs for 20412 TCRD targets
Progress: [##################################################] 100.0% Done.
20412 TCRD targets processed.
Set TDL value for 20412 targets:
  659 targets are Tclin
  1850 targets are Tchem
  11911 targets are Tbio - 486 bumped from Tdark
  5992 targets are Tdark

load-TDLs.py: Done. Elapsed time: 0:02:01.736




(venv) [smathias@juniper python]$ ./load-ChEMBL.py --dbname tcrd6

load-ChEMBL.py (v6.1.0) [Thu May  6 12:19:44 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.2; data ver 6.12.0)
Connected to ChEMBL database chembl_28

Deleting existing ChEMBL data...
  Deleted 0 'ChEMBL' cmpd_activity rows
  Deleted 0 'ChEMBL First Reference Year' tdl_info rows
  Deleted 0 'ChEMBL Selective Compound' tdl_info rows

Processing 12936 input lines in mapping file ../data/ChEMBL/chembl_uniprot_mapping.txt
Progress: [##################################################] 100.0% Done.
  Got 8520 UniProt to ChEMBL 'SINGLE PROTEIN' mappings

Processing 8520 UniProt accessions in up2chembl
Progress: [##################################################] 100.0% Done.
8520 UniProt accessions processed.
  No TCRD target found for 4588 UniProt accessions. See logfile ../log/tcrd6logs/load-ChEMBL.py.log for details.
  1771 targets have no qualifying activities in ChEMBL
Inserted 594355 new cmpd_activity rows
Inserted 2061 new 'ChEMBL First Reference Year' tdl_info rows

Running selective compound analysis...
  Found 23225 selective compounds
Inserted 930 new 'ChEMBL Selective Compound' tdl_info rows

load-ChEMBL.py: Done. Elapsed time: 0:28:07.730


(venv) [smathias@juniper python]$ ./load-TDLs.py --dbname tcrd6

load-TDLs.py (v4.2.0) [Thu May  6 13:51:20 2021]:

Connected to TCRD database tcrd6 (schema ver 6.6.2; data ver 6.12.0)

Set tdl to NULL for 20412 target rows

Deleted previous 'TDLs' dataset

Calculating/Loading TDLs for 20412 TCRD targets
Progress: [##################################################] 100.0% Done.
20412 TCRD targets processed.
Set TDL value for 20412 targets:
  659 targets are Tclin
  1883 targets are Tchem
  11878 targets are Tbio - 486 bumped from Tdark
  5992 targets are Tdark

Exporting UniProts/TDLs for 20412 TCRD targets
Progress: [##################################################] 100.0% Done.
Wrote 20412 lines to file /usr/local/apache2/htdocs/tcrd/download/old_versions/PharosTCRDv6.12_UniProt_Mapping.tsv

load-TDLs.py: Done. Elapsed time: 0:02:05.856

mysql> UPDATE dbinfo SET data_ver = '6.12.0';

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/TCRDv6.12.0.sql



# Ontologies

DROP TABLE mpo;
CREATE TABLE `mpo` (
  `mpoid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  `comment` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`mpoid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `mpo_parent` (
  `mpoid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `parentid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  KEY `mpo_parent_idx1` (`mpoid`),
  CONSTRAINT `fk_mpo_parent__mpo` FOREIGN KEY (`mpoid`) REFERENCES `mpo` (`mpoid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `mpo_xref` (
  `mpoid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `db` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`mpoid`,`db`,`value`),
  KEY `mpo_xref_idx1` (`mpoid`),
  CONSTRAINT `fk_mpo_xref__mpo` FOREIGN KEY (`mpoid`) REFERENCES `mpo` (`mpoid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `mondo` (
  `mondoid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  `comment` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`mondoid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `mondo_parent` (
  `mondoid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `parentid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  KEY `mondo_parent_idx1` (`mondoid`),
  CONSTRAINT `fk_mondo_parent__mondo` FOREIGN KEY (`mondoid`) REFERENCES `mondo` (`mondoid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `mondo_xref` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `mondoid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `db` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `source_info` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `mondo_xref_idx1` (`mondoid`),
  -- UNIQUE KEY `mondo_xref_idx2` (`mondoid`,`db`,`value`),
  CONSTRAINT `fk_mondo_xref__mondo` FOREIGN KEY (`mondoid`) REFERENCES `mondo` (`mondoid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;





#
# Other unresolved issues
#
mysql> select protein_id, count(*) as c from tdl_info group by protein_id order by c DESC limit 5;
+------------+-------+
| protein_id | c     |
+------------+-------+
|        121 | 15986 |
|       NULL |  2546 |
|      13062 |    39 |
|       1184 |    38 |
|      13073 |    33 |
+------------+-------+
mysql> select itype, count(*)  from tdl_info where protein_id = 121 group by itype;
+--------------------------------------+----------+
| itype                                | count(*) |
+--------------------------------------+----------+
| Ab Count                             |        1 |
| Antibodypedia.com URL                |        1 |
| HPA Tissue Specificity Index         |        1 |
| HPM Gene Tissue Specificity Index    |    15976 |
| HPM Protein Tissue Specificity Index |        1 |
| JensenLab PubMed Score               |        1 |
| MAb Count                            |        1 |
| NCBI Gene PubMed Count               |        1 |
| PubTator Score                       |        1 |
| TMHMM Prediction                     |        1 |
| UniProt Function                     |        1 |
+--------------------------------------+----------+
mysql> select itype, count(*)  from tdl_info where protein_id = 13062 group by itype;
+--------------------------------------+----------+
| itype                                | count(*) |
+--------------------------------------+----------+
| Ab Count                             |        1 |
| Antibodypedia.com URL                |        1 |
| EBI Total Patent Count               |        1 |
| Experimental MF/BP Leaf Term GOA     |        1 |
| HPM Protein Tissue Specificity Index |       28 |
| JensenLab PubMed Score               |        1 |
| MAb Count                            |        1 |
| NCBI Gene PubMed Count               |        1 |
| NCBI Gene Summary                    |        1 |
| PubTator Score                       |        1 |
| TMHMM Prediction                     |        1 |
| UniProt Function                     |        1 |
+--------------------------------------+----------+
mysql> select itype, number_value from tdl_info where itype = 'HPM Protein Tissue Specificity Index' and protein_id = 13062;
+--------------------------------------+--------------+
| itype                                | number_value |
+--------------------------------------+--------------+
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.913793 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.958621 |
| HPM Protein Tissue Specificity Index |     0.958621 |
+--------------------------------------+--------------+


