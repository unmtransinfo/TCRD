import mysql.connector
from mysql.connector import Error
from credentials import *  # loads variables for DBHOST, DBNAME, USER, PWORD

# Save these variables in credentials.py, set them appropriately
# DBHOST = 'localhost'
# DBNAME = 'tcrd6'
# USER = 'test_user'
# PWORD = 'user_test'

### SQL Commands

drop_virus_table_sql = "DROP TABLE IF EXISTS virus"
drop_viral_protein_table_sql = "DROP TABLE IF EXISTS viral_protein"
drop_viral_ppi_table_sql = "DROP TABLE IF EXISTS viral_ppi"

create_virus_table_sql = """CREATE TABLE `virus` (
  `virusTaxid` VARCHAR(16) NOT NULL,
  `nucleic1` VARCHAR(128) NULL,
  `nucleic2` VARCHAR(128) NULL,
  `order` VARCHAR(128) NULL,
  `family` VARCHAR(128) NULL,
  `subfamily` VARCHAR(128) NULL,
  `genus` VARCHAR(128) NULL,
  `species` VARCHAR(128) NULL,
  `name` VARCHAR(128) NULL,
  PRIMARY KEY (`virusTaxid`)) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;"""

create_viral_protein_table_sql = """CREATE TABLE `viral_protein` (
    `id` INT NOT NULL,
    `name` VARCHAR(128) NULL,
    `ncbi` VARCHAR(128) NULL,
    `virus_id` VARCHAR(16) NULL,
    PRIMARY KEY (`id`),
    KEY `virus_id_idx` (`virus_id`),
    CONSTRAINT `virus_id` FOREIGN KEY (`virus_id`) REFERENCES `virus` (`virusTaxid`)) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;"""

create_viral_ppi_table_sql = """CREATE TABLE `viral_ppi` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `viral_protein_id` INT NOT NULL,
    `uniprot` VARCHAR(20) NOT NULL,
    `protein_id` INT ,
    `dataSource` VARCHAR(20) NULL,
    `finalLR` DECIMAL(20,12) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `viral_protein_id_idx` (`viral_protein_id`),
    KEY `protein_id_idx` (`protein_id`),
    CONSTRAINT `viral_protein_id` FOREIGN KEY (`viral_protein_id`) REFERENCES `viral_protein` (`id`),
    CONSTRAINT `protein_id` FOREIGN KEY (`protein_id`) REFERENCES `protein` (`id`)) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;"""

populate_virus_table_sql = """insert into virus values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
populate_viral_protein_table_sql = """insert into viral_protein values (%s, %s, %s, %s)"""
populate_viral_ppi_table_sql = """insert into viral_ppi values (NULL, %s, %s, NULL, 'P-HIPSTer', %s)"""

set_protein_id_for_ppi_table_sql = """UPDATE viral_ppi ppi, protein p
SET 
    ppi.protein_id = p.id
WHERE
    p.uniprot = ppi.uniprot
    and ppi.id > 0;"""

drop_uniprot_column_sql = """
    ALTER TABLE viral_ppi 
    DROP COLUMN `uniprot`;"""


### datastructures

class virus:  # for parsing lines of virus_taxonomy.txt into an object
    def __init__(self, line):
        fields = map_data_to_fields(line)
        self.virusTaxid = fields[0] if fields[0] != 'nan' else None
        self.nucleic1 = fields[1] if fields[1] != 'nan' else None
        self.nucleic2 = fields[2] if fields[2] != 'nan' else None
        self.order = fields[3] if fields[3] != 'nan' else None
        self.family = fields[4] if fields[4] != 'nan' else None
        self.subfamily = fields[5] if fields[5] != 'nan' else None
        self.genus = fields[6] if fields[6] != 'nan' else None
        self.species = fields[7] if fields[7] != 'nan' else None
        self.name = fields[8] if fields[8] != 'nan' else None

class vppi:  # for parsing lines of phipster_predictions into an object
    def __init__(self, line):
        fields = map_data_to_fields(line)
        interaction, self.symbol = fields[0].split(' ')
        self.symbol = self.symbol if self.symbol != 'nan' else None
        interaction, self.uniprot = interaction.split('|')
        virusID, self.virusProtID = interaction.split('_id')
        self.virusID = virusID.split('tx')[1]
        self.finalLR = fields[1]

class viral_protein:
    def __init__(self, id, name, ncbi, virus_id = None):
        self.id = id
        self.name = name
        self.ncbi = ncbi
        self.virus = virus_id


### ETL Commands
### Extract, i.e. load from file system

def load():
    protein_names = read_dict('../data/phipster/virProtein_name.txt')
    protein_ncbi = read_dict('../data/phipster/virProtein_ncbi.txt')
    virus_taxonomy = read_table('../data/phipster/virus_taxonomy.txt', virus)
    predicted_interactions = read_table('../data/phipster/phipster_predictions_finalLR100.txt', vppi)
    return virus_taxonomy, protein_names, protein_ncbi, predicted_interactions

def read_table(fileName, objClass):
    with open(fileName) as file_data:
        column_names = map_data_to_fields(file_data.readline())
        return [objClass(line) for line in file_data.readlines()]

def read_dict(fileName):
    with open(fileName) as file_data:
        column_names = map_data_to_fields(file_data.readline())
        return {map_data_to_fields(line)[0]: map_data_to_fields(line)[1] for line in file_data.readlines()}

def map_data_to_fields(line):
    return line.strip().split('\t')


### transform

def transform(protein_names, protein_ncbi, predicted_interactions):
    parent_map = {ppi.virusProtID : ppi.virusID for ppi in predicted_interactions}
    viral_protein_table = [viral_protein(id, name, protein_ncbi.get(id), parent_map.get(id)) for id, name in protein_names.items()]
    viral_ppi_table = [(ppi.virusProtID, ppi.uniprot, ppi.finalLR) for ppi in predicted_interactions]
    return viral_protein_table, viral_ppi_table


### load to DB
def drop_tables(cursor):
    cursor.execute(drop_viral_ppi_table_sql)
    cursor.execute(drop_viral_protein_table_sql)
    cursor.execute(drop_virus_table_sql)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in xrange(0, len(lst), n):
        yield lst[i:i + n]

def batch(cursor, sql, values, rowLimit):
    batches = list(chunks(values, rowLimit))
    for b in batches:
        cursor.executemany(sql, b)

def create_and_populate_viral_ppi_table(cursor, viral_ppi_table):
    print("creating viral_ppi table")
    cursor.execute(create_viral_ppi_table_sql)
    batch(cursor, populate_viral_ppi_table_sql, viral_ppi_table, 50000)
    cursor.execute(set_protein_id_for_ppi_table_sql)
    cursor.execute(drop_uniprot_column_sql)

def create_and_populate_viral_protein_table(cursor, viral_protein_table):
    print("creating viral_protein table")
    cursor.execute(create_viral_protein_table_sql)
    cursor.executemany(populate_viral_protein_table_sql,
                       [(viral_protein.id, viral_protein.name, viral_protein.ncbi, viral_protein.virus) for
                        viral_protein in viral_protein_table])

def create_and_populate_virus_table(cursor, virus_taxonomy):
    print("creating virus table")
    cursor.execute(create_virus_table_sql)
    cursor.executemany(populate_virus_table_sql, [(virus.virusTaxid, virus.nucleic1, virus.nucleic2, virus.order,
                                                   virus.family, virus.subfamily, virus.genus, virus.species,
                                                   virus.name) for virus in virus_taxonomy])

def writeToDatabase(virus_taxonomy, viral_protein_table, viral_ppi_table):
    """ Connect to MySQL database """
    conn = None
    try:
        conn = mysql.connector.connect(host=DBHOST,
                                       database=DBNAME,
                                       user=USER,
                                       password=PWORD)
        if conn.is_connected():
            print('Connected to MySQL database %s'%DBNAME)
            cursor = conn.cursor()

            drop_tables(cursor)
            create_and_populate_virus_table(cursor, virus_taxonomy)
            create_and_populate_viral_protein_table(cursor, viral_protein_table)
            create_and_populate_viral_ppi_table(cursor, viral_ppi_table)

            conn.commit()
            print('done')

    except Error as e:
        print(e)

    finally:
        if conn is not None and conn.is_connected():
            conn.commit()
            conn.close()




# LOAD raw data from files
virus_taxonomy, protein_names, protein_ncbi, predicted_interactions = load()

# transform into db table format
viral_protein_table, viral_ppi_table = transform(protein_names, protein_ncbi, predicted_interactions)

# write to db
writeToDatabase(virus_taxonomy, viral_protein_table, viral_ppi_table)
