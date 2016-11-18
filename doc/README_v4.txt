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

[smathias@juniper scripts]$ ./load-UniProt.py --dbname tcrd4 --loglevel 20 --logfile tcrd4logs/load-UniProt.py.l
og

load-UniProt.py (v2.0.0) [Thu Nov 17 12:53:11 2016]:

Connected to TCRD database tcrd4 (schema ver 4.0.0; data ver 4.0.0)

Processing 20120 records in UniProt file ../data/UniProt/uniprot-human-reviewed_20161116.tab

Loading data for 20120 proteins
Progress: 100% [################################################################################] Time: 21:33:36
Processed 20120 UniProt records.
  Total loaded targets/proteins: 20061
  Total targets/proteins remaining for retries: 59 

Retry loop 1: Trying to load data for 59 proteins
Progress: 100% [#################################################################################] Time: 0:01:25
Processed 30 UniProt records.
  Loaded 30 new targets/proteins
  Total loaded targets/proteins: 20091
  Total targets/proteins remaining for next loop: 29 

Retry loop 2: Trying to load data for 29 proteins
Progress: 100% [#################################################################################] Time: 0:01:11
Processed 15 UniProt records.
  Loaded 15 new targets/proteins
  Total loaded targets/proteins: 20106
  Total targets/proteins remaining for next loop: 14 

Retry loop 3: Trying to load data for 14 proteins
Progress: 100% [#################################################################################] Time: 0:00:36
Processed 7 UniProt records.
  Loaded 7 new targets/proteins
  Total loaded targets/proteins: 20113
  Total targets/proteins remaining for next loop: 7 

Retry loop 4: Trying to load data for 7 proteins
Progress: 100% [#################################################################################] Time: 0:00:13
Processed 4 UniProt records.
  Loaded 4 new targets/proteins
  Total loaded targets/proteins: 20117
  Total targets/proteins remaining for next loop: 3 

Retry loop 5: Trying to load data for 3 proteins
Progress: 100% [#################################################################################] Time: 0:00:02
Processed 2 UniProt records.
  Loaded 2 new targets/proteins
  Total loaded targets/proteins: 20119
  Total targets/proteins remaining for next loop: 1 

Retry loop 6: Trying to load data for 1 proteins
Progress: 100% [#################################################################################] Time: 0:00:01
Processed 1 UniProt records.
  Loaded 1 new targets/proteins
  Total loaded targets/proteins: 20120

load-UniProt.py: Done. Elapsed time: 21:37:07.399

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-1.sql


[smathias@juniper scripts]$ ./pickle-IDGFams.py --dbname tcrd3 --outfile ../tcrd/TCRDv3.1.2_IDGFams.p

pickle-IDGFams.py (v1.3.0) [Wed Nov 16 13:25:49 2016]:
  Connected to TCRD database tcrd3 (schema ver: 1.5.0, data ver: 3.1.2)
  Dumping TCRD IDG Families for 1795 targets
Progress: 100% [###########################################################] Time: 0:00:02
1795 TCRD targets processed. Elapsed time: 0:00:02.068
Saving info for following IDG Family counts to pickle file ../tcrd/TCRDv3.1.2_IDGFams.p
  IC: 342
  GPCR: 406
  NR: 48
  oGPCR: 421
  Kinase: 578

pickle-IDGFams.py: Done.

[smathias@juniper scripts]$ ./load-IDGFams.py --dbname tcrd4 --infile
../tcrd/TCRDv3.1.2_IDGFams.p




mysql> \. InsAbCts_v4.sql
INSERT INTO dataset (name, app, app_version, source) VALUES ('Aintibodypedia.com', 'Antibodypedia2SQL.py', '2.0.0', 'API at http://www.antibodypedia.com/tools/antibodies.php');
SELECT id FROM dataset WHERE name = 'Aintibodypedia.com';
INSERT INTO provenance ('dataset_id', 'table_name', 'where_clause') VALUES (, 'tdl_info', "itype = 'Ab Count'");
INSERT INTO provenance ('dataset_id', 'table_name', 'where_clause') VALUES (, 'tdl_info', "itype = 'MAb Count'");
INSERT INTO provenance ('dataset_id', 'table_name', 'where_clause') VALUES (, 'tdl_info', "itype = 'Antibodypedia URL'");
