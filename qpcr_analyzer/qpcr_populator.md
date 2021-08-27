# qpcr_populator.py

The QPCRPopulator class receives ODM data and creates an output report, along with full QA/QC. It generates the output based on an Excel file that acts as a template.

## Usage

    qpcr = QPCRPopulator(input_file=mapped_file,    # mapped_file is the XLSX output of BioRadMapper (ie. in ODM format)
        template_file=populator_template,           # eg. qpcr_template_ottawa.xlsx
        target_file=output_file, 
        overwrite=True, 
        config_file=populator_config,               # eg. qpcr_populator_ottawa.yaml
        qaqc_config_file=qaqc_config,               # eg. qaqc_ottawa.yaml
        sites_config=sites_config,                  # eg. sites.yaml
        sites_file=sites_file,                      # eg. sites.xlsx
        hide_qaqc=False)
    output_files = qpcr.populate()

## Flow

The following is the flow of code through the main steps for the QPCRPopulator.populate() function:

1. Prepare the WWMeasure Pandas DataFrames: Split by site if required, do further splits by analysis date, add `standardCurveID`s to each Ct sample, to identify which standard curve that sample uses.
1. For each analysis date:
    1. `qaqc.remove_all_outliers()`: For all outliers detected, will set the Ct value to None, and set the new column `qpcr_utils.OUTLIER_COL` to the original Ct value
    1. `create_main()`
        1. Further organize the data
        1. Call `copy_rows()` for the banners in the template file (identified by `main_row_banner`)
        1. For each of our main genes:
            1. Call `copy_rows()` for the headers in the template file (identified by "main_row_header")
            1. Call `copy_rows()` for each sample ID in our data (template rows identified by `main_row_data`)
    1. `create_calibration()`
        1. Organize the same data we passed to create_main
        1. Call `copy_rows()` for the banners in the template file (identified by `cal_row_banner`)
        1. For each of our main genes:
            1. Call `copy_rows()` for the headers in the template file (identified by `cal_row_header`)
            1. Call `copy_rows()` for each SQ value in our data (template rows identified by `cal_row_data`). SQ values are the copies/well for each standard.
    1. For any late binding custom functions, call those functions to finalize parsing of the template.
    1. Run QAQC on the current analysis group, using the cell values calculated by `create_main()` and `create_calibration()`.
    1. Calculate all values of all formulas and save to disk.

## Note On Calculated Values of Formulas

OpenPYXL (and Pandas, which uses OpenPYXL) does not evaluate Excel functions. When saving to disk with Pandas and OpenPYXL, only the formulas are saved. Other downstream users that read our output can therefore only read the formulas, but cannot access the actual values that the formulas evaluate to.

To fix this problem, QPCRPopulator calculates all formula values and saves both those values and the formulas to the output Excel files. Evaluation is performed by the Pycel package, and a modified version of OpenPYXL is used to add custom support for saving the values along with the formulas.

To get an idea of how this is done, see [excel_calculator.py](excel_calculator.py).

## Template Tags

Tags can be placed in any cell of the template file and are replaced by the parser. For example, {value_covn1_0} will be replaced by the Ct value for the covN1 gene for the sample ID associated with the current row. Tags are case-insensitive.

A full list of tags are shown below.

- **{value_n}**: The Ct value for replicate `n` (0-based) for the current row's sample (eg. {value_0}).
- **{value_gene_n}**: The Ct value for replicate `n` (0-based) for the current row's sample, for gene `gene` (eg. {value_covn1_0})
- **{value_emptytubemass_n}**: Empty tube mass for replicate `n` (0-based) for the current row's sample. (eg. {value_emptytubemass_0})
- **{value_tottubemass_n}**: Total tube mass (tube+sample) for replicate `n` (0-based) for the current row's sample. (eg. {value_tottubemass_0})
- **{value_extmass_n}**: Extracted mass for replicate `n` (0-based) for the current row's sample. (eg. {value_extmass_0})
- **{value_setsol_n}**: Settled solids mass for replicate `n` (0-based) for the current row's sample. (eg. {value_setsol_0})
- **{value_totvol_n}**: Total volume for replicate `n` (0-based) for the current row's sample. (eg. {value_totvol_0})
- **{value_sq_n}**: Starting quantity value for replicate `n` (0-based) for the current row's sample. (eg. {value_sq_0}). The SQ value is used to define the starting quantity (copies/well) of a standard sample.

If a number sign (#) is found in a cell, it is replaced by the current data row number. For example, "avg_std_#" will be replaced with "avg_std_3", if we are currently on data #3 (0-based) in the output.

Whenever a tag is encountered, the Pandas row in the WWMeasure table that is associated with that tag is added to the cell's attached_data array data member (attached_data is defined in OpenPYXL's \__slots__ for classes `Cell` and `MergedCell`. This is a custom slot added specifically by the QPCR Populator). Using the custom function \__GETDATA (described in the [Custom Functions](#Custom_Functions) section) we can then retrieve any column from that row.

## Custom Functions

There are custom Python functions that can be called during parsing of the template. The custom functions, placed within the template file, all start with two underscores (\__). Once called, the custom function is replaced by the return value.

It is important to note the binding number of all the custom functions, defined by the CUSTOM_FUNCS global variable in qpcr_populator.py. Custom functions that are called immediately on the first pass by the parser have a bind number of 0. Custom functions with a positive bind number are then called once parsing has done its first pass and the output Excel file has been fully laid out. Functions with a lower bind number are called first (eg. 1 is called, then 2, then 3, etc.) Finally custom functions with a negative bind number are called last, with lower absolute values being called first (ie. -1 is called, then -2, then -3, etc). This ensures that custom functions that provide data that can then be used by other custom functions are called early on. eg. __SETCELL("Cal-{type}-{plateID}", "intercept", 1) tags the current cell in the sheet "Cal-{type}-{plateID}" with the name "intercept". This then allows __GETCELL("Cal-{type}-{plateID}", "intercept", FALSE), which has a later binding number, to get the address from the previous __SETCELL call.

#### __GETRANGE

#### __SETCELL

#### __QUOTIFY

#### __GETDATA

#### __ADDROWID

#### __GETCELL

#### __MERGETO

#### __AVERAGE

#### __MOVINGAVERAGE

#### __GETCALVAL

#### __QAQCHASFAILEDCATEGORY

### Adding Custom Functions

New custom functions should be placed in the appropriate section of [qpcr_populator.py](qpcr_populator.py). The meta data for the function (the bind number, the tag for the function, as well as the Python function called when the parser encounters the tag) are defined by the global variable `CUSTOM_FUNCS`.

Any number of parameters can be used for a custom function. These parameters are passed in as strings, so should be cast appropriately (pay particular attention to booleans, these can be cast with the function self.cast_bool to properly handle strings such as "True", "False", "T", ...).

The custom function call in the Excel spreadsheet is replaced by the return value of the custom function. If an exception is raised, then the entire cell contents is replaced by the exception's error message.

In addition to the user-defined parameters to the custom function, the following named parameters are also added to the function call (which can be collapsed into **kwargs):

- **template_cell**: The template cell that the target cell is based on.
- **target_cell**: The target cell that we are copying the template cell to.
- **target_sheet_name**: The sheet name that we are copying the template cell to. This is the `sheet_name` member in the `worksheets_info` object.

## Row and Column Names

The template file also includes names attached to the columns and rows of the template. These names can be used to reference those rows/columns. Custom rows/columns can be used, but there is a small set of predefined names listed below:

@TODO: Finish