#%%
"""
qpcr_utils.py
=============

Some miscellaneous helper utilities and variables used by the QPCR code.
"""

import yaml
from easydict import EasyDict
import numpy as np
from openpyxl.utils import get_column_letter
from openpyxl.utils import units
import re
import pandas as pd

OUTLIER_COL = "__outlier_values"

MAIN_SHEET = "Main"
SINGLE_CAL_SHEET = "Cal"
CAL_SHEET_FMT = "Cal-{gene}-{plateID}"

# These two (commented-out) formulas are alternatives to the above that accomplish the same thing but
# tests outliers also (outliers are enclosed in square brackets). Normally we do not want to test the outliers
# because they're excluded from the calculations.
# QAQC_DEFAULT_VALIDATES_FORMULA = "AND(ISNUMBER({col='Value'}{row}), OR({col='Value'}{row}>={col='Lower Limit'}{row}, {col='Lower Limit'}{row}=\"\"), OR({col='Value'}{row}<={col='Upper Limit'}{row}, {col='Upper Limit'}{row}=\"\"))"
# QAQC_VALUE_FORMULA = '=IF({cell_ref}="", "", IF(ISNUMBER({cell_ref}), {cell_ref}, VALUE(SUBSTITUTE(SUBSTITUTE({cell_ref},"[",""),"]",""))))'

INDEX_KEY = "_index_"
REPLICATE_NUM = "#"

MAIN_ROW_DATA = "main_row_data"
CAL_ROW_DATA = "cal_row_data"
MAIN_COL_BL_CT = "main_col_bl_ct"
MAIN_COL_CT_AVG = "main_col_ct_avg"
MAIN_COL_CT = "main_col_ct"

# Regex for searching for tags, eg {value_0:0.3f|BLANK|MISSING}. BLANK is an optional alternate text to show if the value exists but is empty (ie. value_0="" or None)
# MISSING is alternate text to use if the value doesn't exist (ie. value_0 doesn't exit)
# $1 = "value_0"
# $2 = ":0.3f"
# $3 = "|BLANK"
# $4 = "|MISSING"
PARSE_VALUES_REGEX = "\{(%s)(:?[^\s|]*)(\|?[^\}\|]*)(\|?[^\}]*)\}"
PARSE_VALUES_REGEX_ANYKEY = re.compile(PARSE_VALUES_REGEX % "[0-9A-Za-z_\.]*", flags=re.IGNORECASE)

class QPCRError(Exception):
    pass

def load_config(config_files):
    """Load a series of configuration YAML (or JSON) files, merging each subsequent configuration with the previous one.

    Parameters
    ----------
    config_files : str | list[str]
        A single (str) or multiple (list[str]) list of YAML files to load. The config files are loaded in order, with each
        subsequent config dictionary updating what has been loaded so far (by setting whichever keys are set).

    Returns
    -------
    The merged configuration dictionary.
    """
    def _update(dictA, dictB):
        for k, v in dictB.items():
            if k in dictA and isinstance(v, dict):
                _update(dictA.get(k, {}), v)
            else:
                dictA[k] = v

    if isinstance(config_files, str):
        config_files = [config_files]
    
    if config_files and len(config_files) > 0:
        config = {}
        for file in config_files:
            with open(file, "r") as f:
                _update(config, yaml.safe_load(f))
        config = EasyDict(config)
    else:
        config = None
    
    return config


def add_sheet_name_to_colrow_name(sheet_name, colrow_name):
    """Add the sheet name to the column or row name. This is to qualify the column/row name with the sheet name. Internally we
    store all column/row names this way.
    """
    if sheet_name is None or colrow_name is None:
        return colrow_name
    return f"{sheet_name}-{colrow_name}"

def add_sheet_name_to_colrow_names(sheet_name, col_names, row_names):
    """Add the sheet name to multiple column and row names.
    """
    col_names = [[add_sheet_name_to_colrow_name(sheet_name, c) for c in c_arr] for c_arr in col_names] if col_names is not None else col_names
    row_names = [[add_sheet_name_to_colrow_name(sheet_name, r) for r in r_arr] for r_arr in row_names] if row_names is not None else row_names
    return col_names, row_names

def get_template_colrow_names(template_ws, sheet_name=None):
    """Get all the column names and row names from the specified template. The row names are found in column A, and the column names in row 1.
    If sheet_name is specified then we add the sheet name to all the found names.
    """
    col_names = [c.value for c in template_ws["1"]][1:]
    col_names = [c.strip().lower().split(",") if c else [None] for c in col_names]
    col_names = [[n2.strip() if n2 else None for n2 in n] for n in col_names]
    row_names = [r.value for r in template_ws["A"]][1:]
    row_names = [r.strip().lower().split(",") if r else [None] for r in row_names]
    row_names = [[n2.strip() if n2 else None for n2 in n] for n in row_names]
    if sheet_name:
        return add_sheet_name_to_colrow_names(sheet_name, col_names, row_names)
    return col_names, row_names


def flatten(arr):
    """Flatten the passed in array. This works for ragged arrays. Using Numpy's flatten does not work for
    ragged arrays (ie. arrays where subarrays might be different sizes, such as [[1], [2,3]])

    Parameters
    ----------
    arr : list | tuple | np.ndarray | scalar
        Array or item to flatten. If not a list/tuple/np.ndarray then [arr] is returned.
    
    Returns
    -------
    list : list
        The flattened list of arr.
    """
    res = []
    if isinstance(arr, (list, tuple, np.ndarray)):
        for subarr in arr:
            flat = flatten(subarr)
            res = res + flat
        return res
    res = [arr]
    return res

def parse_colrow_tags(s, columns_source, cur_row):
    """
    """
    all_matches = set(re.findall("{([^}]*)}", s))

    if isinstance(columns_source, (list, tuple, np.ndarray)):
        columns = columns_source
    else:
        columns = list(columns_source.columns) if isinstance(columns_source, pd.DataFrame) else [c.value for c in columns_source["1"]]
    columns = [c.lower() if c is not None else None for c in columns]

    # Replace all {col='Col Name';col_sheet='Sheet Name'} elements in the formula, to Excel column IDs (eg. AX, B)
    for match in all_matches:
        # @TODO: Make this work better, eg. If a semicolon is in a quote, it should not be split.
        components = [x.strip() for x in match.split(';')]
        components = [[x.strip() if idx > 0 else x.strip().lower() for idx, x in enumerate(args.split('=', 1))] for args in components]

        # args = [x.strip() if idx > 0 else x.strip().lower() for idx, x in enumerate(match.split('='))]
        vals = {}
        for args in components:
            vals[args[0]] = strip_quotes(args[1]) if len(args) == 2 else None

        if "col" in vals:
            col_name = vals["col"]
            col_sheet = vals["col_sheet"] if "col_sheet" in vals else None
            cur_col_id = get_column_letter(columns.index(col_name.lower())+1)
            s = s.replace("{" + match + "}", cur_col_id)
        elif "row" in vals:
            s = s.replace("{" + match + "}", str(cur_row))

    return s

def sheet_and_addr(addr):
    """Split an Excel address into its sheet name component and cell address component. eg. 'Main'!A5 is split as ['Main', 'A5']
    """
    sheet_split = addr.split("!")
    addr = sheet_split[1] if len(sheet_split) > 1 else addr
    sheet = sheet_split[0].strip("\"'") if len(sheet_split) > 1 else ""
    return sheet, addr

def strip_quotes(s):
    """Remove the first set of quotes surrounding a string, either single or double quotes.
    """
    s = s.strip()
    new_s = re.sub(f"^\'(.*)\'$", r"\1", s)
    if new_s == s:
        new_s = re.sub(f"^\"(.*)\"$", r"\1", s)
    return new_s

def points_to_cm(pts):
    """Unit conversion for Excel sizes.
    """
    return units.EMU_to_cm(units.pixels_to_EMU(units.points_to_pixels(pts)))

def estimated_chars_to_cm(chars):
    """Unit conversion for Excel sizes.
    """
    return chars*0.21

def estimated_cm_to_chars(cm):
    """Unit conversion for Excel sizes.
    """
    return cm/estimated_chars_to_cm(1)

def rename_columns(df, *column_names):
    """
    """
    new_column_names = [str(c).strip() for c in df.columns]
    lower_column_names = [re.sub("\s", "", c.lower()) for c in new_column_names]

    for cur_column_names in column_names:
        if not isinstance(cur_column_names, (list, tuple, np.ndarray)):
            cur_column_names = [cur_column_names]

        for column_name in cur_column_names:
            lower_column_name = re.sub("\s", "", column_name.strip().lower())
            if lower_column_name in lower_column_names:
                new_column_names[lower_column_names.index(lower_column_name)] = column_name

    df.columns = new_column_names

def excel_addr_to_fixed(addr, fixed_col, fixed_row):
    """Convert an Excel address (eg. A3) to have a fixed row and/or column (eg. $A$3)

    Parameters
    ----------
    addr : str
        The Excel address to convert to fixed format.
    fixed_col : bool
        If True then convert the column to fixed format.
    fixed_row : bool
        If True then convert the row to fixed format.

    Returns
    -------
    str
        The addr converted to fixed format (eg. $A$3).
    """
    sheet, addr = sheet_and_addr(addr)
    if fixed_col:
        addr = re.sub("([A-Za-z]+)", r"$\1", addr)
    if fixed_row:
        addr = re.sub("([0-9]+)", r"$\1", addr)
    if sheet:
        addr = "'{}'!{}".format(sheet, addr)
        
    return addr

def sheet_to_df(sheet):
    """Create a Pandas pd.DataFrame from an OpenPyXL Worksheet.
    """
    data = sheet.values
    columns = next(data)[0:]
    df = pd.DataFrame(data, columns=columns)
    return df

def parse_values(v, **kwargs):
    """Parse all tags in the string v (case insensitive). These are the tags enclosed in curly braces (eg. "value_covn1_0")

    If v contains tags in curly braces that are not in kwargs, then they are left unchanged in v.

    Tags also have an alternate alt_text, which is specified by separating the tag name with |. If the
    tag name is not found in kwargs, instead of keeping it unchanged we instead replace it with the alt_text.
    For example, "{myTag|<MISSING>}" would be replaced with the string "<MISSING>" if the tag myTag has no key in
    kwargs.

    Parameters
    ----------
    v : str | any
        The string to parse. If it is not a string then it is returned unchanged.
    kwargs : dict
        Dictionary of values for all the recognized tags. The keys are the tags (without curly braces). The values
        are either the literal value or a dictionary. If a dictionary, it contains "value" which is the value,
        "data" which is the pd.DataFrame data in WWMeasure associated with the value, and "re_match" which is a compiled
        regular expression that finds the tag. See populate_format_args and add_array_values.

    Returns
    -------
    v : str | any
        The string v, with all tags matched and replaced. If the input v is not a string then it is returned unchanged.
    matching_data : list
        All the "data" members in kwargs that were associated with tags found in v that were parsed. See kwargs.
    """
    if not isinstance(v, str):
        return v, []

    if INDEX_KEY in kwargs:
        v = v.replace(REPLICATE_NUM, kwargs[INDEX_KEY])

    # Parse all tags in curly braces, the tag names are the keys in kwargs. They can have formatting 
    # options (passed to str.format). We scan the string v in reverse order, parsing the latest tags first since
    # it's easier for embedded tags. If a tag doesn't exist in kwargs, then we keep it in the string (with curly
    # braces) since we might want to parse those some other time in the future.
    closing_brackets = []

    format_args = { k.lower() : v["value"] if isinstance(v, (dict, EasyDict)) else v for k, v in kwargs.items() }
    data_args = { k.lower() : v for k, v in kwargs.items() if isinstance(v, (dict, EasyDict))}
    matching_data = []

    for idx in range(len(v))[::-1]:
        if v[idx] == "}":
            closing_brackets.append(idx)
        if v[idx] == "{":
            if len(closing_brackets) == 0:
                raise ValueError("ERROR: Missing bracket '}'")
            matching_close = closing_brackets.pop()
            sub_str = v[idx:matching_close+1]

            replace = sub_str
            try:
                # See if any tags that have associated data are present. We add the associated data to the matching_data
                # list.
                for data_key, data_vals in data_args.items():
                    regex = data_vals.get("re_match", None)
                    if regex is None:
                        regex = re.compile(PARSE_VALUES_REGEX % data_key, flags=re.IGNORECASE)
                    if re.match(regex, sub_str):
                        matching_data.extend(data_vals["data"])

                # sub_str is the substring of v starting at our current index idx up to the end of the string.
                match = re.match(PARSE_VALUES_REGEX_ANYKEY, sub_str)
                if match is not None:
                    # We found a string in curly braces!
                    # The format is {key:fmt|blank|missing}, where {key:fmt} is passed to the string's
                    # format call, blank is used if the key exists but is blank, and missing is used if
                    # the key doesn't exist. If missing is not specified and key does not exist then
                    # we keep the full tag in the string unmodified.
                    key = match[1].lower()
                    fmt = match[2]
                    blank_text = match[3]
                    missing_text = match[4]                                        
                    sub_str = "{%s%s}" % (key, fmt)
                    if key in format_args.keys():
                        if len(blank_text) > 0 and (pd.isna(format_args[key]) or str(format_args[key]) == ""):
                            replace = blank_text[1:]
                        else:
                            replace = sub_str.format(**format_args)
                    elif len(missing_text) > 0:
                        replace = missing_text[1:]
            except Exception as e:
                print("EXCEPTION:", e)
                pass

            v = "{}{}{}".format(v[:idx], replace, v[matching_close+1:])

    if len(closing_brackets) > 0:
        raise ValueError("ERROR: Unmatched '{'")

    return v, matching_data

def cleanup_file_name(file_name):
    # file_name = re.sub(r"[:=+\*\\/&]", "-", file_name)
    file_name = re.sub(r"[^A-Za-z0-9\.\-\(\)\[\] {}\<\>_]", "-", file_name)
    return file_name
