#%%
"""
fix_xlsx.py
===========

Fixes an XLSX file so that all its internal files follow the correct naming conventions.

This is specific for BioRad QPCR output Excel files. BioRad saves the Excel files (which are ZIP files but with an XLSX extension)
with an internal structure that has backslashes for paths (instead of forward slashes), and also has different capitalization of
certain file names. This makes it so openpyxl can't properly load the files (eg. openpyxl expects a file called "sharedStrings.xml"
but the BioRad software names it with all lowercase as "sharedstrings.xml"). fix_xlsx_file will recreate the XLSX file in place but
with proper file names and paths. If the XLSX file is already in the correct format then it is left unchanged.

Usage
-----

    if fix_xlsx_file("/path/to/file.xlsx"):
        print("Excel file has been fixed and resaved!")
    else:
        print("Excel file is already good, no changes required!")

"""

from zipfile import ZipFile
import re
import tempfile
import os
import random

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
    
    Parameters
    ----------
    path : str
        The Excel file to fix.
    tempdir : str
        The temporary directory to use for fixing the file. We will save the fixed version here, then move it over to overwrite
        the broken version at path. If None then the default temporary directory is used.

    Returns
    -------
    bool
        True of the Excel file had to be fixed (ie. a new file at path was created). False if the file did not have to be
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
