This README includes all commands (and most output) run to build TCRD v4.

[smathias@juniper SQL]$ mysqldump --no-data tcrd3 | sed 's/ AUTO_INCREMENT=[0-9]*\b//g' > create-TCRDv4.sql
[smathias@juniper SQL]$ mysqldump --no-create-db --no-create-info tcrd3 compartment_type data_type disease_association_type expression_type info_type pathway_type phenotype_type ppi_type xref_type > types_v4.sql
mysql> create database tcrd4;
mysql> use tcrd4
Edit create-TCRDv4.sql to rename disease and grant and add protein_id foreign keys to both
mysql> \. create-TCRDv4.sql
mysql> \. types_v4.sql
Check that everything is good:
mysql> SHOW TABLE STATUS FROM `tcrd4`;

ALTER TABLE dataset DROP COLUMN columns_touched;
CREATE TABLE provenance (
  id                    INTEGER(11) NOT NULL AUTO_INCREMENT,
  dataset_id            INTEGER(11) NOT NULL,
  table_name            VARCHAR(255) NOT NULL,
  column_name           VARCHAR(255) NULL,
  where_clause          TEXT NULL,
  comment               TEXT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;
CREATE INDEX provenance_idx1 ON provenance(dataset_id);
ALTER TABLE provenance ADD CONSTRAINT fk_provenance_dataset FOREIGN KEY
provenance_idx1(dataset_id) REFERENCES dataset(id) ON DELETE RESTRICT; -- provenance must have a dataset
INSERT INTO dataset (name, source) VALUES ('IDG-KMC Generated Data', 'Steve Mathias');
INSERT INTO dataset (name, source) VALUES ('IDG-KMC Generated Data', 'Oleg Ursu');
INSERT INTO dataset (name, source) VALUES ('IDG-KMC Generated Data', 'Lars Jensen');
ALTER TABLE xref ADD COLUMN dataset_id INTEGER(11) NOT NULL;
CREATE INDEX xref_idx6 ON xref(dataset_id);
ALTER TABLE xref ADD CONSTRAINT fk_xref_dataset FOREIGN KEY xref_idx6(dataset_id) REFERENCES dataset(id) ON DELETE RESTRICT; -- xrefs must have a dataset
ALTER TABLE alias ADD COLUMN dataset_id INTEGER(11) NOT NULL;
CREATE INDEX alias_idx2 ON alias(dataset_id);
ALTER TABLE alias ADD CONSTRAINT fk_alias_dataset FOREIGN KEY alias_idx2(dataset_id) REFERENCES dataset(id) ON DELETE RESTRICT; -- aliases must have a dataset
DROP TABLE synonym;
INSERT INTO dbinfo (dbname, schema_ver, data_ver, owner) VALUES ('tcrd4', '4.0.0', '4.0.0', 'smathias');

[smathias@juniper SQL]$ mysqldump tcrd4 > tcrd4-0.sql


[smathias@juniper loaders]$ ./load-UniProt.py --dbname tcrd4 --loglevel 20 --logfile tcrd4logs/load-UniProt.py.log

load-UniProt.py (v2.0.0) [Tue Nov 29 15:16:01 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 20120 records in UniProt file ../data/UniProt/uniprot-human-reviewed_20161116.tab

Loading data for 20120 proteins
Progress: 100% [####################################################################] Time: 15:35:54
Processed 20120 UniProt records.
  Total loaded targets/proteins: 20078
  Total targets/proteins remaining for retries: 42 

Retry loop 1: Trying to load data for 42 proteins
Progress: 100% [#####################################################################] Time: 0:01:55
Processed 42 UniProt records.
  Loaded 42 new targets/proteins
  Total loaded targets/proteins: 20120

load-UniProt.py: Done. Elapsed time: 15:37:49.734

GPR89A/B each have two Gene IDs in UniProt. Accordnig to NCBI, GPR89B is 51463. Fix this amnually:
mysql> UPDATE protein SET geneid = 51463 WHERE sym = 'GPR89B';

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-1.sql


[smathias@juniper loaders]$ ./load-GIs.py --dbname tcrd4

load-GIs.py (v2.0.0) [Wed Nov 30 09:47:17 2016]:

Downloading  ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping_selected.tab.gz
         to  ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Uncompressing ../data/UniProt/HUMAN_9606_idmapping_selected.tab.gz
Done. Elapsed time: 0:01:30.376

load-GIs.py (v2.0.0) [Wed Nov 30 09:48:47 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 156576 rows in file ../data/UniProt/HUMAN_9606_idmapping_selected.tab
Progress: 100% [#####################################################################] Time: 0:03:44

156576 rows processed. Elapsed time: 0:03:44.992
20116 targets annotated with GI xref(s)
  Skipped 136460 rows
  Inserted 256791 new GI xref rows

load-GIs.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-2.sql


[smathias@juniper loaders]$ ./load-HGNC.py --dbname tcrd4 --loglevel 20 --logfile tcrd4logs/load-HGNC.py.log

load-HGNC.py (v2.0.0) [Wed Nov 30 17:09:28 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Loading HGNC annotations for 20120 TCRD targets
Progress: 100% [####################################################################] Time: 17:04:45
Processed 20120 targets.
Loaded HGNC annotations for 19874 targets
Total targets remaining for retries: 24 

Retry loop 1: Loading HGNC annotations for 24 TCRD targets
Progress: 100% [#####################################################################] Time: 0:01:20
Processed 24 targets.
  Annotated 24 additional targets
  Total annotated targets: 19898

Updated/Inserted 19898 HGNC ID xrefs
Inserted 2 new protein.sym values
Updated 228 discrepant protein.sym values
Updated/Inserted 19898 protein.chr values
Updated/Inserted 1036 protein.geneid values
Updated/Inserted 17472 MGI ID xrefs
WARNNING: 222 targets did not find an HGNC record.

load-HGNC.py: Done. Elapsed time: 17:06:05.571


[smathias@juniper loaders]$ ./load-STRINGIDs.py --dbname tcrd4

load-STRINGIDs.py (v2.0.0) [Thu Dec  1 10:36:49 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 20499 input lines in file /home/app/TCRD/data/JensenLab/9606_reviewed_uniprot_2_string.04_2015.tsv
Progress: 100% [#####################################################################] Time: 0:00:00
20499 input lines processed. Elapsed time: 0:00:00.071
  Skipped 2397 non-identity lines
  Got 35046 uniprot/name to STRING ID mappings

Processing 2449433 input lines in file /home/app/TCRD/data/JensenLab/9606.protein.aliases.v10.txt
Progress: 100% [#####################################################################] Time: 0:00:15
2449433 input lines processed. Elapsed time: 0:00:15.872
  Got 2166722 alias to STRING ID mappings
  249170 alias errors occurred. See logfile load-STRINGIDs.py.log for details.

Loading STRING IDs for 20120 TCRD targets
Progress: 100% [#####################################################################] Time: 0:34:57
  Updated 19267 STRING ID values

load-STRINGIDs.py: Done.


[smathias@juniper loaders]$ ./load-Antibodypedia.py --dbname tcrd4 --logfile tcrd4logs/load-Antibodypedia.py.log

load-Antibodypedia.py (v2.0.0) [Wed Nov 30 17:09:39 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Loading Antibodypedia annotations for 20120 TCRD targets
Progress: 100% [##############################################################] Time: 1 day, 12:01:06
20120 TCRD targets processed.
  Inserted 20120 Ab Count tdl_info rows
  Inserted 40240 MAb Count tdl_info rows
  Inserted 20120 Antibodypedia URL tdl_info rows

load-Antibodypedia.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-3.sql


[smathias@juniper loaders]$ ./load-NCBIGene.py --dbname tcrd4 --loglevel 20 --logfile tcrd4logs/load-NCBIGene.py.log

load-NCBIGene.py (v2.0.0) [Tue Dec  6 10:38:51 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Loading NCBI Gene annotations for 20120 TCRD targets

Progress: 100% [###############################################################] Time: 1 day, 8:45:13
Processed 20120 targets.
Skipped 189 targets with no geneid
Loaded NCBI annotations for 19931 targets

Inserted 51395 aliases
Inserted 12556 NCBI Gene Summary tdl_infos
Inserted 19931 NCBI Gene PubMed Count tdl_infos
Inserted 617026 GeneRIFs
Inserted 1055342 PubMed xrefs
Inserted 69513 other xrefs

load-NCBIGene.py: Done. Elapsed time: 32:45:13.656

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-4.sql


[smathias@juniper loaders]$ ./load-JensenLabPubMedScores.py --dbname tcrd4

load-JensenLabPubMedScores.py (v2.0.0) [Thu Dec  8 10:35:42 2016]:

Downloading  http://download.jensenlab.org/KMC/Medline/protein_counts.tsv
         to  ../data/JensenLab/protein_counts.tsv
Done. Elapsed time: 0:00:08.446

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 346948 input lines in file ../data/JensenLab/protein_counts.tsv
Progress: 100% [#####################################################################] Time: 0:04:52
346948 input lines processed. Elapsed time: 0:04:52.450
  17387 targets have JensenLab PubMed Scores
  Inserted 332399 new pmscore rows
No target found for 480 STRING IDs. Saved to file: tcrd4logs/protein_counts_not-found.db

Loading 17387 JensenLab PubMed Score tdl_infos
  17387 processed
  Inserted 17387 new JensenLab PubMed Score tdl_info rows

load-JensenLabPubMedScores.py: Done.

mysql> select id from protein where id not in (select distinct protein_id from tdl_info where itype = 'JensenLab PubMed Score') INTO OUTFILE '/tmp/nojlpms.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';
Edit that to create InsMissingJLPMSs_TCRDv4.sql:
[smathias@juniper SQL]$ perl -ne '/^(\d+)/ && print "INSERT INTO tdl_info (protein_id, itype, number_value) VALUES ($1, 'JLPMS', 0);\n"' /tmp/nojlpms.csv > InsZeroJLPMSs_TCRDv4.sql
Edit InsZeroJLPMSs_TCRDv4.sql: s/JLPMS/'JensenLab PubMed Score'/
mysql> \. InsZeroJLPMSs_TCRDv4.sql

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-5.sql


[smathias@juniper loaders]$ ./load-DrugCentral.py --dbname tcrd4

load-DrugCentral.py (v2.0.0) [Thu Dec  8 10:43:39 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 1759 input lines in file /home/app/TCRD4/data/DrugCentral/drug_info_11082016.tsv
1759 input lines processed.
Saved 1759 keys in infos map

Processing 3126 lines from DrugDB MOA activities file /home/app/TCRD4/data/DrugCentral/tclin_11082016.tsv
3126 DrugCentral Tclin rows processed.
  Inserted 3126 new drug_activity rows

Processing 600 lines from Non-MOA activities file /home/app/TCRD4/data/DrugCentral/tchem_drugs_11082016.tsv
600 DrugCentral Tchem rows processed.
  Inserted 600 new drug_activity rows

Processing 11063 lines from indications file /home/app/TCRD4/data/DrugCentral/drug_indications_11082016.tsv
11063 DrugCentral indication rows processed.
  Inserted 12496 new target2disease rows
WARNNING: 980 drugs NOT FOUND in activity files:

load-DrugCentral.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-6.sql


[smathias@juniper loaders]$ ./load-ChEMBL.py --dbname tcrd4

load-ChEMBL.py (v2.0.0) [Thu Dec  8 10:51:22 2016]:

Downloading  ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_uniprot_mapping.txt
         to  ../data/ChEMBL/chembl_uniprot_mapping.txt
Done. Elapsed time: 0:00:03.373

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 9032 input lines in file ../data/ChEMBL/chembl_uniprot_mapping.txt
9032 input lines processed.

Processing 7424 UniProt to ChEMBL ID(s) mappings
Progress: 100% [#####################################################################] Time: 0:13:01
7424 UniProt accessions processed.
  0 targets not found in ChEMBL
  1377 targets have no good activities in ChEMBL
Inserted 448351 new chembl_activity rows
Inserted 1743 new ChEMBL First Reference Year tdl_infos
WARNING: 5 database errors occured. See logfile load-ChEMBL.py.log for details.

Running selective compound analysis...
  Found 16050 selective compounds
Inserted 760 new ChEMBL Selective Compound tdl_infos

load-ChEMBL.py: Done. Elapsed time: 0:13:43.829

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-7.sql


[smathias@juniper loaders]$ ./load-OMIM.py --dbname tcrd4

load-OMIM.py (v2.0.0) [Thu Dec  8 11:06:07 2016]:

Downloading  http://omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/genemap.txt
         to  ../data/OMIM/genemap.txt
Done.

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 16234 lines from input file ../data/OMIM/genemap.txt
Progress: 100% [#####################################################################] Time: 0:01:05
16232 lines processed.
Loaded 3685 OMIM phenotypes for 3644 targets
  Skipped 12453 lines (commented lines and lines with unconfirmed status).
No target found for 1 symbols:
    sym

load-OMIM.py: Done.

[smathias@juniper scripts]$ ./load-GOExptFuncLeafTDLIs.py --dbname tcrd4

load-GOExptFuncLeafTDLIs.py (v2.0.0) [Thu Dec  8 11:13:41 2016]:

Downloading  http://www.geneontology.org/ontology/go.obo
         to  ../data/GO/go.obo

Connected to TCRD database tcrd3 (schema ver 4.0.01; data ver 4.0.0)

load obo file /home/app/TCRD/data/GO/go.obo
45652 nodes imported
Processing 20120 TCRD targets
Progress: 100% [#####################################################################] Time: 0:30:06
20120 TCRD targets processed. Elapsed time: 0:30:09.700
  Inserted 6166 new  tdl_info rows

load-GOExptFuncLeafTDLIs.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-8.sql


[smathias@juniper loaders]$ ./set-TDLs.py --dbname tcrd4

set-TDLs.py (v2.0.0) [Thu Dec  8 11:45:04 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 20120 TCRD targets
Progress: 100% [#####################################################################] Time: 0:30:37
20120 TCRD targets processed. Elapsed time: 0:30:37.756
Set TDL values for 20120 targets
  602 targets are Tclin
  1401 targets are Tchem
  11032 targets are Tbio (873 bumped from Tdark)
  7085 targets are Tdark

set-TDLs.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-9.sql


[smathias@juniper loaders]$ ./load-GWASCatalog.py --dbname tcrd4

load-GWASCatalog.py (v2.0.0) [Fri Dec  9 10:28:59 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 33702 lines from input file /home/smathias/TCRD4/data/EBI/gwas_catalog_v1.0.1-associations_e86_r2016-12-04.tsv
Progress: 100% [#####################################################################] Time: 0:04:00
33702 lines processed.
  Found 16673 GWAS phenotypes for 5176 targets
No target found for 19445 symbols

load-GWASCatalog.py: Done.

[smathias@juniper loaders]$ ./load-IMPC-Phenotypes.py --dbname tcrd4

load-IMPC-Phenotypes.py (v2.0.0) [Fri Dec  9 10:45:14 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 17372 lines from input file /home/app/TCRD/data/IMPC/ALL_genotype_phenotype.csv
Progress: 100% [#####################################################################] Time: 0:07:18
17372 rows processed.
2026 targets annotated with IMPC phenotypes
  Inserted 13781 new phenotype rows
  Inserted 13781 new MGI ID xref rows
No target found for 1084 gene symbols

load-IMPC-Phenotypes.py: Done.

[smathias@juniper loaders]$ ./load-JAXPhenotypes.py --dbname tcrd4

load-JAXPhenotypes.py (v2.0.0) [Fri Dec  9 13:05:37 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 11893 records in MPO file ../data/JAX/VOC_MammalianPhenotype.rpt
  Saved 11892 MPO entries

Processing 18463 lines from input file ../data/JAX/HMD_HumanPhenotype.rpt
Progress: 100% [#####################################################################] Time: 0:03:53
Processed 18463 phenotype records. Elapsed time: 233.007687092
Loaded 56290 new phenotype rows for 9387 distinct proteins
Loaded/Skipped 9456 new MGI xrefs

load-JAXPhenotypes.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-10.sql


[smathias@juniper loaders]$ ./load-JensenLab-DISEASES.py --dbname tcrd4

load-JensenLab-DISEASES.py (v2.0.0) [Mon Dec 12 10:53:26 2016]:

Downloading  http://download.jensenlab.org/human_disease_knowledge_filtered.tsv
         to  ../data/JensenLab/human_disease_knowledge_filtered.tsv

Downloading  http://download.jensenlab.org/human_disease_experiments_filtered.tsv
         to  ../data/JensenLab/human_disease_experiments_filtered.tsv

Downloading  http://download.jensenlab.org/human_disease_textmining_filtered.tsv
         to  ../data/JensenLab/human_disease_textmining_filtered.tsv

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 4602 lines in file ../data/JensenLab/human_disease_knowledge_filtered.tsv
Progress: 100% [#####################################################################] Time: 0:00:48
4602 lines processed. Elapsed time: 0:00:48.436
  2669 targets have disease association(s)
  Inserted 4852 new target2disease rows
No target found for 8 disease association rows. See shelve file: tcrd4logs/load-JensenLab-DISEASES.db

Processing 23987 line in file ../data/JensenLab/human_disease_experiments_filtered.tsv
Progress: 100% [#####################################################################] Time: 0:01:24
23987 lines processed. Elapsed time: 0:01:24.886
  Skipped 16106 zero confidence rows
  4700 targets have disease association(s)
  Inserted 7501 new target2disease rows
No target found for 167 disease association rows. See shelve file: tcrd4logs/load-JensenLab-DISEASES.db

Processing 43987 lines in file ../data/JensenLab/human_disease_textmining_filtered.tsv
Progress: 100% [#####################################################################] Time: 0:07:45
43987 lines processed. Elapsed time: 0:07:45.292
  11727 targets have disease association(s)
  Inserted 43599 new target2disease rows
No target found for 868 disease association rows. See shelve file: tcrd4logs/load-JensenLab-DISEASES.db

load-JensenLab-DISEASES.py: Done.

[smathias@juniper loaders]$ ./load-L1000XRefs.py --dbname tcrd4

load-L1000XRefs.py (v2.0.0) [Mon Dec 12 11:29:42 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 978 rows in file ../data/CMap_LandmarkGenes_n978.csv
Progress: 100% [#####################################################################] Time: 0:00:07

978 rows processed. Elapsed time: 0:00:07.375
977 targets annotated with L1000 xref(s)
  Inserted 977 new L1000 ID xref rows
WARNNING: 1 symbols NOT FOUND in TCRD:
HSPA1A|3303

load-L1000XRefs.py: Done.

mysql> insert into xref (protein_id, xtype, dataset_id, value) values (7573, 'L1000 ID', 20, 'UUUC11D11');

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-11.sql


[smathias@juniper loaders]$ ./load-DrugableEpigenomeTDLInfos.py --dbname tcrd4

load-DrugableEpigenomeTDLInfos.py (v2.0.0) [Mon Dec 12 11:42:02 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing Epigenetic Writers
Processing 63 lines from Protein methyltransferase input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s8.csv
  62 lines processed. Found 62, skipped 0
  Inserted 62 new tdl_info rows
Processing 19 lines from Histone acetyltransferase input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s3.csv
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
Processing 63 lines from Bromodomain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s1.csv
  62 lines processed. Found 62, skipped 0
  Inserted 62 new tdl_info rows
Processing 72 lines from Tudor domain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s10.csv
  71 lines processed. Found 71, skipped 0
  Inserted 71 new tdl_info rows
Processing 30 lines from Methyl-*-binding domain input file /home/smathias/TCRD/data/Epigenetic-RWE/nrd3674-s6.csv
  29 lines processed. Found 29, skipped 0
  Inserted 29 new tdl_info rows

Inserted a total of 532 new Drugable Epigenome Class tdl_infos

load-DrugableEpigenomeTDLInfos.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-12.sql


mysql> update dataset set source = 'Jeremy Yang' where id = 3;

[smathias@juniper loaders]$ ./load-MLPAssayInfo.py --dbname tcrd4

load-MLPAssayInfo.py (v2.0.0) [Mon Dec 12 11:52:00 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 9866 lines in file ../data/PubChem/entrez_assay_summ_mlp_tgt.csv
Progress: 100% [#####################################################################] Time: 1:18:24

9866 rows processed. Elapsed time: 1:18:24.548
  Skipped 5133 non-huamn assay rows
  3842 assays linked to TCRD targets
    3842 linked by GI; 0 linked via EUtils
  No target found for 891 GIs
  810 distinct targets have PubChem MLP assay link(s)

Processing 6822 rows in file ../data/PubChem/entrez_assay_summ_mlp.csv
Progress: 100% [#####################################################################] Time: 0:00:00
Got assay info for 6822 assays. Elapsed time: 0:00:00.048

Loading MLP Assay Info for 810 targets
Progress: 100% [#####################################################################] Time: 0:00:09

810 targets processed. Elapsed time: 0:00:09.200
  Inserted 3842 new mlp_assay_info rows

load-MLPAssayInfo.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-13.sql


[smathias@juniper loaders]$ ./load-IDGFams.py --dbname tcrd4 --infile ../data/TCRDv3.1.2_IDGFams.p 

load-IDGFams.py (v2.0.0) [Tue Dec 13 16:32:27 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Loading 1795 IDF Family designations from pickle file ../data/TCRDv3.1.2_IDGFams.p
Progress: 100% [#####################################################################] Time: 0:00:44
1795 IDG family designations loaded into TCRD. Elapsed time: 0:00:44.184

load-IDGFams.py: Done.

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-14.sql



UPDATE provenance SET comment = "These values indicate that a protein is annotated with a GO leaf term in either the Molecular Function or Biological Process branch with an experimental evidenve code." where id = 31;
UPDATE provenance SET comment = "This data is generated at UNM from PubChem and EUtils data. It has details about targets studied in assays that were part of NIH's Molecular Libraries Program." where id = 40;



# Grant Tagging
[smathias@juniper python]$ ./pickle_grant_info.py 

pickle_grant_info.py (v1.0.0) [Wed Dec 14 15:35:59 2016]:

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

grant_tagger.py (v2.0.0) [Wed Dec 14 15:58:52 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Loading project info from pickle file ../data/NIHExporter/ProjectInfo2000-2015.p

Creating Tagger...

Tagging 83500 projects from 2000
Progress: 100% [#####################################################################] Time: 0:03:30
83500 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 81265 projects from 2001
Progress: 100% [#####################################################################] Time: 0:03:30
81265 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 83423 projects from 2002
Progress: 100% [#####################################################################] Time: 0:03:49
83423 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 61612 projects from 2003
Progress: 100% [#####################################################################] Time: 0:03:39
61612 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 78778 projects from 2004
Progress: 100% [#####################################################################] Time: 0:03:48
78778 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 82209 projects from 2005
Progress: 100% [#####################################################################] Time: 0:04:01
82209 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 81670 projects from 2006
Progress: 100% [#####################################################################] Time: 0:04:06
81670 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 88886 projects from 2007
Progress: 100% [#####################################################################] Time: 0:04:37
88886 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 87922 projects from 2008
Progress: 100% [#####################################################################] Time: 0:04:57
87922 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 98942 projects from 2009
Progress: 100% [#####################################################################] Time: 0:06:16
98942 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

Tagging 93841 projects from 2010
Progress: 100% [#####################################################################] Time: 0:06:24
93841 projects processed. See logfile ../data/NIHExporter/TCRDv4/grant_tagger.py.log for details.

