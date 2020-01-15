-- Table for non-human proteins, corresponding to meatp table:
-- create table protein(
-- protein_id serial primary key,    
-- swissprot varchar(20),            => nhprotein.name
-- accession varchar(10) unique,     => nhprotein.uniprot
-- symbol varchar(30),               => nhprotein.sym
-- name varchar(200),                => nhprotein.description
-- species varchar(40),              => nhprotein.species
-- tax_id int                        => nhprotein.tax_id
-- );
CREATE TABLE `nhprotein` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uniprot` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci DEFAULT NULL,
  `sym` varchar(30) COLLATE utf8_unicode_ci DEFAULT NULL,
  `species` varchar(40) COLLATE utf8_unicode_ci NOT NULL,
  `taxid` int(11) NOT NULL,
  `geneid` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nhprotein_idx1` (`uniprot`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

ALTER TABLE goa ADD COLUMN `assigned_by` varchar(50) DEFAULT NULL;

ALTER TABLE xref ADD COLUMN `nhprotein_id` int(11) DEFAULT NULL;
ALTER TABLE xref ADD CONSTRAINT `fk_xref_nhprotein` FOREIGN KEY (`nhprotein_id`) REFERENCES `nhprotein` (`id`);

INSERT INTO xref_type (name, description) VALUES ('ENSG', 'Ensembl Gene ID');

# Onlologies
DROP table do_parent;
DROP TABLE do;
CREATE TABLE `do` (
  `doid` varchar(12) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`doid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `do_parent` (
  `doid` varchar(12) COLLATE utf8_unicode_ci NOT NULL,
  `parent_id` varchar(12) COLLATE utf8_unicode_ci NOT NULL,
  CONSTRAINT `fk_do_parent__do` FOREIGN KEY (`doid`) REFERENCES `do` (`doid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `do_xref` (
  `doid` varchar(12) COLLATE utf8_unicode_ci NOT NULL,
  `db` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY `do_xref__idx1` (`doid`, `db`, `value`),
  CONSTRAINT `fk_do_xref__do` FOREIGN KEY (`doid`) REFERENCES `do` (`doid`),
  KEY `do_xref__idx2` (`db`, `value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `mpo` (
  `mpid` char(10) COLLATE utf8_unicode_ci NOT NULL,
  `parent_id` varchar(10) COLLATE utf8_unicode_ci NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`mpid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `rdo` (
  `doid` varchar(12) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`doid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `rdo_xref` (
  `doid` varchar(12) COLLATE utf8_unicode_ci NOT NULL,
  `db` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY `rdo_xref__idx1` (`doid`, `db`, `value`),
  CONSTRAINT `fk_rdo_xref__do` FOREIGN KEY (`doid`) REFERENCES `rdo` (`doid`),
  KEY `rdo_xref__idx2` (`db`, `value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `uberon` (
  `uid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  `comment` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `uberon_parent` (
  `uid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `parent_id` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  CONSTRAINT `fk_uberon_parent__uberon` FOREIGN KEY (`uid`) REFERENCES `uberon` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `uberon_xref` (
  `uid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `db` varchar(24) COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY `uberon_xref__idx1` (`uid`, `db`, `value`),
  CONSTRAINT `fk_uberon_xref__uberon` FOREIGN KEY (`uid`) REFERENCES `uberon` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

# Phenoypes
CREATE TABLE `omim` (
  `mim` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  PRIMARY KEY (`mim`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `omim_ps` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `omim_ps_id` char(8) NOT NULL,
  `mim` int(11) NULL,
  `title` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_omim_ps__omim` FOREIGN KEY (`mim`) REFERENCES `omim` (`mim`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
DROP TABLE `phenotype`;
CREATE TABLE `phenotype` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ptype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `nhprotein_id` int(11) DEFAULT NULL,
  `trait` text COLLATE utf8_unicode_ci,
  `top_level_term_id` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `top_level_term_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `term_id` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `term_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `term_description` text COLLATE utf8_unicode_ci,
  `p_value` double DEFAULT NULL,
  `percentage_change` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `effect_size` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `procedure_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `parameter_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `gp_assoc` tinyint(1) DEFAULT NULL,
  `statistical_method` text COLLATE utf8_unicode_ci,
  `sex` varchar(8) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `phenotype_idx1` (`ptype`),
  KEY `phenotype_idx2` (`protein_id`),
  KEY `phenotype_idx3` (`nhprotein_id`),
  CONSTRAINT `fk_phenotype__phenotype_type` FOREIGN KEY (`ptype`) REFERENCES `phenotype_type` (`name`),
  CONSTRAINT `fk_phenotype_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_phenotype_nhprotein` FOREIGN KEY (`nhprotein_id`) REFERENCES `nhprotein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
CREATE TABLE `gwas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `disease_trait` varchar(255) NOT NULL,
  `snps` text,
  `pmid` int(11),
  `study` text,
  `context` text,
  `intergenic` tinyint(1),
  `p_value` double,
  `or_beta` float,
  `cnv` char(1),
  `mapped_trait` text,
  `mapped_trait_uri` text,
  PRIMARY KEY (`id`),
  KEY `gwas_idx1` (`protein_id`),
  CONSTRAINT `fk_gwas_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

# Diseases
DROP TABLE disease;
CREATE TABLE `disease` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dtype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `nhprotein_id` int(11) DEFAULT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `did` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `evidence` text COLLATE utf8_unicode_ci,
  `zscore` decimal(4,3) DEFAULT NULL,
  `conf` decimal(2,1) DEFAULT NULL,
  `description` text COLLATE utf8_unicode_ci,
  `reference` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `drug_name` text COLLATE utf8_unicode_ci,
  `log2foldchange` decimal(5,3) DEFAULT NULL,
  `pvalue` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `score` decimal(16,15) DEFAULT NULL,
  `source` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `O2S` decimal(16,13) DEFAULT NULL,
  `S2O` decimal(16,13) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `disease_idx1` (`dtype`),
  KEY `disease_idx2` (`protein_id`),
  KEY `disease_idx3` (`nhprotein_id`),
  CONSTRAINT `fk_disease__disease_type` FOREIGN KEY (`dtype`) REFERENCES `disease_type` (`name`),
  CONSTRAINT `fk_disease_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_disease_nhprotein` FOREIGN KEY (`nhprotein_id`) REFERENCES `nhprotein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

ALTER TABLE expression ADD COLUMN cell_id varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL;
ALTER TABLE expression ADD COLUMN uberon_id varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL;
ALTER TABLE expression ADD CONSTRAINT `fk_expression_uberon` FOREIGN KEY (`uberon_id`) REFERENCES `uberon` (`uid`); 

-- end of what was run after original create-TCRDv6.sql

CREATE TABLE `homologene` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) DEFAULT NULL,
  `nhprotein_id` int(11) DEFAULT NULL,
  `groupid` int(11) NOT NULL,
  `taxid` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `homologene_idx1` (`protein_id`),
  KEY `homologene_idx2` (`nhprotein_id`),
  CONSTRAINT `fk_homologene_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_homologene_nhprotein` FOREIGN KEY (`nhprotein_id`) REFERENCES `nhprotein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

DROP TABLE ortholog_disease;
CREATE TABLE `ortholog_disease` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `did` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `ortholog_id` int(11) NOT NULL,
  `score` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ortholog_disease_idx1` (`protein_id`),
  KEY `ortholog_disease_idx2` (`ortholog_id`),
  CONSTRAINT `fk_ortholog_disease__ortholog` FOREIGN KEY (`ortholog_id`) REFERENCES `ortholog` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ortholog_disease__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `rat_qtl` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nhprotein_id` int(11) NOT NULL,
  `rgdid` int(11) NOT NULL,
  `qtl_rgdid` int(11) NOT NULL,
  `qtl_symbol` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `qtl_name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `trait_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `measurement_type` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `associated_disease` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `phenotype` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `p_value` decimal(20,19) DEFAULT NULL,
  `lod` float(6,3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `rat_qtl_idx1` (`nhprotein_id`),
  CONSTRAINT `fk_rat_qtl__nhprotein` FOREIGN KEY (`nhprotein_id`) REFERENCES `nhprotein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `rat_term` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `rgdid` int(11) NOT NULL,
  `term_id` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `obj_symbol` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `term_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `qualifier` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `evidence` varchar(5) COLLATE utf8_unicode_ci DEFAULT NULL,
  `ontology` varchar(40) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `rat_term_idx1` (`rgdid`, `term_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;


# LINCS
CREATE TABLE `lincs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `cellid varchar(10) NOT NULL,
  `pert_dcid` int(11) NOT NULL,
  `zscore` decimal(16,15) NOT NULL,
  `pert_canonical_smiles text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `lincs_idx1` (`protein_id`),
  CONSTRAINT `fk_lincs_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;


# ClinVar
# v6.3 and later
CREATE TABLE `clinvar_phenotype` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `clinvar_phenotype_xref` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clinvar_phenotype_id` int(11) NOT NULL,
  `source` varchar(40) NOT NULL,
  `value` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `clinvar_phenotype_idx1` (`clinvar_phenotype_id`),
  CONSTRAINT `fk_clinvar_phenotype_xref__clinvar_phenotype` FOREIGN KEY (`clinvar_phenotype_id`) REFERENCES `clinvar_phenotype` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE `clinvar` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `clinvar_phenotype_id` int(11) NOT NULL,
  `alleleid` int(11) NOT NULL,
  `type` varchar(40) NOT NULL,
  `name` text NOT NULL,
  `review_status` varchar(60) NOT NULL,
  `clinical_significance` varchar(80) DEFAULT NULL,
  `clin_sig_simple` int(11) DEFAULT NULL,
  `last_evaluated` DATE DEFAULT NULL,
  `dbsnp_rs` int(11) DEFAULT NULL,
  `dbvarid` varchar(10) DEFAULT NULL,
  `origin` varchar(60) DEFAULT NULL,
  `origin_simple` varchar(20) DEFAULT NULL,
  `assembly` varchar(8) DEFAULT NULL,
  `chr` varchar(2) DEFAULT NULL,
  `chr_acc` varchar(20) DEFAULT NULL,
  `start` int(11) DEFAULT NULL,
  `stop` int(11) DEFAULT NULL,
  `number_submitters` int(2) DEFAULT NULL ,
  `tested_in_gtr` tinyint(1) DEFAULT NULL,
  `submitter_categories` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `clinvar_idx1` (`protein_id`),
  KEY `clinvar_idx2` (`clinvar_phenotype_id`),
  CONSTRAINT `fk_clinvar_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_clinvar__clinvar_phenotype` FOREIGN KEY (`clinvar_phenotype_id`) REFERENCES `clinvar_phenotype` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

drop table clinvar;
drop table clinvar_phenotype_xref;
drop table clinvar_phenotype;
