#!/bin/bash

baseurl="http://exporter.nih.gov/CSVs/final/"

rm -f abstract_urls.txt

for yr in `seq 2000 2015`; do
    file="RePORTER_PRJABS_C_FY$yr.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> abstract_urls.txt
done

for x in `seq 1 9`; do
    file="RePORTER_PRJABS_C_FY2016_00$x.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> abstract_urls.txt
done
for x in `seq 10 52`; do
    file="RePORTER_PRJABS_C_FY2016_0$x.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> abstract_urls.txt
done

wget -bct 0 -i abstract_urls.txt
echo "Downloading abstract files as wget background process, check latest wget-log file."
