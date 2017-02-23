#!/bin/bash

baseurl="http://exporter.nih.gov/CSVs/final/"

rm -f abstract_urls.txt

for yr in `seq 2010 2014`; do
    file="RePORTER_PRJABS_C_FY$yr.zip"
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> abstract_urls.txt
done

ten = 10
for x in `seq 1 38`; do
    if (("$x" -lt "$ten"))
    then
	file="RePORTER_PRJABS_C_FY2015_00$x.zip"
    else
	file="RePORTER_PRJABS_C_FY2015_0$x.zip"
    fi
    url=$baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> abstract_urls.txt
done

wget -bct 0 -i abstract_urls.txt
echo "Downloading abstract files as wget background process, check latest wget-log file."
