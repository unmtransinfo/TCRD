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
-- Dumping data for table `compartment_type`
--

LOCK TABLES `compartment_type` WRITE;
/*!40000 ALTER TABLE `compartment_type` DISABLE KEYS */;
INSERT INTO `compartment_type` VALUES ('JensenLab Experiment','Experiment channel subcellular locations from JensenLab COMPARTMENTS resource, filtered for confidence scores of 3 or greater.'),('JensenLab Knowledge','Knowledge channel subcellular locations from JensenLab COMPARTMENTS resource, filtered for confidence scores of 3 or greater.'),('JensenLab Prediction','Prediction channel subcellular locations from JensenLab COMPARTMENTS resource, filtered for confidence scores of 3 or greater.'),('JensenLab Text Mining','Text Mining channel subcellular locations from JensenLab COMPARTMENTS resource, filtered for zscore of 3.0 or greater.');
/*!40000 ALTER TABLE `compartment_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `data_type`
--

LOCK TABLES `data_type` WRITE;
/*!40000 ALTER TABLE `data_type` DISABLE KEYS */;
INSERT INTO `data_type` VALUES ('Boolean'),('Date'),('Integer'),('Number'),('String');
/*!40000 ALTER TABLE `data_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `disease_association_type`
--

LOCK TABLES `disease_type` WRITE;
/*!40000 ALTER TABLE `disease_type` DISABLE KEYS */;
INSERT INTO `disease_type` VALUES ('DisGeNET','Currated disease associations from DisGeNET (http://www.disgenet.org/)'),('DrugCentral Indication','Disease indications and associated drug names from Drug Central.'),('Expression Atlas','Target-Disease associations from Expression Atlas where the log2 fold change in gene expresion in disease sample vs reference sample is greater than 1.0. Only reference samples \"normal\" or \"healthy\" are selected. Data is derived from the file: ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz'),('JensenLab Experiment COSMIC','JensenLab Experiment channel using COSMIC'),('JensenLab Experiment DistiLD','JensenLab Experiment channel using DistiLD'),('JensenLab Knowledge GHR','JensenLab Knowledge channel using GHR'),('JensenLab Knowledge UniProtKB-KW','JensenLab Knowledge channel using UniProtKB-KW'),('JensenLab Text Mining','JensenLab Text Mining channel'),('UniProt Disease','Disease association from UniProt comment field with type=\"disease\"');
/*!40000 ALTER TABLE `disease_association_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `expression_type`
--

LOCK TABLES `expression_type` WRITE;
/*!40000 ALTER TABLE `expression_type` DISABLE KEYS */;
INSERT INTO `expression_type` VALUES ('Consensus','String','Qualitative consensus expression value calulated from GTEx, HPA and HPM data aggregated according to manually mapped tissue types.'),('GTEx','Number','GTEx V4 RNA-SeQCv1.1.8 Log Median RPKM and qualitative expression values per SMTSD tissue type.'),('HPA Protein','String',''),('HPA RNA','String',''),('HPM Gene','Number','Human Proteome Map gene-level Log and qualitative expression values.'),('HPM Protein','Number','Human Proteome Map protein-level Log and qualitative expression values.'),('JensenLab Experiment Exon array','String','JensenLab Experiment channel using Exon array'),('JensenLab Experiment GNF','String','JensenLab Experiment channel using GNF'),('JensenLab Experiment HPA','String','JensenLab Experiment channel using Human Protein Atlas IHC'),('JensenLab Experiment HPA-RNA','String','JensenLab Experiment channel using Human Protein Atlas RNA'),('JensenLab Experiment HPM','String','JensenLab Experiment channel using Humap Proteome Map'),('JensenLab Experiment RNA-seq','String','JensenLab Experiment channel using RNA-seq'),('JensenLab Experiment UniGene','String','JensenLab Experiment channel using UniGene'),('JensenLab Knowledge UniProtKB-RC','Boolean','JensenLab Knowledge channel using UniProtKB-RC'),('JensenLab Text Mining','Boolean','JensenLab Text Mining channel'),('UniProt Tissue','Boolean','Tissue and PubMed ID from UniProt');
/*!40000 ALTER TABLE `expression_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `info_type`
--

LOCK TABLES `info_type` WRITE;
/*!40000 ALTER TABLE `info_type` DISABLE KEYS */;
INSERT INTO `info_type` VALUES ('Ab Count','Integer',NULL,'Antibody count from antibodypedia.com'),('Antibodypedia.com URL','String',NULL,'Antibodypedia.com detail page URL for a given protein.'),('ChEMBL Activity Count','Integer',NULL,'Number of filtered bioactivities in ChEMBL better than 1uM (10uM for Ion Channels)'),('ChEMBL First Reference Year','Integer',NULL,'The year of the oldest bioactivity reference this target has in ChEMBL. Note that this is derived from ChEMBL activities as filtered for TCRD purposes.'),('ChEMBL Selective Compound','String',NULL,'2 log selective compound on this target. Value is ChEMBL ID and SMILES joined with a pipe character.'),('Drugable Epigenome Class','String',NULL,'Drugable Epigenome Class/Domain from Nature Reviews Drug Discovery 11, 384-400 (May 2012)'),('DrugDB Count','Integer',NULL,'Number of drugs in DrugDB with with activity better than 1uM (10uM for Ion Channels)'),('EBI Total Patent Count','Integer',NULL,'Total count of all patents mentioning this protein according to EBI text mining'),('EBI Total Patent Count (Relevant)','Integer',NULL,'Total count of all relevant patents mentioning this protein according to EBI text mining'),('Experimental MF/BP Leaf Term GOA','String',NULL,'Indicates that a target is annotated with one or more GO MF/BP leaf term with Experimental Evidence code. Value is a concatenation of all GO terms/names/evidences.'),('GTEx Tissue Specificity Index','Number',NULL,'Tau as defined in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005) calculated on GTEx data.'),('Has MLP Assay','Boolean',NULL,'Indicates that a protein is used in at least one PubChem MLP assay. Details are in mlp_assay_info tabel.'),('HPA Protein Tissue Specificity Index','Number',NULL,'Tau as defined in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005) calculated on HPA Protein data.'),('HPA RNA Tissue Specificity Index','Number',NULL,'Tau as defined in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005) calculated on HPM RNA data.'),('HPM Gene Tissue Specificity Index','Number',NULL,'Tau as defined in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005) calculated on HPM Gene data.'),('HPM Protein Tissue Specificity Index','Number',NULL,'Tau as defined in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005) calculated on HPM Protein data.'),('IMPC Mice In Progress','Boolean',NULL,'IMPC mouse knockout strain is in progress.'),('IMPC Mice Produced','Boolean',NULL,'IMPC mouse knockout strain is available.'),('Is Transcription Factor','Boolean',NULL,'Target is a transcription factor according to http://www.bioguo.org/AnimalTFDB'),('JensenLab COMPARTMENT Prediction Plasma membrane','String',NULL,'Prediction method and value (conf 2 or 3 only) that the protein is Plasma membrane from JensenLab COMPARTMENTS resouce'),('JensenLab PubMed Score','Number',NULL,'PubMed paper count from textmining done in group of Lars-Juhl Jensen.'),('MAb Count','Integer',NULL,'Monoclonal Antibody count from antibodypedia.com'),('NCBI Gene PubMed Count','Integer',NULL,'Number of PubMed references for target and all its aliases'),('NCBI Gene Summary','String',NULL,'Gene summary statement from NCBI Gene database'),('NIHRePORTER 2010-2015 R01 Count','Integer',NULL,'Total number of 2010-2015 R01s associated with this target via JensenLab tagger.'),('PubTator Score','Number',NULL,'PubMed paper count from PubTator data run through Lars Jensen\'s counting proceedure'),('TIN-X Novelty Score','Number',NULL,'TIN-X novelty score from Cristian Bologa.'),('TM Count','Integer',NULL,'Number of transmembrane helices according to Survey of the Human Transmembrane Proteome (https://modbase.compbio.ucsf.edu/projects/membrane/). At least 2 are required to be in their list.'),('TMHMM Prediction','String',NULL,'Short output from TMHMM run locally on protein sequences.'),('UniProt Function','String',NULL,'Funtion comment from UniProt');
/*!40000 ALTER TABLE `info_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `pathway_type`
--

LOCK TABLES `pathway_type` WRITE;
/*!40000 ALTER TABLE `pathway_type` DISABLE KEYS */;
INSERT INTO `pathway_type` VALUES ('KEGG','http://www.kegg.jp/kegg/pathway.html'),('PathwayCommons: ctd','http://www.pathwaycommons.org/pc2/ctd'),('PathwayCommons: humancyc','http://www.pathwaycommons.org/pc2/humancyc'),('PathwayCommons: inoh','http://www.pathwaycommons.org/pc2/inoh'),('PathwayCommons: mirtarbase','http://www.pathwaycommons.org/pc2/mirtarbase'),('PathwayCommons: netpath','http://www.pathwaycommons.org/pc2/netpath'),('PathwayCommons: panther','http://pathwaycommons.org/pc2/panther'),('PathwayCommons: pid','http://www.pathwaycommons.org/pc2/pid'),('PathwayCommons: recon','http://www.pathwaycommons.org/pc2/recon'),('PathwayCommons: smpdb','http://www.pathwaycommons.org/pc2/smpdb'),('PathwayCommons: transfac','http://www.pathwaycommons.org/pc2/transfac'),('Reactome','http://www.reactome.org/'),('UniProt','http://www.uniprot.org/'),('WikiPathways','http://www.wikipathways.org/index.php/WikiPathways');
/*!40000 ALTER TABLE `pathway_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `phenotype_type`
--

LOCK TABLES `phenotype_type` WRITE;
/*!40000 ALTER TABLE `phenotype_type` DISABLE KEYS */;
INSERT INTO `phenotype_type` VALUES ('GWAS Catalog',NULL,'GWAS findings from NHGRI/EBI GWAS catalog file.'),('IMPC','Mammalian Phenotype Ontology','Phenotypes from the International Mouse Phenotyping Consortium. These are single gene knockout phenotypes.'),('JAX/MGI Human Ortholog Phenotype','Mammalian Phenotype Ontology','JAX/MGI house/human orthology phenotypes in file HMD_HumanPhenotype.rpt from ftp.informatics.jax.or'),('OMIM',NULL,'Phenotypes from OMIM with status Confirmed. phenotype.trait is a concatenation of Title, MIM Number, Method, and Comments fields from the OMIM genemap2.txt file.');
/*!40000 ALTER TABLE `phenotype_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `ppi_type`
--

LOCK TABLES `ppi_type` WRITE;
/*!40000 ALTER TABLE `ppi_type` DISABLE KEYS */;
INSERT INTO `ppi_type` VALUES ('BioPlex','The BioPlex (biophysical interactions of ORFeome-based complexes) network is the result of creating thousands of cell lines with each expressing a tagged version of a protein from the ORFeome collection.','http://wren.hms.harvard.edu/bioplex/'),('Reactome','Interactions derived from Reactome pathways','http://www.reactome.org/');
/*!40000 ALTER TABLE `ppi_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `xref_type`
--

LOCK TABLES `xref_type` WRITE;
/*!40000 ALTER TABLE `xref_type` DISABLE KEYS */;
INSERT INTO `xref_type` VALUES ('ArrayExpress',NULL,NULL,NULL),('Bgee',NULL,NULL,NULL),('BindingDB',NULL,NULL,NULL),('BioCyc',NULL,NULL,NULL),('BioGrid',NULL,NULL,NULL),('BRENDA',NULL,NULL,NULL),('CCDS',NULL,NULL,NULL),('ChEMBL',NULL,NULL,NULL),('ChiTaRS',NULL,NULL,NULL),('CleanEx',NULL,NULL,NULL),('CTD',NULL,NULL,NULL),('DIP',NULL,NULL,NULL),('DisProt',NULL,NULL,NULL),('DMDM',NULL,NULL,NULL),('DNASU',NULL,NULL,NULL),('DOSAC-COBS-2DPAGE',NULL,NULL,NULL),('DrugBank',NULL,NULL,NULL),('eggNOG',NULL,NULL,NULL),('EMBL',NULL,NULL,NULL),('Ensembl',NULL,NULL,NULL),('EvolutionaryTrace',NULL,NULL,NULL),('ExpressionAtlas',NULL,NULL,NULL),('Gene3D',NULL,NULL,NULL),('GeneCards',NULL,NULL,NULL),('GeneID',NULL,NULL,NULL),('Genevestigator',NULL,NULL,NULL),('GeneWiki',NULL,NULL,NULL),('GenomeRNAi',NULL,NULL,NULL),('GO',NULL,NULL,NULL),('H-InvDB',NULL,NULL,NULL),('HAMAP',NULL,NULL,NULL),('HGNC',NULL,NULL,NULL),('HOGENOM',NULL,NULL,NULL),('HOVERGEN',NULL,NULL,NULL),('HPA',NULL,NULL,NULL),('HuGE Navigator','An integrated, searchable knowledge base of genetic associations and human genome epidemiology.',NULL,NULL),('InParanoid',NULL,NULL,NULL),('IntAct',NULL,NULL,NULL),('InterPro',NULL,NULL,NULL),('IPI',NULL,NULL,NULL),('KEGG',NULL,NULL,NULL),('KEGG Gene',NULL,NULL,NULL),('KO',NULL,NULL,NULL),('L1000 ID','CMap landmark gene ID. See http://support.lincscloud.org/hc/en-us/articles/202092616-The-Landmark-Genes',NULL,NULL),('MEROPS',NULL,NULL,NULL),('MGI ID',NULL,NULL,NULL),('MIM',NULL,NULL,NULL),('MINT',NULL,NULL,NULL),('NCBI GI',NULL,NULL,NULL),('NextBio',NULL,NULL,NULL),('neXtProt',NULL,NULL,NULL),('OGP',NULL,NULL,NULL),('OMA',NULL,NULL,NULL),('Orphanet',NULL,NULL,NULL),('OrthoDB',NULL,NULL,NULL),('PANTHER',NULL,NULL,NULL),('PaxDb',NULL,NULL,NULL),('PDB',NULL,NULL,NULL),('PDBsum',NULL,NULL,NULL),('PeptideAtlas',NULL,NULL,NULL),('PeroxiBase',NULL,NULL,NULL),('Pfam',NULL,NULL,NULL),('PharmGKB',NULL,NULL,NULL),('PhosphoSite',NULL,NULL,NULL),('PhylomeDB',NULL,NULL,NULL),('PIR',NULL,NULL,NULL),('PIRSF',NULL,NULL,NULL),('PMAP-CutDB',NULL,NULL,NULL),('PRIDE',NULL,NULL,NULL),('PRINTS',NULL,NULL,NULL),('PRO',NULL,NULL,NULL),('ProDom',NULL,NULL,NULL),('PROSITE',NULL,NULL,NULL),('ProteinModelPortal',NULL,NULL,NULL),('Proteomes',NULL,NULL,NULL),('PubMed',NULL,NULL,NULL),('Reactome',NULL,NULL,NULL),('RefSeq',NULL,NULL,NULL),('REPRODUCTION-2DPAGE',NULL,NULL,NULL),('SABIO-RK',NULL,NULL,NULL),('SignaLink',NULL,NULL,NULL),('SMART',NULL,NULL,NULL),('SMR',NULL,NULL,NULL),('STRING','STRING ENSP mappings loaded from UniProt XML',NULL,NULL),('SUPFAM',NULL,NULL,NULL),('SWISS-2DPAGE',NULL,NULL,NULL),('TCDB',NULL,NULL,NULL),('TIGRFAMs',NULL,NULL,NULL),('TreeFam',NULL,NULL,NULL),('UCD-2DPAGE',NULL,NULL,NULL),('UCSC',NULL,NULL,NULL),('UniCarbKB',NULL,NULL,NULL),('UniGene',NULL,NULL,NULL),('UniPathway',NULL,NULL,NULL),('UniProt Keyword','UniProt keyword ids and values',NULL,NULL);
/*!40000 ALTER TABLE `xref_type` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-11-16 13:12:49
