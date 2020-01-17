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


