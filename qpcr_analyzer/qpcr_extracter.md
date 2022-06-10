# qpcr_extracter.py

The QPCRExtracter class receives input files (either in PDF or XLSX format) from a QPCR machine, extracts the data quantification table, and saves the results in an Excel file ready for the QPCRPopulator.

More details will be made available here shortly.

## Usage

    extracter = QPCRExtracter(config,       # Main Extracter config file
        format_configs)                     # Array of configs that specify the input file layout

    # merged_extracted_file is the main output to be sent to QPCRPopulator.
    # extracted_files are the individual extracted files, one for each of input_files (will be None at indices
    #   where the input_file could not be extracted).
    # raw_files are the raw versions of the input_files in Excel format. These are the unmodified extracted tables before
    #   any further processing is performed (ie. before the extracted_files are created).
    merged_extracted_file, extracted_files, raw_files = extracter.extract(input_files, output_dir, raw_dir)

