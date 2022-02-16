#%%
# %load_ext autoreload
# %autoreload 2
"""
qpcr_extracter.py
=================

Extracts data from BioRad output and puts it in a format for the BioRadMapper to map to the ODM.

Usage
-----

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

"""

from easydict import EasyDict
import pandas as pd
import numpy as np
import yaml
import argparse
import copy
import re
from datetime import datetime
import time
from collections import OrderedDict
import camelot
from functools import partial
import cloud_utils
import os
import tempfile
import warnings
import json
from qpcr_sites import QPCRSites

from fix_xlsx import fix_xlsx_file
from qpcr_utils import (
    QPCRError,
    rename_columns, 
)

# WELLID_REGEX = r"^([A-Za-z]*)([0-9]*)$"

class QPCRExtracter(object):
    # row_name = "__row__"
    # col_name = "__col__"

    def __init__(self, input_files, output_file, output_dir, samples_file, config_file, sites_file=None, sites_config=None, upload_to=None, overwrite=False, save_raw=False):
        with open(config_file, "r") as f:
            self.config = EasyDict(yaml.safe_load(f))

        self.saved_raw_file = None
        self.save_raw = save_raw
        self.overwrite = overwrite
        self.run_date = datetime.now()
        self.output_file = output_file
        self.upload_to = upload_to
        self.cached_sheets = {}
        self.input_files = [input_files] if isinstance(input_files, str) else input_files
        self.input_file_index = -1
        self.current_input_file = None
        self.current_output_file = None
        self.output_dir = output_dir
        self.samples_file = samples_file
        self.downloaded_samples_file = None

        self.sites = None
        if sites_config:
            self.sites = QPCRSites(sites_config, sites_file)

        if not cloud_utils.is_s3(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

        self.config = self.make_arrays(self.config, ["remove_empty_col", "well_type_std", "well_type_unk", "well_type_ntc"])

        # The samples file contains additional details about the samples, such as the sample date, QPCR date,
        # extracted mass, total volume, etc. For each well (row) we will add this data.
        self.download_samples_file()

    def download_samples_file(self):
        """Load the samples file, which contains sample dates, qpcr dates, sample extracted mass, sample volumes, etc.

        If a local cached version is available then load that instead, unless the samples_file_cache_ttl (set in the
        config file) has expired.
        """
        if self.samples_file:
            if cloud_utils.is_local(self.samples_file):
                print(f"Loading local samples file at {self.samples_file}")
                self.downloaded_samples_file = None
            else:
                # Download the samples file or use a local cached version if the TTL hasn't expired
                base_name = self.samples_file
                base_name = re.sub("[^\w\s-]", "_", base_name)
                base_name = re.sub("[-\s]+", "-", base_name)
                base_name = f"samples_file.{base_name}.xlsx"
                self.downloaded_samples_file = self.make_temp_dir_filename(base_name)
                samples_ttl = self.config.samples_excel.get("samples_file_cache_ttl", None)
                if not os.path.exists(self.downloaded_samples_file) or samples_ttl is None or time.time() - os.path.getmtime(self.downloaded_samples_file) >= samples_ttl:
                    self.downloaded_samples_file = cloud_utils.download_file(self.samples_file, self.downloaded_samples_file)
                else:
                    print(f"Using cached samples file at {self.downloaded_samples_file}")                    

            samples_file = self.downloaded_samples_file or self.samples_file

            try:
                # Load the samples file
                xl = pd.ExcelFile(samples_file)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.samples_df = xl.parse(xl.sheet_names[0])
                    self.samples_df.columns = [c.strip() for c in self.samples_df.columns]
            except Exception as e:
                file_name = os.path.basename(samples_file)
                raise QPCRError(f"Could not load samples data file '{file_name}' with the following error: {e}")

            rename_columns(self.samples_df, self.config.samples_excel.sample_location_col, self.config.samples_excel.sample_date_col, self.config.samples_excel.copy_samples_cols, self.config.samples_excel.order_sizes_cols)

            # There an error in the samples file where Total Weight and Empty Tube Weight have been
            # reversed, fix it by making the Total Weight always the larger of the two
            if "order_sizes_cols" in self.config.samples_excel and len(self.config.samples_excel.order_sizes_cols) > 1:
                # Order from smallest to largest
                def _reorder(row):
                    row = pd.to_numeric(row, errors="coerce")
                    prev_index = row.index.copy()
                    row = row.sort_values()
                    row.index = prev_index
                    return row
                self.samples_df[self.config.samples_excel.order_sizes_cols] = self.samples_df[self.config.samples_excel.order_sizes_cols].apply(_reorder, axis=1)
        else:
            self.samples_df = None

    def load_cached_sheets(self, file_name):
        """Load all the sheets from an Excel file, save them as Pandas DataFrames in our internal cache of sheets 
        (self.cached_sheets dictionary, where the keys are the sheet names and values are the DataFrames).

        Will we replace any previously loaded cached sheets.
        """
        self.cached_sheets = {}
        if os.path.exists(file_name):
            loaded_xl = pd.ExcelFile(file_name)
            for sheet_name in loaded_xl.sheet_names:
                self.cached_sheets[sheet_name] = loaded_xl.parse(sheet_name)

    def append_to_cached_sheets(self, new_sheets):
        """Append a dictionary of Pandas DataFrames to our internal list of cached sheets (self.cached_sheets). The dictionary
        keys are the sheet names and values are the DataFrames.
        """
        for sheet_name, df in new_sheets.items():
            if sheet_name in self.cached_sheets:
                df_blank = pd.DataFrame({c:[None] for c in df.columns})
                df = pd.concat([self.cached_sheets[sheet_name], df_blank, df])
            self.cached_sheets[sheet_name] = df

    def advance_and_prepare_input_file(self):
        """Advance to the next input file. Extract the table if it's a PDF, or clean up the file if it's an Excel file.
        """
        self.saved_raw_file = None

        if self.input_file_index >= len(self.input_files) - 1:
            return False

        self.input_file_index += 1
        self.current_input_file = cloud_utils.download_file(self.input_files[self.input_file_index])
        self.current_plate_id = re.sub("[^\w]", "_", os.path.basename(self.current_input_file))
        self.current_output_file = self.rename_to_output_dir(self.output_file or (self.current_input_file + "-results.xlsx"))
        file_name = os.path.basename(self.current_input_file)
        ext = os.path.splitext(file_name.lower())[1]        
        if ext == ".pdf":
            # Extract from the PDF
            self.saved_raw_file = self.make_temp_dir_filename(f"{self.current_input_file}.xlsx")
            # try:
            self.full_df = self.convert_to_excel(self.current_input_file, self.saved_raw_file)
            # except Exception as e:
            #     file_name = os.path.basename(self.current_input_file)
            #     raise QPCRError(f"Could not extract table from PDF input file: {file_name}")
        elif ext == ".xlsx":
            try:
                print(f"Opening {self.current_input_file}")
                self.saved_raw_file = self.current_input_file

                # Fix the Excel file and load it. See fix_xlsx_file for details of what fixing does and why it's needed.
                fix_xlsx_file(self.current_input_file)
                xl = pd.ExcelFile(self.current_input_file)
                sheet_name = self.config.data_sheet
                if isinstance(sheet_name, int):
                    sheet_name = xl.sheet_names[sheet_name]

                # Keep on parsing (increasing skiprows on each step) until we find the header that has
                # all the required columns
                required_columns = [c[0].strip().lower() for c in self.config.extract_pdf_columns if c[1]]
                skiprows = 0
                while True:
                    self.full_df = xl.parse(sheet_name, keep_default_na=False, skiprows=skiprows)
                    cur_columns = [(str(c) or "").strip().lower() for c in self.full_df.columns]
                    missing_columns = [c for c in required_columns if c not in cur_columns]
                    if len(missing_columns) == 0:
                        break
                    if len(self.full_df.index) == 0:
                        raise QPCRError(f"Could not find required headers in input file: {file_name}")
                    skiprows += 1
                
                # Drop everything after (and including) the fist blank row
                for idx, row in self.full_df.iterrows():
                    non_empties = [c for c in row if c is not None and c != ""]
                    if len(non_empties) == 0:
                        self.full_df = self.full_df.drop(self.full_df.index[idx:], axis=0)
            except Exception as e:
                file_name = os.path.basename(self.current_input_file)
                raise QPCRError(f"Could not extract table from Excel input file: {file_name}")
        else:
            file_name = os.path.basename(self.current_input_file)
            raise QPCRError(f"Unrecognized file type for input file: {file_name}")

        # Create missing optional columns
        optional_columns = [c[0] for c in self.config.extract_pdf_columns if not c[1]]
        missing_optional_columns = [c for c in optional_columns if c not in self.full_df.columns]
        if len(missing_optional_columns) > 0:
            self.full_df[missing_optional_columns] = None

        # Extract requested columns in correct order
        # all_columns = self.get_column_names(self.full_df, [c[0] for c in self.config.extract_pdf_columns])
        all_columns = [c[0] for c in self.config.extract_pdf_columns]
        try:
            self.full_df = self.full_df[all_columns]
        except Exception as e:
            input_name = os.path.basename(self.current_input_file)
            raise QPCRError(json.dumps([f"Input file '{input_name}' must have all the following columns:", all_columns]))

        return True

    def make_arrays(self, d, keys):
        """Convert the values of the keys in the dictionary d to arrays. If they are not an array (eg. a string, integer, etc), then we simply
        place the value in an array of size 1.
        """
        d = copy.deepcopy(d)
        if isinstance(keys, str):
            keys = [keys]
        for key in keys:
            if key not in d:
                continue
            val = d[key]
            if not isinstance(val, (list, tuple)):
                val = [val]
            d[key] = val
        return EasyDict(d)

    def make_sample_ids(self, sample_id_col, sample_date_col, row):
        """Make the sample ID for a single row.

        @TODO This function is specific to the uOttawa lab, and should be made more general or controlled through a config file.

        Parameters
        ----------
        sample_id_col : str
            The column where the original sample ID is stored. We will use this to construct a valid sample ID.
        sample_date_col : str
            The column where the sample date is stored.
        row : pd.Series
            A row containing sample_id_col and sample_date_col. It can be a row from either the extracted DataFrame or the samples file.
        
        Returns
        -------
        sample_id : str
            The final sample ID to use
        match_sample_id : str
            A sample ID, very similar to sample_id, that should be used to match values between the extracted DataFrame and the samples file.
            This sample ID is typically sample_id but with a few components removed.
        """
        sample_id = str(row[sample_id_col]).strip().lower()
        orig = sample_id

        # Remove any trailing _r (or _r#). These are reruns (ie. samples that were previously run, but had to be rerun due to some error)
        # We'll re-add the _r# at the end.
        rerun = re.search("_r[0-9]*$", sample_id)
        if rerun:
            sample_id = sample_id[:-len(rerun[0])]

        # All numbers should be preceded by a dot, rather than an underscore
        sample_id = re.sub("_(?=[0-9])", ".", sample_id)
        
        #  Replace spaces and dashes with dots
        sample_id = re.sub("[ -]", ".", sample_id)

        # Replace text months to integers
        for month_num, months in enumerate(self.config.months_mapper):
            # Sort by month length, to match longer month first (eg. "April" will match with "April" to get 04,
            # instead of with "Apr" to get "04il")
            months.sort(key=len, reverse=True)
            for month in months:
                sample_id = re.sub(month, f"{month_num+1}.", sample_id, flags=re.IGNORECASE)
        sample_id = re.sub("\.\.", ".", sample_id)

        # Number groups are preceded by a dot and trailed by a dot or end of string
        # Add leading 0 to number groups that are 1 character long
        sample_id = re.sub("(?<=\.)([0-9])(?=\.|$)", "0\\1", sample_id)
        # Reduce length of number groups down to last 2 digits if longer than 2 digits
        sample_id = re.sub("(?<=\.)([0-9]*([0-9][0-9]))(?=\.|$)", "\\2", sample_id)

        # All letter groups should be preceded by an underscore (except for PS).
        sample_id = re.sub("\.(?=[A-Za-z])", "_", sample_id)
        sample_id = re.sub("_ps", ".ps", sample_id)

        # Last numbers should be mm.dd.yy
        comps = sample_id.split(".")
        num_trailing_digit_groups = 0
        for comp in comps[::-1]:
            try:
                _ = int(comp)   # Will throw exception if comp isn't a string integer
                num_trailing_digit_groups += 1
            except:
                break

        if num_trailing_digit_groups == 2:
            # Add the default year since only the month and day are available in the sample ID
            default_year = str(self.config.default_year)[-2:]
            sample_id = f"{sample_id}.{default_year}"
        elif num_trailing_digit_groups < 2 and sample_date_col is not None:
            # There aren't enough trailing digits to form a sample date, so extract the sample date from sample_date_col
            try:
                date = pd.to_datetime(row[sample_date_col]) or ""
                if isinstance(date, pd.Timestamp):
                    date = date.strftime("%m.%d.%y")
                else:
                    date = str(date)
            except:
                date = ""
            if len(date) > 0:
                sample_id = f"{sample_id}.{date}"

        match_sample_id = sample_id

        # Site ID is the first match. Sometimes an extra number is added at the end of the site ID
        # and so can't be found in the samples file. For those items, try removing the numbers
        # (one at a time) at the end and see if that will match a site ID, and use it if it does.
        comps = sample_id.split(".")
        if num_trailing_digit_groups < len(comps) and self.sites is not None: #self.sites_df is not None:
            siteid = comps[0]
            siteid_and_number = self.sites.split_off_siteid_number(siteid)
            sample_id = ".".join([*siteid_and_number, *comps[1:]])
            match_sample_id = ".".join([siteid_and_number[0], *comps[1:]])
        else:
            if self.sites is not None:
                comps[0] = self.sites.get_siteid(comps[0]) or comps[0]
            match_sample_id = ".".join(comps)

        # Readd _r rerun
        match_sample_id = re.sub("\.ps", "", match_sample_id)
        if rerun:
            sample_id = f"{sample_id}{rerun[0]}"
            match_sample_id = f"{match_sample_id}{rerun[0]}"

        return sample_id, match_sample_id

    def join_samples_data(self):
        """Join the sample data (from the samples file) with the main extracted DataFrame.
        """
        if self.samples_df is None:
            return

        try:
            match_col = "_____match"
            samples_sample_id_col = "_____sampleid"

            # Map all sample Ids to common names. The columns will initially be [sample_id, match_sample_id]. sample_id is the cleaned ID while match_sample_id is the
            # sample ID used for pairing rows in full_df with matching rows in samples_df.
            self.full_df[self.config.cleaned_sample_id_col] = self.full_df[[self.config.sample_id_col]].agg(partial(self.make_sample_ids, self.config.sample_id_col, self.config.sample_date_col), axis=1)
            self.samples_df[samples_sample_id_col] = self.samples_df.agg(partial(self.make_sample_ids, self.config.samples_excel.sample_location_col, self.config.samples_excel.sample_date_col), axis=1) #[[samples_sample_id_col, sample_date_col]].agg(partial(self.make_sample_id_from_samples_file, samples_sample_id_col, sample_date_col), axis=1)

            self.full_df[match_col] = self.full_df[self.config.cleaned_sample_id_col].map(lambda x: x[1])
            self.full_df[self.config.cleaned_sample_id_col] = self.full_df[self.config.cleaned_sample_id_col].map(lambda x: x[0])

            self.samples_df[match_col]  = self.samples_df[samples_sample_id_col].map(lambda x: x[1])
            self.samples_df[samples_sample_id_col]  = self.samples_df[samples_sample_id_col].map(lambda x: x[0])

            self.samples_df = self.samples_df.drop_duplicates(subset=match_col, keep="first")

            # Do any additional replacements of the sample IDs used for pairing between full_df and samples_df
            if "full_df" in self.config.samples_excel.join_samples_id_pairing:
                for info in self.config.samples_excel.join_samples_id_pairing.full_df:
                    self.full_df[match_col] = self.full_df[match_col].apply(lambda x: re.sub(info.pattern, info.replace, x))
            if "samples_df" in self.config.samples_excel.join_samples_id_pairing:
                for info in self.config.samples_excel.join_samples_id_pairing.samples_df:
                    self.samples_df[match_col] = self.samples_df[match_col].apply(lambda x: re.sub(info.pattern, info.replace, x))
            
            self.full_df = self.full_df.join(self.samples_df[[samples_sample_id_col, match_col] + self.config.samples_excel.copy_samples_cols].set_index(match_col), on=match_col)

            del self.full_df[match_col]
            del self.full_df[samples_sample_id_col]
            del self.samples_df[match_col]
            del self.samples_df[samples_sample_id_col]

            # Add analysis date if missing (using the first set analysis date for the plate)
            missing_dates = self.full_df[self.config.source_analysis_date_col].isna()
            if (~missing_dates.sum()).sum() == 0:
                date = None
            else:
                other_dates = self.full_df.loc[~missing_dates, self.config.source_analysis_date_col]
                if len(other_dates.index) == 0:
                    date = None
                else:
                    date = other_dates.iloc[0]
            self.full_df.loc[missing_dates, self.config.source_analysis_date_col] = date
        except Exception as e:
            cols = self.config.samples_excel.copy_samples_cols
            file_name = os.path.basename(self.samples_file)
            raise QPCRError(json.dumps([f"Samples datasheet '{file_name}' is not in the correct format. Please ensure that the following columns are available:", cols]))
    
    def add_sites(self):
        """Add all the site information for each of the rows in the main extracted DataFrame (full_df).

        Site info has the site ID, site title, region, aliases, parentid, etc.
        """
        if self.sites is None:
            return
        self.full_df[self.sites.get_siteid_column()] = self.full_df[self.config.cleaned_sample_id_col].map(self.sites.get_sample_siteid)
        self.full_df[self.sites.get_site_title_column()] = self.full_df[self.config.cleaned_sample_id_col].map(self.sites.get_sample_site_title)
        self.full_df[self.sites.get_siteid_aliases_column()] = self.full_df[self.config.cleaned_sample_id_col].map(self.sites.get_sample_siteid_aliases)
        self.full_df[self.sites.get_parentid_column()] = self.full_df[self.config.cleaned_sample_id_col].map(self.sites.get_sample_parentid)
        self.full_df[self.sites.get_parent_title_column()] = self.full_df[self.config.cleaned_sample_id_col].map(self.sites.get_sample_parent_title)
        self.full_df[self.sites.get_sample_type_column()] = self.full_df[self.config.cleaned_sample_id_col].map(self.sites.get_sample_sample_type)

    def apply_defaults(self):
        # Apply any defaults in the config file
        if "defaults" in self.config:
            def _cast_as(dtype, default_value, value):
                dtype = dtype.lower()
                try:
                    if dtype == "int":
                        value = int(value)
                    elif dtype == "float":
                        if pd.isna(value):
                            value = default_value
                        else:
                            value = float(value)
                except:
                    value = None
                return default_value if value is None else value

            for conf in self.config.defaults:
                # for column in conf.columns:
                filt = self.full_df[self.config.well_type_col].isin(conf.well_types)
                self.full_df.loc[filt, conf.columns] = self.full_df.loc[filt, conf.columns].applymap(partial(_cast_as, conf.dtype, conf.default_value))

    def apply_value_mappers(self):
        """Perform any additional processing by running the value_mappers in the config file. eg. samples named "EB" will
        receive "EB" in the "Content" column.
        """
        if "value_mappers" in self.config:
            for value_mapper in self.config.value_mappers:
                filt = self.full_df[value_mapper.match_column].str.contains(value_mapper.match_expression)
                self.full_df.loc[filt, value_mapper.target_column] = value_mapper.target_value

    def assign_missing_sample_ids(self, collection, format="__sample{:03}__"):
        for group_num,g in enumerate(collection):
            df = self.rowcols_to_df([g])[0]
            if len(df[self.config.sample_id_col].index) > 0 and df[self.config.sample_id_col].iloc[0] == "":
                gene = df[self.config.target_col].iloc[0].strip().lower()
                group_filt = self.full_df[self.config.well_id_col].isin(df[self.config.well_id_col])
                self.full_df.loc[group_filt, self.config.sample_id_col] = format.format(gene=gene, group_num=group_num)

    def extract(self):
        """Run a full extraction on the input files passed to the constructor.
        """
        output_files = []
        input_files = []
        upload_files = []
        raw_files = []
        while self.advance_and_prepare_input_file():
            print("Extracting from:", self.current_input_file)
            print("Plate ID:", self.current_plate_id)

            if self.saved_raw_file:
                raw_files.append(self.saved_raw_file)

            if self.current_input_file:
                input_files.append(self.current_input_file)
            
            if self.output_file:
                # Same output file for each input file. Only load on first input file if not overwriting (appending)
                load_existing = self.input_file_index == 0 and not self.overwrite
            else:
                # Different output file for each input file
                load_existing = not self.overwrite
            if load_existing:
                self.load_cached_sheets(self.current_output_file)
            
            # Remove rows with empty column
            if "remove_empty_col" in self.config:
                cols = self.config.remove_empty_col
                if isinstance(cols, str):
                    cols = [cols]
                cols = [c for c in cols if c in self.full_df.columns]
                self.full_df = self.full_df.dropna(subset=cols)

            self.full_df[self.config.well_id_col] = self.full_df[self.config.well_id_col].apply(lambda x: str(x).upper())

            def _valid_float(val):
                """Check if a value can be cast to a float by Pandas. Note that None can
                be cast (to nan). Strings can't be cast unless it is in the format of a float.
                """
                try:
                    _ = pd.to_numeric(val)
                    return True
                except:
                    return False

            # Remove any Ct value that's not a number, and cast the remaining values to a float
            keep_filt = self.full_df[self.config.ct_col].map(_valid_float)
            self.full_df = self.full_df[keep_filt]
            self.full_df[self.config.ct_col] = pd.to_numeric(self.full_df[self.config.ct_col])

            # Do general string mappings based on config.string_mapper
            for cur_map in self.config.string_mapper:
                columns = cur_map.columns
                if isinstance(columns, str):
                    columns = [columns]
                self.full_df[columns] = self.full_df[columns].applymap(lambda x: re.sub(cur_map.match, cur_map.replace, x, flags=re.IGNORECASE if cur_map.get("ignore_case", False) else 0))
            
            standards_filt = self.full_df[self.config.well_type_col].isin(self.config.well_type_std)
            unknowns_filt = self.full_df[self.config.well_type_col].isin(self.config.well_type_unk)
            ntc_filt = self.full_df[self.config.well_type_col].isin(self.config.well_type_ntc)

            # standards_df = self.full_df[standards_filt]
            # unknowns_df = self.full_df[unknowns_filt]
            # ntc_df = self.full_df[ntc_filt]

            std_ids = "_std_" + self.full_df.loc[standards_filt, self.config.sample_id_col].astype(str) + self.full_df.loc[standards_filt, self.config.sq_col].astype(str) + "_" + self.full_df.loc[standards_filt, self.config.target_col].astype(str).str.lower() + "_"
            self.full_df.loc[standards_filt, self.config.sample_id_col] = std_ids

            # For standards: People will often incorrectly assign the SQ (starting quantity/copies per well) values (either they forget or they
            # accidentally assign the same SQ value to multiple groups). Make sure we group the SQ values appropriately.
            # @TODO: We should remove this. Do some tests first to make sure it's no longer needed
            # for std_gene, std_df in self.full_df.loc[standards_filt].groupby(self.config.target_col): #, self.config.target_col].unique():
            #     # std_gene_df = 
            #     for sample_id in list(std_df[self.config.sample_id_col].unique()):
            #         current = std_df.loc[self.full_df[self.config.sample_id_col] == sample_id]
            #         num = len(current.index)
            #         if num >= self.config.preferred_std_replicates*2:
            #             std_ids.loc[current.index] = ""
            # self.full_df.loc[standards_filt, self.config.sample_id_col] = std_ids

            self.full_df.loc[standards_filt, self.config.sample_id_col] = self.current_plate_id + "_" + self.full_df.loc[standards_filt, self.config.sample_id_col]
            # self.full_df[self.config.ct_col] = self.full_df[self.config.ct_col].fillna("")
            self.assign_instrument()
            self.full_df[self.config.index_col] = None
            self.assign_std_copies()
            self.full_df[self.config.cleaned_sample_id_col] = None
            # self.full_df[self.config.sample_date_col] = None
            self.join_samples_data()
            # self.add_sample_date()
            self.assign_index_numbers()
            self.full_df[self.config.plate_id_col] = self.current_plate_id
            self.add_sites()

            self.apply_defaults()
            self.apply_value_mappers()

            # Remove any unknowns without sample data
            remove_if_no_sample_data = self.config.samples_excel.get("remove_if_no_sample_data", None)
            if remove_if_no_sample_data:
                remove_filt = self.full_df[remove_if_no_sample_data].isna() & self.full_df[self.config.well_type_col].isin(self.config.well_type_unk)
                self.full_df = self.full_df[~remove_filt]

            output_sheets = OrderedDict({
                "Results" : self.full_df,
            })
            
            self.append_to_cached_sheets(output_sheets)

            if self.output_file:
                # Saving all extractions to a single file, so only save once we've finished extracting
                # the last file.
                if self.input_file_index == len(self.input_files) - 1:
                    output_file, upload_file = self.save_df(self.cached_sheets, self.current_output_file, upload=True)
                    output_files.append(output_file)
                    if upload_file:
                        upload_files.append(upload_file)
            else:
                # Saving to individual output files for each extracted file, so save on each iteration
                output_file, upload_file = self.save_df(self.cached_sheets, self.current_output_file, upload=True)
                self.cached_sheets = {}
                output_files.append(output_file)
                if upload_file:
                    upload_files.append(upload_file)
        
        return input_files, output_files, raw_files, upload_files

    def make_temp_dir_filename(self, path):
        """Make a file path/name in the temporary directory, based on an input path name.
        """
        return os.path.join(tempfile.gettempdir(), os.path.basename(path))
        # return os.path.join("temp", os.path.basename(path))

    def rename_to_output_dir(self, path):
        """Make a file path/name in the output directory, based on an input path name.
        """
        return os.path.join(self.output_dir, os.path.basename(path))

    def assign_index_numbers(self):
        """Assing the values in the "index" column. These are in the form "plateID-#".
        """
        for (sample_id, gene, well_type), sample_group in self.full_df.groupby([self.config.sample_id_col, self.config.target_col, self.config.well_type_col]):
            # sample_group = self.sort_ct_values(sample_group, gene, well_type)
            index_numbers = { idx:f"{self.current_plate_id}-" + (f"{exist_idx}-" if exist_idx is not None else "") + f"{rep:03d}" for rep,(idx, exist_idx) in enumerate(zip(sample_group.index, self.full_df.loc[sample_group.index][self.config.index_col]))}
            # index_numbers = { idx:rep for rep,(idx, exist_idx) in enumerate(zip(sample_group.index, self.full_df.loc[sample_group.index][self.config.index_col]))}
            self.full_df.loc[sample_group.index, self.config.index_col] = pd.Series(index_numbers)

    def assign_std_copies(self):
        """Assign the values in the "std_copies_col": The copies/well for the standards.
        """
        self.full_df[self.config.std_copies_col] = None
        std_filt = self.full_df[self.config.well_type_col].isin(self.config.well_type_std)

        if self.config.get("std_copies_per_well", None) is None:
            # If std_copies_per_well is not defined in config file then we do nothing and assume the user has properly
            # entered the copies/well in the "Starting Quantity (SQ)" column
            self.full_df.loc[std_filt, self.config.std_copies_col] = self.full_df.loc[std_filt, self.config.sq_col]
        else:
            # Go through all genes
            for gene_name in self.full_df[self.config.target_col].unique():
                cur_filt = std_filt & (self.full_df[self.config.target_col] == gene_name)
                std_items = self.full_df.loc[cur_filt].sort_values(self.config.sq_col, ascending=False)

                # Get the configured copies per well
                if gene_name in self.config.std_copies_per_well:
                    copies_per_well = self.config.std_copies_per_well[gene_name]
                elif "_default" in self.config.std_copies_per_well:
                    copies_per_well = self.config.std_copies_per_well["_default"]
                else:
                    # Copies/well for gene_name and "_default" not specified in config file, so use what is found
                    # in the sq_col (ie. assume the user has entered it correctly)
                    copies_per_well = np.array(std_items[self.config.sq_col].unique())
                    copies_per_well.sort()
                    copies_per_well = copies_per_well[::-1]
                
                # Go through the sample IDs in order, assign the copies per well in order
                for idx, sample_id in enumerate(std_items[self.config.sample_id_col].unique()):
                    std_copies = None if idx >= len(copies_per_well) else copies_per_well[idx]
                    sample_filt = self.full_df[self.config.sample_id_col] == sample_id
                    self.full_df.loc[cur_filt & sample_filt, self.config.std_copies_col] = std_copies
            
    def assign_instrument(self):
        """Assign the instrument name in the instrument_col column.
        """
        self.full_df[self.config.instrument_col] = "BioRad"

    def save_df(self, dfs, file_name, upload=False):
        """Save all the DataFrames in dfs to separate sheets in the same Excel file.

        Parameters
        ----------
        dfs : dict[sheet:df]
            A dictionary of DataFrame sheets. The key is the sheet name and the value is the DataFrame.
        file_name : str
            The Excel file name to save to.
        upload : bool
            If True, then upload the saved Excel File to the upload_to path.
        """
        print(f"Saving to '{file_name}'...")
        dirname = os.path.dirname(file_name)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with pd.ExcelWriter(file_name) as writer:
            # df = df.drop([self.col_name, self.row_name], axis=1)
            for sheet_name, df in dfs.items():
                # drop_columns = [self.col_name, self.row_name]
                # drop_columns = [c for c in drop_columns if c in df.columns]
                # if len(drop_columns) > 0:
                #     df = df.drop(drop_columns, axis=1)
                df.to_excel(writer, sheet_name=sheet_name, freeze_panes=(1, 0), index=False)

        upload_file = None
        if upload and self.upload_to:
            print(f"Uploading extracted file to {self.upload_to}")
            upload_path = os.path.join(self.upload_to, os.path.basename(file_name))
            upload_file = upload_path
            cloud_utils.upload_file(file_name, upload_path)

        return file_name, upload_file

    def format_cell(self, c):
        """Format a cell value (c) in the extracted file. We replace new lines with spaces and try to cast strings to a float.
        If we can't cast to a float then we keep the value unchanged.
        """
        if not isinstance(c, str):
            return c

        c = c.replace("\n", " ")

        try:
            v = float(c)
            c = c if v is None else v
        except:
            pass
            
        return c

    def convert_to_excel(self, input_file, output_file):
        """Convert a BioRad PDF input_file to an Excel file (output_file), by extracting the "Quantification Data" table.
        """
        print(f"Reading PDF {input_file}...")
        tables = camelot.read_pdf(input_file,
            pages="all", 
            split_text=True,
            multiple_tables=True)
        check_columns = [self.config.sample_id_col, self.config.ct_col, self.config.target_col, self.config.well_id_col]
        df = None
        print("Extracting tables from PDF...")
        for table in tables:
            columns = [c.replace("\n", " ").strip() for c in table.df.loc[0].tolist()]
            check = np.sum([c in columns for c in check_columns])
            if check != len(check_columns):
                continue

            cur_df = table.df
            cur_df.columns = columns
            cur_df = cur_df.drop(0, axis=0)
            cur_df[cur_df == "N/A"] = None
            cur_df = cur_df.applymap(self.format_cell)

            if df is None:
                df = cur_df.copy()
            else:
                df = pd.concat([df, cur_df], ignore_index=True)

        if output_file and self.save_raw:
            print(f"Saving raw extraction to {output_file}")
            sheets = {str(self.config.data_sheet) : df}
            self.save_df(sheets, output_file, upload=False)

        return df

if __name__ == "__main__":
    if "get_ipython" in globals():
        opts = EasyDict({
            "input_files" : [
                # June 30
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-30_N1_N2_O__CSC_NFN_H_UO_13 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-30_N2_O__CSC_NFN_H_UO_13 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-30_PEPPER_O_CSC_NFN_H_UO_12 SAMPLES_KB.pltd.pdf",

                # Bad for June 28
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-28_N1_N2_O_G_Liz  Samples_Xin.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-28_Pepper_O_G_Liz  Samples_Xin.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-28_PEPPER_O_KB.pltd.pdf",

                # Good for June 28
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-28_N1_N2_O_VC_6 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-28_PEPPER_O_VC_6 SAMPLES_KB.pltd.pdf",

                # June 29
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-29_N1_N2_O_H_CSC_VC_11 samples.Xin.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-06-29_Pepper_O_H_CSC_VC_11 samples.Xin.pltd.pdf",                

                # July 28
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-june/qPCR-2021-07-28_N1_O_CSC_H_UO_VC_BLK_21 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-june/qPCR-2021-07-28_N2_O_CSC_H_UO_VC_BLK_21 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-june/qPCR-2021-07-28_PEPPER_O_CSC_H_UO_VC_BLK_21 SAMPLES_KB.pltd.pdf",

                # May 25
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-05-25_N1_O_H_G_CASS_VC_15 samples.Xin.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-05-25_N2_O_H_G_CASS_VC_15 samples.Xin.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad/qPCR-2021-05-25_PEPPER_O_H_VC_GAT_CASS 15 SAMPLES.pltd.pdf",

                # BioRad error
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-error/qPCR-2021-07-26_N1_N2_O_VC_7 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-error/qPCR-2021-07-26_N1_N2_PEPPER_O_VC_7 SAMPLES_KB.pltd.pdf",

                # July 30
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/july30/qPCR-2021-07-30_PEPPER_O_NFG_UO_11 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/july30/qPCR-2021-07-30_N1_N2_O_NFG_UO_11 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/july30/qPCR-2021-07-30_ALPHA_DELTA VARIANT_KB.pltd.pdf",

                # July 23
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/july23/qPCR-2021-07-23_N2_O_Redos_CSC_ AC_H_UO_BLK_16 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/july23/qPCR-2021-07-23_PEPPER_O_Redos_CSC_ AC_H_UO_16 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/july23/qPCR-2021-07-23_PEPPER_O_Redos_CSC_ AC_H_UO_BLK_16 SAMPLES_KB.pltd.pdf",

                # Aug 23
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug23/qPCR-2021-08-20_N1_N2_PEPPER_O_02 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug23/qPCR-2021-08-23_N1_N2_PEPPER_O_02 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug23/qPCR-2021-08-23_PEPPER_O_F_VC_H_09 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug23/qPCR-2021-08-23.pdf",

                # Aug 19
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug19/qPCR-2021-08-19_PEPPER_O_CSC_H_VC_GAT_13 SAMPLES_KB.pltd.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug19/qPCR-2021-08-19_N1_O_CSC_H_VC_GAT_13 SAMPLES_KB.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug19/qPCR-2021-08-19_N2_O_CSC_H_VC_GAT_13 SAMPLES_KB.pltd.xlsx",                

                # Sep 10
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep10/qPCR-2021-09-10 N1 O 09.09 H 09.07 HD 09.08-09.09 AC 09.08 uO 09.09 4A 28 12A 28 20A 28 ST.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep10/qPCR-2021-09-10 N2 O 09.09 H 09.07 HD 09.07-09 AC 09.08 uO 09.08-09.10  4A 28 12A 28 20A 28.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep10/qPCR-2021-09-10 Pep O H AC uO 4A C C 28.pdf",

                # Sep 7-10
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-07 N1 N2 Ottwa rerun.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qpCR-2021-09-07 Pep O 09.03-09.06 VC 09.02 09.05 ST.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-08 N1 O 09.08 H09.02-04 AC09.03-09.07 AW09.07 uO 09.07-09.08 ST.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-08 N2 O H AC Aw uO.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-08 Pep O H H_D AC Aw uO ST.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-08 Pep uO.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-09 N1 N2 Pep O 09.08 VC 09.07.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-09 Pep O VC 09.08.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-10 N1 O 09.09 H 09.07 HD 09.08-09.09 AC 09.08 uO 09.09 4A 28 12A 28 20A 28 ST.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-10 N2 O 09.09 H 09.07 HD 09.07-09 AC 09.08 uO 09.08-09.10  4A 28 12A 28 20A 28.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-10 Pep O H AC uO 4A C C 28.pdf",

                # Sep 9
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-09 N1 N2 Pep O 09.08 VC 09.07.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep07-10/qPCR-2021-09-09 Pep O VC 09.08.pdf",

                # Aug 9
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug09/qPCR-2021-08-10 PMMoV VC Aug 9 Aw Aug 9.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug09/qPCR-2021-08-10 PMMoV O Aug 9 H Aug 5 7 8 CSC Aug 6 AC Aug 5 6 VC1 Aug 9 S.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug09/qPCR-2021-08-10 N2 O Aug 9 H Aug 5 6 7 Ac Aug  5 6 Aw Aug 5 VC Aug 9 S.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug09/qPCR-2021-08-10 N1 O Aug 9 H Aug 5 7 8 CSC Aug 9 Ac Aug 5 6 VC Aug 9 Aw Aug 9 EVR S.pdf",

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/error/qPCR-2021-08-26_N1_UO_14 SAMPLES_WT.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/error/qPCR-2021-08-26_N2_UO_14 SAMPLES_WT.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/error/qPCR-2021-08-26_PEPPER_UO_1-7 SAMPLES_WT.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/error/qPCR-2021-08-26_PEPPER_UO_7-14 SAMPLES_WT.pltd.pdf",

                # BioRad new test
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-newtest/qPCR-2021-07-30_N1_N2_O_NFG_UO_11 SAMPLES_KB.pltd.pdf",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-newtest/qPCR-2021-07-30_PEPPER_O_NFG_UO_11 SAMPLES_KB.pltd.pdf",

                # Tyson D3
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/Tyson/2021-05-06_B117 VARIANT_9 SAMPLES.pltd.pdf",

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/aug19/qPCR-2021-08-19_N1_O_CSC_H_VC_GAT_13 SAMPLES_KB.xlsx",

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep28/qPCR-2021-09-28 N1 O 09.27 H 09.23 AC 09.23-09.24 Vc 1 2 09.27 IL 1 2 09.27 repeat_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep28/qPCR-2021-09-28 N1 O 09.27 H 09.23-09.26 AC 09.23-09.24 VC 09.27 Split 09.27_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep28/qPCR-2021-09-28 N2 O 09.27 H 09.23-09.26 AC 09.23-09.24 VC 09.27 IL 09.27_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep28/qPCR-2021-09-28 pep IL 1 2 09.27 -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep28/qPCR-2021-09-28 pep O 09.27 H 09.23-09.26 AC 09.23-09.24 VC 09.27_All Wells -  Quantification Cq Results.xlsx",
                
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep29/qPCR-2021-09-29 N1 O 09.28 HD 09.24-09.26 Aw 09.27 uO 09.28_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep29/qPCR-2021-09-29 N2 O 09.28 HD 09.24-09.26 Aw 09.27 UO 09.28_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/sep29/qPCR-2021-09-29 Pep O 09.28 HD 09.24-09.24 Aw 09.27 UO 09.28_All Wells -  Quantification Cq Results.xlsx",

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/nov2-error2/qPCR-2021-11-01 N1 N2 O 10.29-10.31 VC 10.28 Man vs RbQ-  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/nov2-error2/qPCR-2021-11-01 pep O 10.29-10.31 VC 10.28 ROB VS MAN_All Wells -  Quantification Cq Results.xlsx",

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/nov20-error/qPCR_2021-11-17 N1 N2 O 11.16 UO 11.16 AW 11.16Redo_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/nov20-error/qPCR-2021-11-17 Pep O 11.16 UO 11.16 Aw 11.16_All Well -  Quantification Cq Results.xlsx",        
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec1-error/qPCR-2021-11-30 N1 N1 O 11.29 H 11.25-28 VC 11.29 HD 11.26-28 REDO_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec1-error/qPCR-2021-11-30 N1 N2 redo H 11.25 VC211.29 HD 11.26-11.28  -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec1-error/qPCR-2021-11-30 PEPPER O 11.29 H 11.25-28 VC 11.29 HD 11.26-28_All Wells -  Quantification Cq Results.xlsx"

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec26-error/qPCR-2021-12-22 N1 N2 O 12.21 UO 12.21 SV 12.21R_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec26-error/qPCR-2021-12-22 N1 OMICRON O 12.21 UO 12.21 SV 12.21_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec26-error/qPCR-2021-12-22_N2_O 12.21 UO_NA 12.21 UO_FT 12.21 UO_ST 12.21  Stitt 12.21_All Wells -  Quantification Cq Results.xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/dec26-error/qPCR-2021-12-22_Pepper_O 12.21 UO_NA 12.21 UO_FT 12.21 UO_ST 12.21  Stitt 12.21_All Wells -  Quantification Cq Results.xlsx",
                
                "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/Tyson/2021-05-06_B117 VARIANT_9 SAMPLES.pltd.pdf.xlsx",
            ],

            "samples" : "<samples path here>",
            # "samples" : "/Users/martinwellman/Downloads/COVID SAMPLE LOG SHEET-2.xlsx",
            "sites_file" : "sites.xlsx",
            "sites_config" : "sites.yaml",

            "output_dir" : "/Users/martinwellman/Documents/Health/Wastewater/Code/extracted",
            "config" : "qpcr_extracter_ottawa.yaml",
            "output_file" : "merged-jan6.xlsx",
            "upload_to" : "", #"s3://odm-qpcr-analyzer/extracted/",
            "save_raw" : True,
            "overwrite" : True,
        })

        # This is just to hide the "samples" path on Github. You can enter the path here or
        # above in the opts dictionary (where it says "<samples path here>")
        with open("../../samples.yaml", "r") as f:
            samples = EasyDict(yaml.safe_load(f))
            print(f"Overriding samples argument with: {samples.samples}")
            opts["samples"] = samples.samples
    else:
        args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        args.add_argument("--input_files", nargs="+", type=str, help="Input file to analyze", required=True)
        args.add_argument("--output_dir", type=str, help="Location to save results", default="results")
        args.add_argument("--output_file", type=str, help="Optional output file name saved to output_dir. If ommitted then the output file name will be the first input file with an Excel xlsx extension added", required=False)
        args.add_argument("--upload_to", type=str, help="Optionally upload the results to this S3 bucket and folder (eg. s3://my-bucket/extracted/", required=False)
        args.add_argument("--config", type=str, help="Configuration file", default="qpcr_extracter_ottawa.yaml")
        args.add_argument("--samples", type=str, help="Excel file with samples details (eg. Total weight, extracted weight, dates)", required=False)
        args.add_argument("--sites_file", type=str, help="Excel file specifying all WW sites with information about each site.", required=False)
        args.add_argument("--sites_config", type=str, help="Config file for the sites file.", required=False)
        args.add_argument("--overwrite", help="If specified then overwrite the output file if it exists. By default we append to it.", action="store_true")
        args.add_argument("--save_raw", help="If specified then save the intermediary raw Excel files, resulting from extracting the tables from the PDF.", action="store_true")
        opts = args.parse_args()

    tic = datetime.now()
    print("Starting extracter at:", tic)
    qpcr = QPCRExtracter(opts.input_files, opts.output_file, opts.output_dir, opts.samples, opts.config, sites_file=opts.sites_file, sites_config=opts.sites_config, upload_to=opts.upload_to, overwrite=opts.overwrite, save_raw=opts.save_raw)
    input_files, output_files, raw_files, upload_files = qpcr.extract()
    print("Input files:", input_files)
    print("Output files:", output_files)
    print("Raw files:", raw_files)
    print("Uploaded files:", upload_files)
    toc = datetime.now()
    print("Started at:", tic)
    print("Ended at:", toc)
    print("Total duration:", toc - tic)

