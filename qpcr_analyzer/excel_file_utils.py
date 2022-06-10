#%%
"""
# excel_file_utils.py

A few Excel utility functions, meant to deal with various problems associated with some XLS and XLSX files.

## fix_xlsx_file

Fixes an XLSX file so that all its internal files follow the correct naming conventions.

This is specific to BioRad QPCR output Excel files. BioRad saves the Excel files (which are ZIP files but with an XLSX extension)
with an internal structure that has backslashes for paths (instead of forward slashes), and also has different capitalization of
certain file names. This makes it so openpyxl can't properly load the files (eg. openpyxl expects a file called "sharedStrings.xml"
but the BioRad software names it with all lowercase as "sharedstrings.xml"). fix_xlsx_file will recreate the XLSX file in place but
with proper file names and paths. If the XLSX file is already in the correct format then it is left unchanged.

### Usage

    if fix_xlsx_file("/path/to/file.xlsx"):
        print("Excel file has been fixed and resaved!")
    else:
        print("Excel file is already good, no changes required!")

## xls_to_xlsx

Converts an XLS file to an XLSX file. Special handling is performed for some invalid XLS files.  Some XLS files, such as from 
QIAquant machines, have a missing biff version, causing an error when loading the XLS file with pd.read_excel. This function 
ensures that this error is ignored.

### Usage

    new_file = xls_to_xlsx("/path/to/file.xls")
    if new_file:
        print("XLS file resaved to", new_file)
    else:
        print("Nothing performed on XLS file, either due to incorrect extension or an error")
        
"""

from zipfile import ZipFile
import re
import tempfile
import os
import random

import sys
import xlrd
from xlrd.biffh import XL_WORKBOOK_GLOBALS
import pandas as pd
from uuid import uuid4

# Used by _fix_xlsx_file_name to fix an XLSX internal file name. We execute re.sub(match, replace, filename)
# for each array element below (in order) on all filenames in an Excel file.
_EXCEL_INTERNAL_FILES_NAME_MAPPERS = [
    {
        "match" : "\\\\",
        "replace" : "/",
    },
    {
        "match" : "\\[content_types\\]",
        "replace" : "[Content_Types]",
    },
    {
        "match" : "sharedstrings\.xml",
        "replace" : "sharedStrings.xml"
    },
    {
        "match" : "calcchain\.xml",
        "replace" : "calcChain.xml"
    },
]

def _fix_xlsx_file_name(filename):
    """Fixes a filename (a path) in an Excel file using all the regex commands in _EXCEL_INTERNAL_FILES_NAME_MAPPERS.
    """
    for mapper in _EXCEL_INTERNAL_FILES_NAME_MAPPERS:
        filename = re.sub(mapper["match"], mapper["replace"], filename)
    return filename

def _fix_xlsx_file_names(zip):
    """Fixes all file names in the specified Excel file archive. zip is a ZipFile. Returns True if fixes had to be made, False if everything is good
    and so no changes performed.
    """
    has_changed = False
    for f in zip.filelist:
        newname = _fix_xlsx_file_name(f.filename)
        has_changed = has_changed or f.filename != newname
        f.filename = newname
    return has_changed

def fix_xlsx_file(path, tempdir=None):
    """Fix the internal file system for the specified Excel file if required. If it is already good then nothing is changed or saved.
    The file is modified and saved back to the same filename.

    Args:
        path (str): The Excel file to fix.
        tempdir (str, optional): The temporary directory to use for fixing the file. We will save the fixed version here, then move it over to overwrite
            the broken version at path. If None then the default temporary directory is used. Defaults to None.

    Returns:
        bool: True of the Excel file had to be fixed (ie. a new file at path was created). False if the file did not have to be
            fixed (or the file doesn't exist) and therefore nothing has changed.
    """
    if not os.path.isfile(path):
        return False
    
    with ZipFile(path, "r") as inzip:
        if _fix_xlsx_file_names(inzip):
            # An internal filename has changed, so we need to recreate the XLSX (zip) file
            print(f"Fixing Excel file {path}")
            tempdir = tempdir if tempdir is not None else tempfile.gettempdir()
            if tempdir:
                os.makedirs(tempdir, exist_ok=True)

            # Loop until we can open a new output ZIP file that doesn't yet exist, with a different
            # name for each loop
            def _get_new_basename():
                return "{}{}".format(int(random.random()*100000), basename)
            basename = os.path.basename(path)
            basename = _get_new_basename()
            while True:
                try:
                    temp_path = os.path.join(tempdir, basename)
                    outzip = ZipFile(temp_path, "x")
                    break
                except FileExistsError as e:
                    basename = _get_new_basename()

            # Copy all the files to the new zip file
            for info in inzip.infolist():
                with inzip.open(info) as file:
                    outzip.writestr(info.filename, file.read())
            outzip.close()

            # Delete the old zip file and copy over the new one
            os.remove(path)
            os.rename(temp_path, path)

            return True
    
    return False


def xls_to_xlsx(input_file, output_file=None):
    """Convert an XLS file to an XLSX file.
    
    Special handling is performed for some invalid XLS files. Some XLS files, such as from QIAquant output, have a 
    missing biff version, causing an error when loading the XLS file with pd.read_excel. This
    function ensures that this error is ignored.

    Args:
        input_file (str): Full path with filename of the XLS file to load. If the extension is
            not XLS then nothing is done.
        output_file (str, optional): The full path and filename to save the converted file to. If
            the extension is not .xlsx then .xlsx is added. If None then we output to input_file but with
            an .xlsx extension. If output_file was generated internally due to not having an XLSX extension
            or due to being None then the file name generated is guaranteed to not have previously
            existed. Defaults to None.

    Returns:
        str: The new xlsx file created, or None if no conversion was done, either due to
            input_file not being an xls file or due to an error.
    """
    file_ext = os.path.splitext(input_file)[-1]
    if file_ext != ".xls":
        return None

    verify_not_exists = False
    if not output_file:
        output_file = f"{os.path.splitext(input_file)[0]}.xlsx"
        verify_not_exists = True
    if os.path.splitext(output_file)[-1] != ".xlsx":
        output_file = f"{os.path.splitext(output_file)[0]}.xlsx"
        verify_not_exists = True
        
    # If we made our own output_file name (eg. the caller passed in output_file=None or
    # the passed in output_file did not have an xls extension) then make sure the name we choose
    # does not exist.
    if verify_not_exists:
        rename_idx = 0
        output_file_base = os.path.splitext(output_file)[0]
        while os.path.exists(output_file) and rename_idx < 9999:
            output_file = f"{output_file_base}-{rename_idx:04n}.xlsx"
            rename_idx += 1
        rename_idx = 0
        while os.path.exists(output_file) and rename_idx < 99:
            output_file = f"{output_file_base}-{uuid4()}.xlsx"
            rename_idx += 1

    df = None
        
    try:
        # Try a regular load first, if it fails we'll try a specialized custom load
        df = pd.read_excel(input_file, engine="xlrd", header=None)
    except:
        # print("Exception with default load")
        pass
    
    if df is None:
        try:
            # Based on xlrd.book.open_workbook_xls, but without any exceptions for a missing biff_version    
            bk = xlrd.Book()
            bk.biff2_8_load(
                filename=input_file, file_contents=None,
                logfile=sys.stdout, verbosity=0, use_mmap=True,
                encoding_override="iso-8859-1",
                formatting_info=False,
                on_demand=False,
                ragged_rows=False,
                ignore_workbook_corruption=False
            )
            biff_version = bk.getbof(XL_WORKBOOK_GLOBALS)
            bk.biff_version = biff_version
            if biff_version <= 40:
                bk.fake_globals_get_sheet()
            elif biff_version == 45:
                bk.parse_globals()
            else:
                bk.parse_globals()
                bk._sheet_list = [None for sh in bk._sheet_names]
                bk.get_sheets()
            bk.nsheets = len(bk._sheet_list)
            
            # Convert the data to a Pandas DataFrame
            sh = bk.sheet_by_index(0)
            all_rows = []
            for row in range(sh.nrows):
                vals = sh.row_values(row)
                all_rows.append(vals)                
            df = pd.DataFrame.from_records(all_rows)
        except:
            # print("Exception with custom load")
            pass

    if df is not None:
        # Save the DataFrame as an xlsx file
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        df.to_excel(output_file, index=False, header=False)
        return output_file
            
    return None
