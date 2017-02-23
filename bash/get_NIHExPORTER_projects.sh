#!/bin/bash

baseurl="http://exporter.nih.gov/CSVs/final/"

rm -f project_urls.txt

ten = 10
for x in `seq 34 38`; do
    if (("$x" -lt "$ten"))
    then
	file="RePORTER_PRJ_C_FY2015_00$x.zip"
    else
	file="RePORTER_PRJ_C_FY2015_0$x.zip"
    fi
    url=$abs_baseurl$file
    #echo "Getting URL $url..."
    echo "$url" >> project_urls.txt
done

wget -bct 0 -i _urls.txt
echo "Downloading project files as wget background process, check latest wget-log file."

