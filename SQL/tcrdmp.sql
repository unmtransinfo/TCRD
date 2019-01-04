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

