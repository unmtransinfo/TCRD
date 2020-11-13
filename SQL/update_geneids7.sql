-- mysql> select id, name, description, sym, uniprot, geneid from protein where sym like 'HSPA1%';
-- +-------+-------------+----------------------------------+---------+---------+--------+
-- | id    | name        | description                      | sym     | uniprot | geneid |
-- +-------+-------------+----------------------------------+---------+---------+--------+
-- |  2350 | HS71B_HUMAN | Heat shock 70 kDa protein 1B     | HSPA1B  | P0DMV9  |   3303 |
-- |  5265 | HS71L_HUMAN | Heat shock 70 kDa protein 1-like | HSPA1L  | P34931  |   3305 |
-- | 10323 | HSP7E_HUMAN | Heat shock 70 kDa protein 14     | HSPA14  | Q0VDF9  |  51182 |
-- | 10802 | HS12A_HUMAN | Heat shock 70 kDa protein 12A    | HSPA12A | O43301  | 259217 |
-- | 11985 | HS12B_HUMAN | Heat shock 70 kDa protein 12B    | HSPA12B | Q96MM6  | 116835 |
-- | 12229 | HS71A_HUMAN | Heat shock 70 kDa protein 1A     | HSPA1A  | P0DMV8  |   3303 |
-- | 12720 | HSP13_HUMAN | Heat shock 70 kDa protein 13     | HSPA13  | P48723  |   6782 |
-- +-------+-------------+----------------------------------+---------+---------+--------+
UPDATE protein SET geneid = 3304 WHERE sym = 'HSPA1B';

-- mysql> select id, name, description, sym, uniprot, geneid from protein where sym like 'GPR89%';
-- +------+-------------+----------------------+--------+---------+--------+
-- | id   | name        | description          | sym    | uniprot | geneid |
-- +------+-------------+----------------------+--------+---------+--------+
-- | 9832 | GPHRA_HUMAN | Golgi pH regulator A | GPR89A | B7ZAQ6  |  51463 |
-- | 9833 | GPHRB_HUMAN | Golgi pH regulator B | GPR89B | P0CG08  |  51463 |
-- +------+-------------+----------------------+--------+---------+--------+
UPDATE protein SET geneid = 653519 WHERE sym = 'GPR89B';

-- mysql> select id, name, description, sym, uniprot, geneid from protein where uniprot like 'P0C0L%';
-- +-------+------------+-----------------+------+---------+-----------+
-- | id    | name       | description     | sym  | uniprot | geneid    |
-- +-------+------------+-----------------+------+---------+-----------+
-- | 10749 | CO4A_HUMAN | Complement C4-A | C4A  | P0C0L4  |       720 |
-- | 10747 | CO4B_HUMAN | Complement C4-B | C4B  | P0C0L5  | 100293534 |
-- +-------+------------+-----------------+------+---------+-----------+
UPDATE protein set geneid = 721 WHERE uniprot = 'P0C0L5';

-- mysql> select id, name, description, sym, uniprot, geneid from protein where sym like 'CALM%';
-- +-------+-------------+---------------------------+--------+---------+--------+
-- | id    | name        | description               | sym    | uniprot | geneid |
-- +-------+-------------+---------------------------+--------+---------+--------+
-- |   979 | CALL4_HUMAN | Calmodulin-like protein 4 | CALML4 | Q96GE6  |  91860 |
-- |  1033 | CALL5_HUMAN | Calmodulin-like protein 5 | CALML5 | Q9NZT1  |  51806 |
-- | 11902 | CALL3_HUMAN | Calmodulin-like protein 3 | CALML3 | P27482  |    810 |
-- | 12434 | CALM1_HUMAN | Calmodulin-1              | CALM1  | P0DP23  |    801 |
-- | 12769 | CALM2_HUMAN | Calmodulin-2              | CALM2  | P0DP24  |    801 |
-- | 13378 | CALL6_HUMAN | Calmodulin-like protein 6 | CALML6 | Q8TD86  | 163688 |
-- | 13380 | CALM3_HUMAN | Calmodulin-3              | CALM3  | P0DP25  |    801 |
-- +-------+-------------+---------------------------+--------+---------+--------+
UPDATE protein set geneid = 805 WHERE uniprot = 'P0DP24';
UPDATE protein set geneid = 808 WHERE uniprot = 'P0DP25';

-- Above are one's I've known about previously
-- Let's find some more...
-- mysql> SELECT geneid, COUNT(*) c FROM protein GROUP BY geneid HAVING c > 1;
-- +-----------+------+
-- | geneid    | c    |
-- +-----------+------+
-- |      NULL | 1511 |
-- |       463 |    2 |
-- |       670 |    2 |
-- |       796 |    2 |
-- |      1029 |    2 |
-- |      1442 |    2 |
-- |      1523 |    2 |
-- |      2074 |    2 |
-- |      2778 |    4 |
-- |      3017 |    2 |
-- |      4338 |    2 |
-- |      5414 |    2 |
-- |      5621 |    2 |
-- |      6399 |    2 |
-- |      7112 |    2 |
-- |      8209 |    2 |
-- |      9369 |    2 |
-- |      9378 |    2 |
-- |      9379 |    2 |
-- |      9465 |    2 |
-- |      9910 |    2 |
-- |     10326 |    2 |
-- |     10407 |    2 |
-- |     11013 |    2 |
-- |     11163 |    2 |
-- |     22891 |    2 |
-- |     27113 |    2 |
-- |     27433 |    2 |
-- |     51082 |    2 |
-- |     51207 |    2 |
-- |     81488 |    2 |
-- |     83871 |    2 |
-- |    113457 |    2 |
-- |    122183 |    5 |
-- |    158055 |    2 |
-- |    163590 |    2 |
-- |    220074 |    2 |
-- |    220869 |    2 |
-- |    221960 |    2 |
-- |    222967 |    2 |
-- |    378949 |    2 |
-- |    388372 |    2 |
-- |    388677 |    2 |
-- |    399668 |    2 |
-- |    445329 |    2 |
-- |    445815 |    2 |
-- |    728279 |    2 |
-- |    728945 |    2 |
-- |    730755 |    2 |
-- | 100008586 |    4 |
-- | 100129239 |    2 |
-- | 100129407 |    2 |
-- | 100131608 |    2 |
-- | 100133093 |    3 |
-- | 100133267 |    2 |
-- | 100134938 |    2 |
-- | 100287399 |    2 |
-- | 100288695 |    2 |
-- | 100289087 |    3 |
-- | 100302736 |    2 |
-- | 100996758 |    2 |
-- | 101059938 |    2 |
-- | 101060211 |    3 |
-- | 101060233 |    3 |
-- | 101060301 |    2 |
-- | 101060321 |    2 |
-- | 101928147 |    2 |
-- | 102723680 |    3 |
-- | 102724428 |    2 |
-- | 102724560 |    2 |
-- | 102724594 |    2 |
-- | 102724652 |    2 |
-- | 105373251 |    2 |
-- | 110599583 |    2 |
-- +-----------+------+
-- Go through these manually and fix those required as below

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 670;
-- +-------+------------+---------------------------------+------+---------+--------+
-- | id    | name       | description                     | sym  | uniprot | geneid |
-- +-------+------------+---------------------------------+------+---------+--------+
-- |  7517 | PARG_HUMAN | Poly(ADP-ribose) glycohydrolase | PARG | Q86W56  |    670 |
-- | 15296 | BPHL_HUMAN | Valacyclovir hydrolase          | BPHL | Q86WA6  |    670 |
-- +-------+------------+---------------------------------+------+---------+--------+
UPDATE protein set geneid = 8505 WHERE uniprot = 'Q86W56';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 1442;
-- +------+------------+---------------------------------------+------+---------+--------+
-- | id   | name       | description                           | sym  | uniprot | geneid |
-- +------+------------+---------------------------------------+------+---------+--------+
-- |  515 | CSH1_HUMAN | Chorionic somatomammotropin hormone 1 | CSH1 | P0DML2  |   1442 |
-- | 1452 | CSH2_HUMAN | Chorionic somatomammotropin hormone 2 | CSH2 | P0DML3  |   1442 |
-- +------+------------+---------------------------------------+------+---------+--------+
UPDATE protein set geneid = 1443 WHERE uniprot = 'P0DML3';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 3017;
-- +-------+-------------+------------------------------+-------+---------+--------+
-- | id    | name        | description                  | sym   | uniprot | geneid |
-- +-------+-------------+------------------------------+-------+---------+--------+
-- |  5261 | H2B1D_HUMAN | Histone H2B type 1-D         | H2BC5 | P58876  |   3017 |
-- | 13564 | H2B1C_HUMAN | Histone H2B type 1-C/E/F/G/I | H2BC4 | P62807  |   3017 |
-- +-------+-------------+------------------------------+-------+---------+--------+
UPDATE protein set geneid = 8347 WHERE uniprot = 'P62807';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 6399;
-- +-------+-------------+-------------------------------------------------+----------+---------+--------+
-- | id    | name        | description                                     | sym      | uniprot | geneid |
-- +-------+-------------+-------------------------------------------------+----------+---------+--------+
-- | 17620 | TPC2B_HUMAN | Trafficking protein particle complex subunit 2B | TRAPPC2B | P0DI82  |   6399 |
-- | 20235 | TPC2A_HUMAN | Trafficking protein particle complex subunit 2  | TRAPPC2  | P0DI81  |   6399 |
-- +-------+-------------+-------------------------------------------------+----------+---------+--------+
-- UniProt just has this one WRONG, no duplicates
UPDATE protein set geneid = 10597 WHERE uniprot = 'P0DI82';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 10407;
-- +------+-------------+------------------------------+---------+---------+--------+
-- | id   | name        | description                  | sym     | uniprot | geneid |
-- +------+-------------+------------------------------+---------+---------+--------+
-- | 7620 | SG11A_HUMAN | Sperm-associated antigen 11A | SPAG11A | Q6PDA7  |  10407 |
-- | 7926 | SG11B_HUMAN | Sperm-associated antigen 11B | SPAG11B | Q08648  |  10407 |
-- +------+-------------+------------------------------+---------+---------+--------+
UPDATE protein set geneid = 653423 WHERE uniprot = 'Q6PDA7';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 11013;
-- +------+-------------+-------------------+---------+---------+--------+
-- | id    | name        | description       | sym     | uniprot | geneid |
-- +-------+-------------+-------------------+---------+---------+--------+
-- | 17929 | TB15B_HUMAN | Thymosin beta-15B | TMSB15B | P0CG35  |  11013 |
-- | 19177 | TB15A_HUMAN | Thymosin beta-15A | TMSB15A | P0CG34  |  11013 |
-- +-------+-------------+-------------------+---------+---------+--------+
UPDATE protein set geneid = 286527 WHERE uniprot = 'P0CG35';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 113457;
-- +-------+-------------+------------------------+--------+---------+--------+
-- | id    | name        | description            | sym    | uniprot | geneid |
-- +-------+-------------+------------------------+--------+---------+--------+
-- |  4845 | TBA3D_HUMAN | Tubulin alpha-3D chain | TUBA3D | P0DPH8  | 113457 |
-- | 19680 | TBA3C_HUMAN | Tubulin alpha-3C chain | TUBA3C | P0DPH7  | 113457 |
-- +-------+-------------+------------------------+--------+---------+--------+
UPDATE protein set geneid = 7278 WHERE uniprot = 'P0DPH7';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 122183;
-- +-------+-------------+--------------------------+--------+---------+--------+
-- | id    | name        | description              | sym    | uniprot | geneid |
-- +-------+-------------+--------------------------+--------+---------+--------+
-- |  3885 | PR20B_HUMAN | Proline-rich protein 20B | PRR20B | P86481  | 122183 |
-- |  5019 | PR20D_HUMAN | Proline-rich protein 20D | PRR20D | P86480  | 122183 |
-- |  7869 | PR20A_HUMAN | Proline-rich protein 20A | PRR20A | P86496  | 122183 |
-- |  8208 | PR20C_HUMAN | Proline-rich protein 20C | PRR20C | P86479  | 122183 |
-- | 18940 | PR20E_HUMAN | Proline-rich protein 20E | PRR20E | P86478  | 122183 |
-- +-------+-------------+--------------------------+--------+---------+--------+
UPDATE protein set geneid = 729233 WHERE uniprot = 'P86481';
UPDATE protein set geneid = 729240 WHERE uniprot = 'P86479';
UPDATE protein set geneid = 729246 WHERE uniprot = 'P86480';
UPDATE protein set geneid = 729250 WHERE uniprot = 'P86478';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 220869;
-- +-------+-------------+----------------------------------+-------+---------+--------+
-- | id    | name        | description                      | sym   | uniprot | geneid |
-- +-------+-------------+----------------------------------+-------+---------+--------+
-- | 11189 | CBWD5_HUMAN | COBW domain-containing protein 5 | CBWD5 | Q5RIA9  | 220869 |
-- | 15373 | CBWD3_HUMAN | COBW domain-containing protein 3 | CBWD3 | Q5JTY5  | 220869 |
-- +-------+-------------+----------------------------------+-------+---------+--------+
UPDATE protein set geneid = 465129 WHERE uniprot = 'Q5JTY5';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 221960;
-- +------+-------------+----------------------------------------+-------+---------+--------+
-- | id   | name        | description                            | sym   | uniprot | geneid |
-- +-----+-------------+----------------------------------------+-------+---------+--------+
-- |  85 | CCZ1_HUMAN  | Vacuolar fusion protein CCZ1 homolog   | CCZ1  | P86791  | 221960 |
-- | 856 | CCZ1B_HUMAN | Vacuolar fusion protein CCZ1 homolog B | CCZ1B | P86790  | 221960 |
-- +-----+-------------+----------------------------------------+-------+---------+--------+
UPDATE protein set geneid = 852428 WHERE uniprot = 'P86791';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 222967;
-- +------+-------------+---------------------------------+----------+---------+--------+
-- | id   | name        | description                     | sym      | uniprot | geneid |
-- +------+-------------+---------------------------------+----------+---------+--------+
-- | 9084 | R10B2_HUMAN | Radial spoke head 10 homolog B2 | RSPH10B2 | B2RC85  | 222967 |
-- | 9600 | R10B1_HUMAN | Radial spoke head 10 homolog B  | RSPH10B  | P0C881  | 222967 |
-- +------+-------------+---------------------------------+----------+---------+--------+
UPDATE protein set geneid = 728194 WHERE uniprot = 'B2RC85';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 378949;
-- +-------+-------------+-------------------------------------------------------------+---------+---------+--------+
-- | id    | name        | description                                                 | sym     | uniprot | geneid |
-- +-------+-------------+-------------------------------------------------------------+---------+---------+--------+
-- | 18965 | RBY1A_HUMAN | RNA-binding motif protein, Y chromosome, family 1 member A1 | RBMY1A1 | P0DJD3  | 378949 |
-- | 19828 | RBY1D_HUMAN | RNA-binding motif protein, Y chromosome, family 1 member D  | RBMY1D  | P0C7P1  | 378949 |
-- +-------+-------------+-------------------------------------------------------------+---------+---------+--------+
UPDATE protein set geneid = 5940 WHERE uniprot = 'P0DJD3';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 388372;
-- +-------+------------+----------------------------+--------+---------+--------+
-- | id    | name       | description                | sym    | uniprot | geneid |
-- +-------+------------+----------------------------+--------+---------+--------+
-- |  3501 | CCL4_HUMAN | C-C motif chemokine 4      | CCL4   | P13236  | 388372 |
-- | 10729 | CC4L_HUMAN | C-C motif chemokine 4-like | CCL4L1 | Q8NHW4  | 388372 |
-- +-------+------------+----------------------------+--------+---------+--------+
UPDATE protein set geneid = 6351 WHERE uniprot = 'P13236';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 399668;
-- +------+-------------+----------------------------------------------------+-----------+---------+--------+
-- | id   | name        | description                                        | sym       | uniprot | geneid |
-- +------+-------------+----------------------------------------------------+-----------+---------+--------+
-- | 3930 | SIL2B_HUMAN | Small integral membrane protein 10-like protein 2B | SMIM10L2B | P0DMW5  | 399668 |
-- | 3933 | SIL2A_HUMAN | Small integral membrane protein 10-like protein 2A | SMIM10L2A | P0DMW4  | 399668 |
-- +------+-------------+----------------------------------------------------+-----------+---------+--------+
UPDATE protein set geneid = 644596 WHERE uniprot = 'P0DMW5';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 445329;
-- +-------+-------------+----------------------+---------+---------+--------+
-- | id    | name        | description          | sym     | uniprot | geneid |
-- +-------+-------------+----------------------+---------+---------+--------+
-- | 15795 | ST1A4_HUMAN | Sulfotransferase 1A4 | SULT1A4 | P0DMN0  | 445329 |
-- | 19301 | ST1A3_HUMAN | Sulfotransferase 1A3 | SULT1A3 | P0DMM9  | 445329 |
-- +-------+-------------+----------------------+---------+---------+--------+
UPDATE protein set geneid = 6818 WHERE uniprot = 'P0DMM9';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 728279;
-- +------+-------------+--------------------------------+----------+---------+--------+
| id   | name        | description                    | sym      | uniprot | geneid |
+------+-------------+--------------------------------+----------+---------+--------+
| 2748 | KRA21_HUMAN | Keratin-associated protein 2-1 | KRTAP2-1 | Q9BYU5  | 728279 |
| 5690 | KRA22_HUMAN | Keratin-associated protein 2-2 | KRTAP2-2 | Q9BYT5  | 728279 |
+------+-------------+--------------------------------+----------+---------+--------+
UPDATE protein set geneid = 81872 WHERE uniprot = 'Q9BYU5';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 728945;
-- +------+-------------+-----------------------------------------------+---------+------------+--------+
-- | id   | name        | description                                   | sym     | uniprot    | geneid |
-- +------+-------------+-----------------------------------------------+---------+------------+--------+
-- | 6439 | PAL4F_HUMAN | Peptidyl-prolyl cis-trans isomerase A-like 4F | PPIAL4F | P0DN26     | 728945 |
-- | 8650 | PAL4E_HUMAN | Peptidyl-prolyl cis-trans isomerase A-like 4E | PPIAL4E | A0A075B759 | 728945 |
-- +------+-------------+-----------------------------------------------+---------+------------+--------+
UPDATE protein set geneid = 730262 WHERE uniprot = 'A0A075B759';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 730755;
-- +-------+-------------+--------------------------------+----------+---------+--------+
-- | id    | name        | description                    | sym      | uniprot | geneid |
-- +-------+-------------+--------------------------------+----------+---------+--------+
-- |  6269 | KRA24_HUMAN | Keratin-associated protein 2-4 | KRTAP2-4 | Q9BYR9  | 730755 |
-- | 10369 | KRA23_HUMAN | Keratin-associated protein 2-3 | KRTAP2-3 | P0C7H8  | 730755 |
-- +-------+-------------+--------------------------------+----------+---------+--------+
UPDATE protein set geneid = 85294 WHERE uniprot = 'Q9BYR9';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100008586;
-- +-------+-------------+---------------+---------+---------+-----------+
-- | id    | name        | description   | sym     | uniprot | geneid    |
-- +-------+-------------+---------------+---------+---------+-----------+
-- | 12200 | GG12I_HUMAN | G antigen 12I | GAGE12I | P0CL82  | 100008586 |
-- | 13240 | GG12F_HUMAN | G antigen 12F | GAGE12F | P0CL80  | 100008586 |
-- | 13242 | GG12G_HUMAN | G antigen 12G | GAGE12G | P0CL81  | 100008586 |
-- | 13348 | GAGE7_HUMAN | G antigen 7   | GAGE7   | O76087  | 100008586 |
-- +-------+-------------+---------------+---------+---------+-----------+
UPDATE protein set geneid = 26748 WHERE uniprot = 'P0CL82';
UPDATE protein set geneid = 645073 WHERE uniprot = 'P0CL81';
UPDATE protein set geneid = 2579 WHERE uniprot = 'O76087';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100129239;
-- +-------+-------------+----------------------------------+----------+------------+-----------+
-- | id    | name        | description                      | sym      | uniprot    | geneid    |
-- +-------+-------------+----------------------------------+----------+------------+-----------+
-- |   211 | CX05B_HUMAN | Uncharacterized protein CXorf51B | CXorf51B | P0DPH9     | 100129239 |
-- | 14315 | CX05A_HUMAN | Uncharacterized protein CXorf51A | CXorf51A | A0A1B0GTR3 | 100129239 |
-- +-------+-------------+----------------------------------+----------+------------+-----------+
UPDATE protein set geneid = 100133053 WHERE uniprot = 'P0DPH9';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100129407;
-- +-------+-------------+-----------------+---------+------------+-----------+
-- | id    | name        | description     | sym     | uniprot    | geneid    |
-- +-------+-------------+-----------------+---------+------------+-----------+
-- | 11527 | F236A_HUMAN | Protein FAM236A | FAM236A | A0A1B0GUQ0 | 100129407 |
-- | 12683 | F236B_HUMAN | Protein FAM236B | FAM236B | A0A1B0GV22 | 100129407 |
-- +-------+-------------+-----------------+---------+------------+-----------+
UPDATE protein set geneid = 100132304 WHERE uniprot = 'A0A1B0GV22';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100131608;
-- +------+-------------+---------------------------+---------+---------+-----------+
-- | id   | name        | description               | sym     | uniprot | geneid    |
-- +------+-------------+---------------------------+---------+---------+-----------+
-- | 7194 | P23D1_HUMAN | Proline-rich protein 23D1 | PRR23D1 | E9PI22  | 100131608 |
-- | 9154 | P23D2_HUMAN | Proline-rich protein 23D2 | PRR23D2 | P0DMB1  | 100131608 |
-- +------+-------------+---------------------------+---------+---------+-----------+
UPDATE protein set geneid = 100133251 WHERE uniprot = 'P0DMB1';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100133093;
-- +-------+-------------+----------------+--------+---------+-----------+
-- | id    | name        | description    | sym    | uniprot | geneid    |
-- +-------+-------------+----------------+--------+---------+-----------+
-- |  3204 | FM25A_HUMAN | Protein FAM25A | FAM25A | B3EWG3  | 100133093 |
-- |  5435 | FM25G_HUMAN | Protein FAM25G | FAM25G | B3EWG6  | 100133093 |
-- | 12447 | FM25C_HUMAN | Protein FAM25C | FAM25C | B3EWG5  | 100133093 |
-- +-------+-------------+----------------+--------+---------+-----------+
UPDATE protein set geneid = 643161 WHERE uniprot = 'B3EWG3';
UPDATE protein set geneid = 644054 WHERE uniprot = 'B3EWG5';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100133267;
-- +------+-------------+--------------------+----------+---------+-----------+
-- | id   | name        | description        | sym      | uniprot | geneid    |
-- +------+-------------+--------------------+----------+---------+-----------+
-- |  575 | D130B_HUMAN | Beta-defensin 130B | DEFB130B | P0DP73  | 100133267 |
-- | 1580 | D130A_HUMAN | Beta-defensin 130A | DEFB130A | P0DP74  | 100133267 |
-- +------+-------------+--------------------+----------+---------+-----------+
UPDATE protein set geneid = 245940 WHERE uniprot = 'P0DP74';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100134938;
-- +-------+-------------+-----------------------------+---------+---------+-----------+
-- | id    | name        | description                 | sym     | uniprot | geneid    |
-- +-------+-------------+-----------------------------+---------+---------+-----------+
-- | 17178 | UPK3L_HUMAN | Uroplakin-3b-like protein 1 | UPK3BL1 | B0FP48  | 100134938 |
-- | 18145 | UPKL2_HUMAN | Uroplakin-3b-like protein 2 | UPK3BL2 | E5RIL1  | 100134938 |
-- +-------+-------------+-----------------------------+---------+---------+-----------+
UPDATE protein set geneid = 107983993 WHERE uniprot = 'E5RIL1';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100287399;
-- +-------+-------------+--------------------------------------+--------+------------+-----------+
-- | id    | name        | description                          | sym    | uniprot    | geneid    |
-- +-------+-------------+--------------------------------------+--------+------------+-----------+
-- |  9422 | POTB2_HUMAN | POTE ankyrin domain family member B2 | POTEB2 | H3BUK9     | 100287399 |
-- | 15466 | POTEB_HUMAN | POTE ankyrin domain family member B  | POTEB  | A0A0A6YYL3 | 100287399 |
-- +-------+-------------+--------------------------------------+--------+------------+-----------+
UPDATE protein set geneid = 100996331 WHERE uniprot = 'A0A0A6YYL3';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100288695;
-- +-------+-------------+-----------------------------------------------------------------+-------+---------+-----------+
-- | id    | name        | description                                                     | sym   | uniprot | geneid    |
-- +-------+-------------+-----------------------------------------------------------------+-------+---------+-----------+
-- | 2905 | LIMS3_HUMAN | LIM and senescent cell antigen-like-containing domain protein 3 | LIMS3 | P0CW19  | 100288695 |
-- | 8106 | LIMS4_HUMAN | LIM and senescent cell antigen-like-containing domain protein 4 | LIMS4 | P0CW20  | 100288695 |
-- +-------+-------------+-----------------------------------------------------------------+-------+---------+-----------+
UPDATE protein set geneid = 96626 WHERE uniprot = 'P0CW19';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100289087;
-- +------+-------------+--------------------------------------+--------+---------+-----------+
-- | id   | name        | description                          | sym    | uniprot | geneid    |
-- +------+-------------+--------------------------------------+--------+---------+-----------+
-- | 16730 | TSPY3_HUMAN | Testis-specific Y-encoded protein 3  | TSPY3  | P0CV98  | 100289087 |
-- | 18091 | TSPY1_HUMAN | Testis-specific Y-encoded protein 1  | TSPY1  | Q01534  | 100289087 |
-- | 18233 | TSPYA_HUMAN | Testis-specific Y-encoded protein 10 | TSPY10 | P0CW01  | 100289087 |
-- +------+-------------+--------------------------------------+--------+---------+-----------+
UPDATE protein set geneid = 7258 WHERE uniprot = 'Q01534';
UPDATE protein set geneid = 728137 WHERE uniprot = 'P0CV98';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 100302736;
-- +------+-------------+-------------------------------------------------+--------+---------+-----------+
-- | id   | name        | description                                     | sym    | uniprot | geneid    |
-- +------+-------------+-------------------------------------------------+--------+---------+-----------+
-- | 16286 | TCAM2_HUMAN | TIR domain-containing adapter molecule 2        | TICAM2 | Q86XR7  | 100302736 |
-- | 19343 | TMED7_HUMAN | Transmembrane emp24 domain-containing protein 7 | TMED7  | Q9Y3B3  | 100302736 |
-- +------+-------------+-------------------------------------------------+--------+---------+-----------+
UPDATE protein set geneid = 51014 WHERE uniprot = 'Q9Y3B3';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 388677;
-- +-------+-------------+-------------------------------------------+-----------+---------+-----------+
-- | id    | name        | description                               | sym       | uniprot | geneid    |
-- +-------+-------------+-------------------------------------------+-----------+---------+-----------+
-- | 7186 | NT2NA_HUMAN | Notch homolog 2 N-terminal-like protein A | NOTCH2NLA | Q7Z3S9  | 388677 |
-- | 7339 | NT2NC_HUMAN | Notch homolog 2 N-terminal-like protein C | NOTCH2NLC | P0DPK4  | 388677 |
-- +-------+-------------+-------------------------------------------+-----------+---------+-----------+
UPDATE protein set geneid = 100996717 WHERE uniprot = 'P0DPK4';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 101059938;
-- +-------+-------------+-----------------------------------------------------------+--------+---------+-----------+
-- | id    | name        | description                                               | sym    | uniprot | geneid    |
-- +-------+-------------+-----------------------------------------------------------+--------+---------+-----------+
-- | 2440 | NPIA7_HUMAN | Nuclear pore complex-interacting protein family member A7 | NPIPA7 | E9PJI5  | 101059938 |
-- | 7979 | NPIA8_HUMAN | Nuclear pore complex-interacting protein family member A8 | NPIPA8 | P0DM63  | 101059938 |
-- +-------+-------------+-----------------------------------------------------------+--------+---------+-----------+
UPDATE protein set geneid = 101059953 WHERE uniprot = 'P0DM63';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 101060211;
-- +------+-------------+-------------------------------------------+--------+---------+-----------+
-- | id   | name        | description                               | sym    | uniprot | geneid    |
-- +------+-------------+-------------------------------------------+--------+---------+-----------+
-- |   920 | CT457_HUMAN | Cancer/testis antigen family 45 member A7 | CT45A7 | P0DMV0  | 101060211 |
-- | 13717 | CT456_HUMAN | Cancer/testis antigen family 45 member A6 | CT45A6 | P0DMU7  | 101060211 |
-- | 14607 | CT455_HUMAN | Cancer/testis antigen family 45 member A5 | CT45A5 | P0DMU8  | 101060211 |
-- +------+-------------+-------------------------------------------+--------+---------+-----------+
UPDATE protein set geneid = 441521 WHERE uniprot = 'P0DMU8';
UPDATE protein set geneid = 541465 WHERE uniprot = 'P0DMU7';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 101060233;
-- +-------+-------------+-------------------------------+---------+---------+-----------+
-- | id    | name        | description                   | sym     | uniprot | geneid    |
-- +-------+-------------+-------------------------------+---------+---------+-----------+
-- |  5555 | OPSG_HUMAN  | Medium-wave-sensitive opsin 1 | OPN1MW  | P04001  | 101060233 |
-- |  8527 | OPSG3_HUMAN | Medium-wave-sensitive opsin 3 | OPN1MW3 | P0DN78  | 101060233 |
-- | 19072 | OPSG2_HUMAN | Medium-wave-sensitive opsin 2 | OPN1MW2 | P0DN77  | 101060233 |
-- +-------+-------------+-------------------------------+---------+---------+-----------+
UPDATE protein set geneid = 2652 WHERE uniprot = 'P04001';
UPDATE protein set geneid = 728458 WHERE uniprot = 'P0DN77';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 101060301;
-- +------+-------------+--------------------------------------------------+----------+---------+-----------+
-- | id   | name        | description                                      | sym      | uniprot | geneid    |
-- +------+-------------+--------------------------------------------------+----------+---------+-----------+
-- | 3246 | HNRC3_HUMAN | Heterogeneous nuclear ribonucleoprotein C-like 3 | HNRNPCL3 | B7ZW38  | 101060301 |
-- | 3567 | HNRC4_HUMAN | Heterogeneous nuclear ribonucleoprotein C-like 4 | HNRNPCL4 | P0DMR1  | 101060301 |
-- +------+-------------+--------------------------------------------------+----------+---------+-----------+
UPDATE protein set geneid = 649330 WHERE uniprot = 'B7ZW38';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 101060321;
-- +-------+-------------+------------------------------+---------+---------+-----------+
-- | id    | name        | description                  | sym     | uniprot | geneid    |
-- +-------+-------------+------------------------------+---------+---------+-----------+
-- |  4346 | TBC3G_HUMAN | TBC1 domain family member 3G | TBC1D3G | Q6DHY5  | 101060321 |
-- | 19521 | TBC3C_HUMAN | TBC1 domain family member 3C | TBC1D3C | Q6IPX1  | 101060321 |
-- +-------+-------------+------------------------------+---------+---------+-----------+
UPDATE protein set geneid = 414060 WHERE uniprot = 'Q6IPX1';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 101928147;
-- +------+-------------+-----------------+---------+---------+-----------+
-- | id   | name        | description     | sym     | uniprot | geneid    |
-- +------+-------------+-----------------+---------+---------+-----------+
-- | 15127 | F243B_HUMAN | Protein FAM243B | FAM243B | P0DPQ4  | 101928147 |
-- | 20333 | F243A_HUMAN | Protein FAM243A | FAM243A | B9A014  | 101928147 |
-- +------+-------------+-----------------+---------+---------+-----------+
UPDATE protein set geneid = 102723451 WHERE uniprot = 'P0DPQ4';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 102723680;
-- +------+-------------+-------------------------------------------+--------+---------+-----------+
-- | id   | name        | description                               | sym    | uniprot | geneid    |
-- +------+-------------+-------------------------------------------+--------+---------+-----------+
-- |  9814 | CT452_HUMAN | Cancer/testis antigen family 45 member A2 | CT45A2 | Q5DJT8  | 102723680 |
-- | 11060 | CT459_HUMAN | Cancer/testis antigen family 45 member A9 | CT45A9 | P0DMV2  | 102723680 |
-- | 15085 | CT458_HUMAN | Cancer/testis antigen family 45 member A8 | CT45A8 | P0DMV1  | 102723680 |
-- +------+-------------+-------------------------------------------+--------+---------+-----------+
UPDATE protein set geneid = 728911 WHERE uniprot = 'Q5DJT8';
UPDATE protein set geneid = 102723737 WHERE uniprot = 'P0DMV1';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 102724428;
-- +------+-------------+------------------------------------------------+-------+------------+-----------+
-- | id   | name        | description                                    | sym   | uniprot    | geneid    |
-- +------+-------------+------------------------------------------------+-------+------------+-----------+
-- | 15509 | SIK1B_HUMAN | Probable serine/threonine-protein kinase SIK1B | SIK1B | A0A0B4J2F2 | 102724428 |
-- | 15510 | SIK1_HUMAN  | Serine/threonine-protein kinase SIK1           | SIK1  | P57059     | 102724428 |
-- +------+-------------+------------------------------------------------+-------+------------+-----------+
UPDATE protein set geneid = 150094 WHERE uniprot = 'P57059';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 102724560;
-- +-------+------------+------------------------------------------+------+---------+-----------+
-- | id    | name       | description                              | sym  | uniprot | geneid    |
-- +-------+------------+------------------------------------------+------+---------+-----------+
-- |  1036 | CBS_HUMAN  | Cystathionine beta-synthase              | CBS  | P35520  | 102724560 |
-- | 10575 | CBSL_HUMAN | Cystathionine beta-synthase-like protein | CBSL | P0DN79  | 102724560 |
-- +-------+------------+------------------------------------------+------+---------+-----------+
UPDATE protein set geneid = 875 WHERE uniprot = 'P35520';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 102724594;
-- +------+-------------+--------------------------------------------------+---------+---------+-----------+
-- | id   | name        | description                                      | sym     | uniprot | geneid    |
-- +------+-------------+--------------------------------------------------+---------+---------+-----------+
-- |  4182 | U2AF5_HUMAN | Splicing factor U2AF 35 kDa subunit-like protein | U2AF1L5 | P0DN76  | 102724594 |
-- | 17062 | U2AF1_HUMAN | Splicing factor U2AF 35 kDa subunit              | U2AF1   | Q01081  | 102724594 |
-- +------+-------------+--------------------------------------------------+---------+---------+-----------+
UPDATE protein set geneid = 7307 WHERE uniprot = 'Q01081';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 102724652;
-- +-----+-------------+---------------------------+--------+------------+-----------+
-- | id  | name        | description               | sym    | uniprot    | geneid    |
-- +-----+-------------+---------------------------+--------+------------+-----------+
-- | 1384 | CRYAA_HUMAN | Alpha-crystallin A chain  | CRYAA  | P02489     | 102724652 |
-- | 6016 | CRYA2_HUMAN | Alpha-crystallin A2 chain | CRYAA2 | A0A140G945 | 102724652 |
-- +-----+-------------+---------------------------+--------+------------+-----------+
UPDATE protein set geneid = 1404 WHERE uniprot = 'P02489';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 105373251;
-- +------+-------------+-----------------+---------+------------+-----------+
-- | id   | name        | description     | sym     | uniprot    | geneid    |
-- +------+-------------+-----------------+---------+------------+-----------+
-- | 13759 | F236C_HUMAN | Protein FAM236C | FAM236C | P0DP71     | 105373251 |
-- | 14702 | F236D_HUMAN | Protein FAM236D | FAM236D | A0A1B0GTK5 | 105373251 |
-- +------+-------------+-----------------+---------+------------+-----------+
UPDATE protein set geneid = 109729126 WHERE uniprot = 'P0DP71';

-- mysql> SELECT id, name, description, sym, uniprot, geneid from protein where geneid = 110599583;
-- +------+-------------+-----------------------------------------------+----------------+---------+-----------+
-- | id   | name        | description                                   | sym            | uniprot | geneid    |
-- +------+-------------+-----------------------------------------------+----------------+---------+-----------+
-- |   145 | EFCE2_HUMAN | EEF1AKMT4-ECE2 readthrough transcript protein | EEF1AKMT4-ECE2 | P0DPD8  | 110599583 |
-- | 14689 | ECE2_HUMAN  | Endothelin-converting enzyme 2                | ECE2           | P0DPD6  | 110599583 |
-- +------+-------------+-----------------------------------------------+----------------+---------+-----------+
UPDATE protein set geneid = 9718 WHERE uniprot = 'P0DPD6';

-- mysql> SELECT geneid, COUNT(*) c FROM protein GROUP BY geneid HAVING c > 1;
-- +-----------+------+
-- | geneid    | c    |
-- +-----------+------+
-- |      NULL | 1511 |
-- |       463 |    2 |
-- |       796 |    2 |
-- |      1029 |    2 |
-- |      1404 |    2 |
-- |      1523 |    2 |
-- |      2074 |    2 |
-- |      2778 |    4 |
-- |      4338 |    2 |
-- |      5414 |    2 |
-- |      5621 |    2 |
-- |      7112 |    2 |
-- |      8209 |    2 |
-- |      9369 |    2 |
-- |      9378 |    2 |
-- |      9379 |    2 |
-- |      9465 |    2 |
-- |      9910 |    2 |
-- |     10326 |    2 |
-- |     11163 |    2 |
-- |     22891 |    2 |
-- |     27113 |    2 |
-- |     27433 |    2 |
-- |     51082 |    2 |
-- |     51207 |    2 |
-- |     81488 |    2 |
-- |     83871 |    2 |
-- |    158055 |    2 |
-- |    163590 |    2 |
-- |    220074 |    2 |
-- |    414060 |    2 |
-- |    445815 |    2 |
-- | 100996758 |    2 |
-- +-----------+------+
