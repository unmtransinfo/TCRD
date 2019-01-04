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

New tables and changes to support metapath are in SQL/tcrdmp.sql

Fix the GPR89s:
GPR89A/B each have two Gene IDs in UniProt. According to NCBI, GPR89B is 51463. Fix this manually:
mysql> select id, name, description, sym, uniprot, geneid from protein where sym like 'GPR89%';
+-------+-------------+----------------------+--------+---------+--------+
| id    | name        | description          | sym    | uniprot | geneid |
+-------+-------------+----------------------+--------+---------+--------+
| 10748 | GPHRB_HUMAN | Golgi pH regulator B | GPR89B | P0CG08  | 653519 |
| 10839 | GPHRA_HUMAN | Golgi pH regulator A | GPR89A | B7ZAQ6  | 653519 |
+-------+-------------+----------------------+--------+---------+--------+
mysql> UPDATE protein SET geneid = 51463 WHERE sym = 'GPR89B';

Fix the Medium-wave-sensitive opsins:
mysql> select id, name, description, sym, uniprot, geneid from protein where name like 'OPSG%';
+-------+-------------+-------------------------------+---------+---------+--------+
| id    | name        | description                   | sym     | uniprot | geneid |
+-------+-------------+-------------------------------+---------+---------+--------+
| 17443 | OPSG_HUMAN  | Medium-wave-sensitive opsin 1 | OPN1MW  | P04001  | 728458 |
| 17321 | OPSG2_HUMAN | Medium-wave-sensitive opsin 2 | OPN1MW2 | P0DN77  | 728458 |
| 17263 | OPSG3_HUMAN | Medium-wave-sensitive opsin 3 | OPN1MW3 | P0DN78  | 728458 |
+-------+-------------+-------------------------------+---------+---------+--------+
mysql> select id, name, idg2, fam, famext from target where id in (17443, 17321, 17263);
+-------+-------------------------------+------+------+--------+
| id    | name                          | idg2 | fam  | famext |
+-------+-------------------------------+------+------+--------+
| 17263 | Medium-wave-sensitive opsin 3 |    0 | NULL | NULL   |
| 17321 | Medium-wave-sensitive opsin 2 |    0 | NULL | NULL   |
| 17443 | Medium-wave-sensitive opsin 1 |    0 | NULL | NULL   |
+-------+-------------------------------+------+------+--------+

UPDATE protein SET geneid = 2652 WHERE id = 17443;
UPDATE protein set geneid = 101060233 WHERE id =17263 ;
-- UPDATE target set fam = 'GPCR', famext = 'GPCR' WHERE id in (17443, 17321, 17263);

[smathias@juniper SQL]$ mysqldump tcrd6 > dumps6/tcrd6-1.sql


