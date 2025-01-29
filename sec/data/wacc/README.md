The steps below should be completed at the beginning of every year.

### WACC data source
link: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html

Look for "Costs of Capital by Industry (in US $)" and download the file for the given year in the "US" column.
For example, download the file at the "1/24" link and name it 2024.csv in this directory. The library accesses the "Cost of Capital" column within this file -- **ensure the values in this column are formatted as decimals (and not as percentages).**

If a new year rolls around and there is no file yet at the above link, simply duplicate the file from the previous year in this directory and name it for the current year. This is a temporary fix to ensure that we will not have an error thrown when trying to access current WACC for a company. Keep checking back to see when the new file for this year is posted, and then download it (replacing the temporary duplicate file we created).

### Ticker to industry mapping
link: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/databreakdown.html

Download the indname.xlsx spreadsheet located at the link under the "Company Lookup" section. Then, you will need to manually transform this file by going to the "US By Industry" sheet, deleting all columns except "Ticker" and "Industry Group", and then renaming these columns "ticker" and "industry" respectively. Then export this file as industries.csv and replace the one currently located in this directory.

### Verification of new files
Sometimes the industry names in the WACC files have typos or are slightly altered year over year. This will cause an error when we query the WACC file using the proper industry name that is given in industries.csv. Such errors and variations must be manually corrected so that the industry names are consistent. To do this, call `get_wacc()` on all companies in the S&P500 and note any that throw an error. Determine which industry is being queried, and find the closest one in the new year's WACC file. Then change the name of the industry in the WACC file to the one that is being queried by the failing company. Repeat this process until no errors are thrown.

### Date of last data update
2025-01-28, but 2025 data has not been posted yet so 2025.csv is a duplicate of 2024.csv