-- MySQL dump 10.13  Distrib 5.6.24, for Linux (x86_64)
--
-- Host: localhost    Database: tcrd3
-- ------------------------------------------------------
-- Server version	5.6.24

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alias`
--

DROP TABLE IF EXISTS `alias`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alias` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `type` enum('symbol','uniprot') COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `alias_idx1` (`protein_id`),
  CONSTRAINT `fk_alias_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chembl_activity`
--

DROP TABLE IF EXISTS `chembl_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `chembl_activity` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) DEFAULT NULL,
  `cmpd_chemblid` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `cmpd_name_in_ref` text COLLATE utf8_unicode_ci,
  `smiles` text COLLATE utf8_unicode_ci,
  `act_value` decimal(10,8) DEFAULT NULL,
  `act_type` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `reference` text COLLATE utf8_unicode_ci,
  `pubmed_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `chembl_activity_idx1` (`target_id`),
  CONSTRAINT `fk_chembl_activity__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `compartment`
--

DROP TABLE IF EXISTS `compartment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `compartment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ctype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `go_id` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `go_term` text COLLATE utf8_unicode_ci,
  `evidence` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `zscore` decimal(4,3) DEFAULT NULL,
  `conf` decimal(2,1) DEFAULT NULL,
  `url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `compartment_idx1` (`ctype`),
  KEY `compartment_idx2` (`target_id`),
  KEY `compartment_idx3` (`protein_id`),
  CONSTRAINT `fk_compartment__compartment_type` FOREIGN KEY (`ctype`) REFERENCES `compartment_type` (`name`),
  CONSTRAINT `fk_compartment_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_compartment_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `compartment_type`
--

DROP TABLE IF EXISTS `compartment_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `compartment_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `data_type`
--

DROP TABLE IF EXISTS `data_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `data_type` (
  `name` varchar(7) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dataset`
--

DROP TABLE IF EXISTS `dataset`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dataset` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `source` text COLLATE utf8_unicode_ci NOT NULL,
  `app` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `app_version` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `datetime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `columns_touched` text COLLATE utf8_unicode_ci,
  `url` text COLLATE utf8_unicode_ci,
  `comments` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dbinfo`
--

DROP TABLE IF EXISTS `dbinfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dbinfo` (
  `dbname` varchar(16) COLLATE utf8_unicode_ci NOT NULL,
  `schema_ver` varchar(16) COLLATE utf8_unicode_ci NOT NULL,
  `data_ver` varchar(16) COLLATE utf8_unicode_ci NOT NULL,
  `owner` varchar(16) COLLATE utf8_unicode_ci NOT NULL,
  `is_copy` tinyint(1) NOT NULL DEFAULT '0',
  `dump_file` varchar(64) COLLATE utf8_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `disease_type`
--

DROP TABLE IF EXISTS `disease_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `disease_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `do`
--

DROP TABLE IF EXISTS `do`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `do` (
  `id` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `def` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `do_parent`
--

DROP TABLE IF EXISTS `do_parent`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `do_parent` (
  `doid` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `parent` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `drug_activity`
--

DROP TABLE IF EXISTS `drug_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `drug_activity` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) NOT NULL,
  `drug` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `act_value` decimal(10,8) DEFAULT NULL,
  `act_type` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `action_type` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `has_moa` tinyint(1) NOT NULL,
  `source` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `reference` text COLLATE utf8_unicode_ci,
  `smiles` text COLLATE utf8_unicode_ci,
  `cmpd_chemblid` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `nlm_drug_info` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `drug_activity_idx1` (`target_id`),
  CONSTRAINT `fk_drug_activity__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dto`
--

DROP TABLE IF EXISTS `dto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dto` (
  `id` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `parent` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dto_idx1` (`parent`),
  CONSTRAINT `fk_dto_dto` FOREIGN KEY (`parent`) REFERENCES `dto` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `expression`
--

DROP TABLE IF EXISTS `expression`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `expression` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `etype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `tissue` text COLLATE utf8_unicode_ci NOT NULL,
  `qual_value` enum('Not detected','Low','Medium','High') COLLATE utf8_unicode_ci NOT NULL,
  `number_value` decimal(12,6) DEFAULT NULL,
  `boolean_value` tinyint(1) DEFAULT NULL,
  `string_value` text COLLATE utf8_unicode_ci,
  `pubmed_id` int(11) DEFAULT NULL,
  `evidence` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `zscore` decimal(4,3) DEFAULT NULL,
  `conf` decimal(2,1) DEFAULT NULL,
  `oid` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `confidence` tinyint(1) DEFAULT NULL,
  `age` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `gender` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `expression_idx1` (`etype`),
  KEY `expression_idx2` (`target_id`),
  KEY `expression_idx3` (`protein_id`),
  CONSTRAINT `fk_expression__expression_type` FOREIGN KEY (`etype`) REFERENCES `expression_type` (`name`),
  CONSTRAINT `fk_expression__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_expression__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `expression_type`
--

DROP TABLE IF EXISTS `expression_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `expression_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `data_type` varchar(7) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`),
  UNIQUE KEY `expression_type_idx1` (`name`,`data_type`),
  KEY `fk_expression_type__data_type` (`data_type`),
  CONSTRAINT `fk_expression_type__data_type` FOREIGN KEY (`data_type`) REFERENCES `data_type` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `feature`
--

DROP TABLE IF EXISTS `feature`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `feature` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  `srcid` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `evidence` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `begin` int(11) DEFAULT NULL,
  `end` int(11) DEFAULT NULL,
  `position` int(11) DEFAULT NULL,
  `original` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `variation` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `feature_idx1` (`protein_id`),
  CONSTRAINT `fk_feature_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gene_attribute`
--

DROP TABLE IF EXISTS `gene_attribute`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gene_attribute` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `gat_id` int(11) NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `value` int(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `gene_attribute_idx1` (`protein_id`),
  KEY `gene_attribute_idx2` (`gat_id`),
  CONSTRAINT `fk_gene_attribute__gene_attribute_type` FOREIGN KEY (`gat_id`) REFERENCES `gene_attribute_type` (`id`),
  CONSTRAINT `fk_gene_attribute__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gene_attribute_type`
--

DROP TABLE IF EXISTS `gene_attribute_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gene_attribute_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `association` text COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci NOT NULL,
  `resource_group` enum('omics','genomics','proteomics','physical interactions','transcriptomics','structural or functional annotations','disease or phenotype associations') COLLATE utf8_unicode_ci NOT NULL,
  `measurement` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `attribute_group` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `attribute_type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `pubmed_ids` text COLLATE utf8_unicode_ci,
  `url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `gene_attribute_type_idx1` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `generif`
--

DROP TABLE IF EXISTS `generif`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `generif` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `pubmed_ids` text COLLATE utf8_unicode_ci,
  `text` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `generif_idx1` (`protein_id`),
  CONSTRAINT `fk_generif_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `goa`
--

DROP TABLE IF EXISTS `goa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `goa` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `go_id` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `go_term` text COLLATE utf8_unicode_ci,
  `evidence` text COLLATE utf8_unicode_ci,
  `goeco` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `goa_idx1` (`protein_id`),
  CONSTRAINT `fk_goa_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hgram_cdf`
--

DROP TABLE IF EXISTS `hgram_cdf`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hgram_cdf` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `attr_count` int(11) NOT NULL,
  `attr_cdf` decimal(17,16) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `hgram_cdf_idx1` (`protein_id`),
  KEY `hgram_cdf_idx2` (`type`),
  CONSTRAINT `fk_hgram_cdf__gene_attribute_type` FOREIGN KEY (`type`) REFERENCES `gene_attribute_type` (`name`),
  CONSTRAINT `fk_hgram_cdf__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `info_type`
--

DROP TABLE IF EXISTS `info_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `info_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `data_type` varchar(7) COLLATE utf8_unicode_ci NOT NULL,
  `unit` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`),
  UNIQUE KEY `info_type_idx1` (`name`,`data_type`),
  UNIQUE KEY `expression_type_idx1` (`name`,`data_type`),
  KEY `fk_info_type__data_type` (`data_type`),
  CONSTRAINT `fk_info_type__data_type` FOREIGN KEY (`data_type`) REFERENCES `data_type` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `kegg_distance`
--

DROP TABLE IF EXISTS `kegg_distance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `kegg_distance` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pid1` int(11) NOT NULL,
  `pid2` int(11) NOT NULL,
  `distance` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `kegg_distance_idx1` (`pid1`),
  KEY `kegg_distance_idx2` (`pid2`),
  CONSTRAINT `fk_kegg_distance__protein1` FOREIGN KEY (`pid1`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_kegg_distance__protein2` FOREIGN KEY (`pid2`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mlp_assay_info`
--

DROP TABLE IF EXISTS `mlp_assay_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mlp_assay_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `assay_name` text COLLATE utf8_unicode_ci NOT NULL,
  `method` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `active_sids` int(11) DEFAULT NULL,
  `inactive_sids` int(11) DEFAULT NULL,
  `iconclusive_sids` int(11) DEFAULT NULL,
  `total_sids` int(11) DEFAULT NULL,
  `aid` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `mlp_assay_info_idx1` (`protein_id`),
  CONSTRAINT `fk_mai_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `p2pc`
--

DROP TABLE IF EXISTS `p2pc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `p2pc` (
  `panther_class_id` int(11) NOT NULL,
  `protein_id` int(11) NOT NULL,
  KEY `p2pc_idx1` (`panther_class_id`),
  KEY `p2pc_idx2` (`protein_id`),
  CONSTRAINT `fk_p2pc__panther_class` FOREIGN KEY (`panther_class_id`) REFERENCES `panther_class` (`id`),
  CONSTRAINT `fk_p2pc_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `panther_class`
--

DROP TABLE IF EXISTS `panther_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `panther_class` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pcid` char(7) COLLATE utf8_unicode_ci NOT NULL,
  `parent_pcids` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `panther_class_idx1` (`pcid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `patent_count`
--

DROP TABLE IF EXISTS `patent_count`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `patent_count` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `year` int(4) NOT NULL,
  `count` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `patent_count_idx1` (`protein_id`),
  CONSTRAINT `fk_patent_count__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pathway`
--

DROP TABLE IF EXISTS `pathway`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pathway` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `pwtype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `id_in_source` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  `url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `pathway_idx1` (`target_id`),
  KEY `pathway_idx2` (`protein_id`),
  KEY `pathway_idx3` (`pwtype`),
  CONSTRAINT `fk_pathway__pathway_type` FOREIGN KEY (`pwtype`) REFERENCES `pathway_type` (`name`),
  CONSTRAINT `fk_pathway_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pathway_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pathway_type`
--

DROP TABLE IF EXISTS `pathway_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pathway_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `phenotype`
--

DROP TABLE IF EXISTS `phenotype`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `phenotype` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ptype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `trait` text COLLATE utf8_unicode_ci,
  `pmid` int(11) DEFAULT NULL,
  `snps` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `top_level_term_id` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `top_level_term_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `term_id` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `term_name` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `p_value` double DEFAULT NULL,
  `percentage_change` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `effect_size` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `statistical_method` text COLLATE utf8_unicode_ci,
  `term_description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `phenotype_idx1` (`ptype`),
  KEY `phenotype_idx2` (`target_id`),
  KEY `phenotype_idx3` (`protein_id`),
  CONSTRAINT `fk_phenotype_info_type` FOREIGN KEY (`ptype`) REFERENCES `phenotype_type` (`name`),
  CONSTRAINT `fk_phenotype_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_phenotype_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `phenotype_type`
--

DROP TABLE IF EXISTS `phenotype_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `phenotype_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `ontology` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`),
  UNIQUE KEY `phenotype_type_idx1` (`name`,`ontology`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pmscore`
--

DROP TABLE IF EXISTS `pmscore`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pmscore` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `year` int(4) NOT NULL,
  `score` decimal(12,6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `pmscore_idx1` (`protein_id`),
  CONSTRAINT `fk_pmscore_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ppi`
--

DROP TABLE IF EXISTS `ppi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ppi` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ppitype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `protein1_id` int(11) NOT NULL,
  `protein1_str` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `protein2_id` int(11) NOT NULL,
  `protein2_str` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `p_int` decimal(10,9) DEFAULT NULL,
  `p_ni` decimal(10,9) DEFAULT NULL,
  `p_wrong` decimal(10,9) DEFAULT NULL,
  `evidence` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ppi_idx1` (`protein1_id`),
  KEY `ppi_idx2` (`protein2_id`),
  KEY `ppi_idx3` (`ppitype`),
  CONSTRAINT `fk_ppi_protein1` FOREIGN KEY (`protein1_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ppi_protein2` FOREIGN KEY (`protein2_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ppi_type`
--

DROP TABLE IF EXISTS `ppi_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ppi_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  `url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `protein`
--

DROP TABLE IF EXISTS `protein`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `protein` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci NOT NULL,
  `uniprot` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `up_version` int(11) DEFAULT NULL,
  `geneid` int(11) DEFAULT NULL,
  `sym` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `family` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `chr` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `seq` text COLLATE utf8_unicode_ci,
  `dtoid` varchar(13) COLLATE utf8_unicode_ci DEFAULT NULL,
  `stringid` varchar(15) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `protein_idx1` (`uniprot`),
  UNIQUE KEY `protein_idx2` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `protein2pubmed`
--

DROP TABLE IF EXISTS `protein2pubmed`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `protein2pubmed` (
  `protein_id` int(11) NOT NULL,
  `pubmed_id` int(11) NOT NULL,
  KEY `protein2pubmed_idx1` (`protein_id`),
  KEY `protein2pubmed_idx2` (`pubmed_id`),
  CONSTRAINT `fk_protein2pubmed__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_protein2pubmed__pubmed` FOREIGN KEY (`pubmed_id`) REFERENCES `pubmed` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ptscore`
--

DROP TABLE IF EXISTS `ptscore`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ptscore` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `year` int(4) NOT NULL,
  `score` decimal(12,6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ptscore_idx1` (`protein_id`),
  CONSTRAINT `fk_ptscore_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pubmed`
--

DROP TABLE IF EXISTS `pubmed`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pubmed` (
  `id` int(11) NOT NULL,
  `title` text COLLATE utf8_unicode_ci NOT NULL,
  `journal` text COLLATE utf8_unicode_ci,
  `date` varchar(10) COLLATE utf8_unicode_ci DEFAULT NULL,
  `authors` text COLLATE utf8_unicode_ci,
  `abstract` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `synonym`
--

DROP TABLE IF EXISTS `synonym`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `synonym` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `syononym_idx1` (`target_id`),
  KEY `syononym_idx2` (`protein_id`),
  CONSTRAINT `fk_synonym_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_synonym_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `t2tc`
--

DROP TABLE IF EXISTS `t2tc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `t2tc` (
  `target_id` int(11) NOT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `nucleic_acid_id` int(11) DEFAULT NULL,
  KEY `t2tc_idx1` (`target_id`),
  KEY `t2tc_idx2` (`protein_id`),
  CONSTRAINT `fk_t2tc__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`),
  CONSTRAINT `fk_t2tc__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `target`
--

DROP TABLE IF EXISTS `target`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `target` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `ttype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  `comment` text COLLATE utf8_unicode_ci,
  `tdl` enum('Tclin+','Tclin','Tchem+','Tchem','Tbio','Tgray','Tdark') COLLATE utf8_unicode_ci DEFAULT NULL,
  `idgfam` enum('GPCR','oGPCR','Kinase','IC','NR') COLLATE utf8_unicode_ci DEFAULT NULL,
  `idg2` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `disease`
--

DROP TABLE IF EXISTS `disease`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `disease` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dtype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) NULL,
  `protein_id` int(11) NULL,
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
  PRIMARY KEY (`id`),
  KEY `disease_idx1` (`dtype`),
  KEY `disease_idx2` (`target_id`),
  KEY `disease_idx3` (`protein_id`),
  CONSTRAINT `fk_disease_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_disease_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_disease__disease_type` FOREIGN KEY (`dtype`) REFERENCES `disease_type` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `grant`
--

DROP TABLE IF EXISTS `grant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `grant` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) NULL,
  `protein_id` int(11) NULL,
  `appid` int(11) NOT NULL,
  `full_project_num` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `activity` varchar(4) COLLATE utf8_unicode_ci NOT NULL,
  `funding_ics` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `year` int(4) NOT NULL,
  `cost` decimal(12,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `grant_idx1` (`target_id`),
  KEY `grant_idx2` (`protein_id`),
  CONSTRAINT `fk_grant_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_grant_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tdl_info`
--

DROP TABLE IF EXISTS `tdl_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tdl_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `itype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `nucleic_acid_id` int(11) DEFAULT NULL,
  `string_value` text COLLATE utf8_unicode_ci,
  `number_value` decimal(12,6) DEFAULT NULL,
  `integer_value` int(11) DEFAULT NULL,
  `date_value` date DEFAULT NULL,
  `boolean_value` tinyint(1) DEFAULT NULL,
  `curration_level` varchar(50) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `tdl_info_idx1` (`itype`),
  KEY `tdl_info_idx2` (`target_id`),
  KEY `tdl_info_idx3` (`protein_id`),
  CONSTRAINT `fk_tdl_info__info_type` FOREIGN KEY (`itype`) REFERENCES `info_type` (`name`),
  CONSTRAINT `fk_tdl_info__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tdl_info__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tdl_update_log`
--

DROP TABLE IF EXISTS `tdl_update_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tdl_update_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target_id` int(11) NOT NULL,
  `old_tdl` varchar(10) COLLATE utf8_unicode_ci DEFAULT NULL,
  `new_tdl` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `person` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `datetime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `explanation` text COLLATE utf8_unicode_ci,
  `application` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `app_version` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `tdl_update_log` (`target_id`),
  CONSTRAINT `fk_tdl_update_log__target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `techdev_contact`
--

DROP TABLE IF EXISTS `techdev_contact`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `techdev_contact` (
  `id` int(11) NOT NULL,
  `contact_name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `contact_email` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `date` date DEFAULT NULL,
  `grant_number` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `pi` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `techdev_info`
--

DROP TABLE IF EXISTS `techdev_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `techdev_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `contact_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `comment` text COLLATE utf8_unicode_ci NOT NULL,
  `publication_pcmid` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `publication_pmid` int(11) DEFAULT NULL,
  `resource_url` text COLLATE utf8_unicode_ci,
  `data_url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `techdev_info_idx1` (`contact_id`),
  KEY `techdev_info_idx2` (`protein_id`),
  CONSTRAINT `fk_techdev_info__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_techdev_info__techdev_contact` FOREIGN KEY (`contact_id`) REFERENCES `techdev_contact` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tinx_articlerank`
--

DROP TABLE IF EXISTS `tinx_articlerank`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tinx_articlerank` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `importance_id` int(11) NOT NULL,
  `pmid` int(11) NOT NULL,
  `rank` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tinx_articlerank_idx1` (`importance_id`),
  CONSTRAINT `fk_tinx_articlerank__tinx_importance` FOREIGN KEY (`importance_id`) REFERENCES `tinx_importance` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tinx_disease`
--

DROP TABLE IF EXISTS `tinx_disease`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tinx_disease` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `doid` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
  `name` text COLLATE utf8_unicode_ci NOT NULL,
  `summary` text COLLATE utf8_unicode_ci,
  `score` decimal(34,16) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tinx_importance`
--

DROP TABLE IF EXISTS `tinx_importance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tinx_importance` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `disease_id` int(11) NOT NULL,
  `score` decimal(34,16) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tinx_importance_idx1` (`protein_id`),
  KEY `tinx_importance_idx2` (`disease_id`),
  CONSTRAINT `fk_tinx_importance__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tinx_importance__tinx_disease` FOREIGN KEY (`disease_id`) REFERENCES `tinx_disease` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tinx_novelty`
--

DROP TABLE IF EXISTS `tinx_novelty`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tinx_novelty` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `protein_id` int(11) NOT NULL,
  `score` decimal(34,16) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tinx_novelty_idx1` (`protein_id`),
  CONSTRAINT `fk_tinx_novelty__protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary view structure for view `tinx_target`
--

DROP TABLE IF EXISTS `tinx_target`;
/*!50001 DROP VIEW IF EXISTS `tinx_target`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `tinx_target` AS SELECT 
 1 AS `target_id`,
 1 AS `protein_id`,
 1 AS `uniprot`,
 1 AS `sym`,
 1 AS `tdl`,
 1 AS `idgfam`,
 1 AS `family`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `xref`
--

DROP TABLE IF EXISTS `xref`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `xref` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `xtype` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `target_id` int(11) DEFAULT NULL,
  `protein_id` int(11) DEFAULT NULL,
  `nucleic_acid_id` int(11) DEFAULT NULL,
  `value` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `xtra` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `xref_idx3` (`xtype`,`target_id`,`value`),
  UNIQUE KEY `xref_idx5` (`xtype`,`protein_id`,`value`),
  KEY `xref_idx1` (`xtype`),
  KEY `xref_idx2` (`target_id`),
  KEY `xref_idx4` (`protein_id`),
  CONSTRAINT `fk_xref__xref_type` FOREIGN KEY (`xtype`) REFERENCES `xref_type` (`name`),
  CONSTRAINT `fk_xref_protein` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_xref_target` FOREIGN KEY (`target_id`) REFERENCES `target` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `xref_type`
--

DROP TABLE IF EXISTS `xref_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `xref_type` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `description` text COLLATE utf8_unicode_ci,
  `url` text COLLATE utf8_unicode_ci,
  `eg_q_url` text COLLATE utf8_unicode_ci,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Final view structure for view `tinx_target`
--

/*!50001 DROP VIEW IF EXISTS `tinx_target`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`smathias`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `tinx_target` AS select `t`.`id` AS `target_id`,`p`.`id` AS `protein_id`,`p`.`uniprot` AS `uniprot`,`p`.`sym` AS `sym`,`t`.`tdl` AS `tdl`,`t`.`idgfam` AS `idgfam`,`p`.`family` AS `family` from ((`target` `t` join `t2tc`) join `protein` `p`) where ((`t`.`id` = `t2tc`.`target_id`) and (`t2tc`.`protein_id` = `p`.`id`) and `p`.`id` in (select distinct `tinx_novelty`.`protein_id` from `tinx_novelty`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-11-16 10:21:30
