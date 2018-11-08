#!/bin/bash

MYSQL_USER='smathias'

REQUIRED_TABLES="
tinx_articlerank
tinx_disease
tinx_importance
tinx_novelty
tinx_target
pubmed
protein
target
t2tc
do
do_parent
dto
"

mysqldump \
	-u ${MYSQL_USER} \
	--no-create-db \
	--compact \
	--skip-lock-tables \
	-e \
	--add-locks \
	--no-autocommit \
	-p tcrd ${REQUIRED_TABLES} > tcrd_tinx_subset.sql


gzip tcrd_tinx_subset.sql


echo $REQUIRED_TABLES
