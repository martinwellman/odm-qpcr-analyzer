# qpcr_extracter.py

The QPCRExtracter class receives BioRad input files (either in PDF or XLSX format), extracts the data quantification table, joins the table with some additional data (such as sample extraction mass, sample date, etc.), and saves the results in an Excel file ready for the BioRadMapper to convert it to ODM format.

More details will be made available here shortly.

## Usage

    extracter = QPCRExtracter(local_input_files,    # list of BioRad PDF/Excel files
        output_file,                                # All extracted data are merged into this Excel file.
        output_dir,
        samples_file, 
        "qpcr_extracter_ottawa.yaml", 
        sites_config="sites.yaml",
        sites_file="sites.xlsx",
        upload_to=None, 
        overwrite=True,
        save_raw=True)
    local_input_files, extracted_files, raw_files, upload_files = extracter.extract()
