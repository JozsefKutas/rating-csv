# rating-csv

rating-csv converts XBRL files using the Record of Credit Ratings (ROCR)
taxonomy to CSV. XBRL rating history files can be downloaded from the following
locations:
- S&P: https://disclosure.spglobal.com/ratings/en/regulatory/ratingshistory
- Moody's: https://ratings.moodys.com/sec-17g-7b
- Fitch: https://www.fitchratings.com/ratings-history-disclosure

For more information, see https://www.sec.gov/structureddata/rocr-publication-guide

Download the XBRL files and run the `rating_csv.py` Python script to perform the conversion:

```shell
py .\rating_csv.py "xbrl/SP-Sovereign-2024-01-01.zip" "csv/sp_sovereign_20231231.csv" "obligor" --asof 2023-12-31
py .\rating_csv.py "xbrl/xbrl100-2023-12-15.zip" "csv/moodys_20231231.csv" "obligor" --asof 2023-12-31
py .\rating_csv.py "xbrl/ratings-history-disclosure_Fitch_Ratings-2024-01-01.zip" "csv/fitch_20231231.csv" "obligor" --asof 2023-12-31
```

Command line arguments and options:

<pre>
positional arguments:
  zip_path          The path of the ZIP archive containing the XBRL files to read.
  csv_path          The path of the CSV file to write to.
  {obligor,issuer}  The type of ratings to extract.

options:
  -h, --help        show this help message and exit
  --asof ASOF       If specified, only extract the most recent ratings as of this date. Must be in ISO 8601 format.
</pre>
