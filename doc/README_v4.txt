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


GPR89A/B each have two Gene IDs in UniProt. Accordnig to NCBI, GPR89B is 51463. Fix this amnually:
mysql> UPDATE protein SET geneid = 51463 WHERE sym = 'GPR89B';

[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-1.sql


[smathias@juniper loaders]$ ./load-GIs.py --dbname tcrd4



[smathias@juniper SQL]$ mysqldump tcrd4 > dumps/tcrd4-2.sql

