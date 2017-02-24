#!/bin/bash

baseurl="http://exporter.nih.gov/CSVs/final/"

rm -f project_urls.txt

for yr in `seq 2000 2015`; do
    file="RePORTER_PRJ_C_FY$yr.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> project_urls.txt
done

for x in `seq 1 9`; do
    file="RePORTER_PRJ_C_FY2016_00$x.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> project_urls.txt
done
for x in `seq 10 52`; do
    file="RePORTER_PRJ_C_FY2016_0$x.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> project_urls.txt
done

wget -bct 0 -i project_urls.txt
echo "Downloading project files as wget background process, check latest wget-log file."

