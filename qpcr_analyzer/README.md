# QPCR Analyzer

This folder contains all the main QPCR Analyzer code.

Order of execution will typically be the following:

1. **qpcr_extracter.py**: Extract data from BioRad PDFs or Excel files (QPCRExtracter). See [qpcr_extracter.md](qpcr_extracter.md) for details.
2. **biorad_mapper.py**: Map the extracted data to ODM format (BioRadMapper).
3. **qpcr_populator.py**: Populate our output files (QPCRPopulator). See [qpcr_populator.md](qpcr_populator.md) for details.

In addition to the above, there are several other options that can be performed. To see a full implementation on a Lambda Function, see [lambda_container](../lambda_container/).

## Local Fixes and Changes

There are a few changes that must be made to OpenPYXL and the Python Ghostscript packages. These changes should eventually be moved to the OpenPYXL and Ghostscript repos or to a fork of the repos.

In order to apply the fixes, edit [localfixes.sh](localfixes.sh), change the `ROOT` variable to your local Python site-packages folder (where your Python packages are stored), then run:

    ./localfixes.sh

This is a crude temporary fix/change. While the [localfixes.sh](localfixes.sh) script applies the changes locally and must be run manually, in the [lambda_container](../lambda_container/) this is accomplished automatically with multiple `RUN` commands already in the [Dockerfile](../lambda_container/source/Dockerfile).

The changes applied are described below.

### Local Fixes/Changes: OpenPYXL

1. The `datetime` package throws an exception when parsing invalid dates. OpenPYXL should properly handle these exceptions, but the type of exception `datetime` throws is different in different Python versions. OpenPYXL has an `except ValueError:` clause to catch the exception. In order to allow catching the correct exception, the clause must be changed to `except:` to ensure catching of all exceptions occurs.
1. To add support for saving both formulas and evaluated values of the formulas to Excel files, OpenPYXL requires a few changes. The first is to add `calculated_value` to the `__slots__` of the classes `Cell` and `MergedCell` (in openpyxl/cell/cell.py). The second is to save the `calculated_value` to disk (in openpyx/cell/_writer.py) by adding the value to the `v` sub-element of the cell's `c` element in the XLSX file.
1. The `QPCRPopulator` attaches Pandas DataFrame rows from the WWMeasure table to cells of the Excel file. This allows the populator to access the data that was used to populate each cell. In order to allow this, the `attached_data` variable is added to the `__slots__` of the classes `Cell` and `MergedCell` (in openpyxl/cell/cell.py).

### Local Fixes: Ghostscript

1. The `ghostscript` package does not properly encode string parameters passed to the Ghostscript API (in ghostscript/_gsprint.py). This is only a problem in certain versions of Python (Python 3.8.10). The parameters must be properly encoded by calling each parameter's encode("UTF-8") members.

## Notes on BioRad Software Output

The BioRad software that outputs the QPCR quantification data can save in both PDF and XLSX formats. There are a few important points to make about these outputs:

1. The QPCRExtracter, which reads the BioRad output, is much faster at reading Excel files compared to PDF files. For improved performance you should feed in the BioRad Excel files instead of the PDF files.

1. The PDF output has only two decimal places for all Ct values, whereas the XLSX output has 13. This will result in slight differences in the QPCR reports generated depending on which files you input into the QPCR Analyzer.

1. The XLSX files are not exactly in the standard XLSX format. BioRad saves the Excel files (which are ZIP files but with an XLSX extension) with an internal structure that has backslashes for paths (instead of the standard forward slashes), and also has different capitalization of certain file names (eg. "shared**s**trings.xml" instead of "shared**S**trings.xml"). This makes it so OpenPYXL (and Pandas, which uses OpenPYXL) can't properly load the files. To fix this problem, we use the `fix_xlsx_file` function in [fix_xlsx.py](fix_xlsx.py).
