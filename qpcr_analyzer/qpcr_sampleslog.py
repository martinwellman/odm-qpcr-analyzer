#%%
# %load_ext autoreload
# %autoreload 2

"""
# qpcr_sampleslog.py
"""

import yaml
import cloud_utils
import pandas as pd
import warnings
import argparse
from easydict import EasyDict
import re
import os
from datetime import datetime, date
import traceback

from qpcr_sampleids import QPCRSampleIDs

from qpcr_utils import (
    QPCRError,
    rename_columns, 
)

class QPCRSamplesLog(object):
    def __init__(self, config, samples_log_file, sampleids_config, sites_config, sites_file):
        with open(config, "r") as f:
            self.config = yaml.safe_load(f)
            
        self.sampleids = QPCRSampleIDs(sampleids_config, sites_config, sites_file)
            
        self.samples_log_file = samples_log_file
        self.download_samples_file(samples_log_file)
        
    def rename_columns(self, df, columns_config):
        """Rename columns in the DataFrame based on the specified configuration.

        Args:
            df (pd.DataFrame): DataFrame to rename columns. Unrecognized columns will be deleted.
            columns_config (list[tuple[str,str]]): The renaming info. Each element is an (old_name, new_name)
                tuple. Columns who's name matches old_name are renamed to new_name. Matching to old_name also
                involves removing spaces and making the column names lower case. This helps improve the
                chances of finding a matching column.
            
        Returns:
            pd.DataFrame: The DataFrame with the changes.
        """
        orig_columns = df.columns
        cleaned_columns = [re.sub("\s", "", c.strip().lower()) for c in orig_columns]
        # Original columns as specified in the config
        cleaned_columns_config = [[re.sub("\s", "", c[0].strip().lower()), c[1]] for c in columns_config]
        new_columns = []
        unknown_columns = []
        matched_with_config = []
        
        # Go through each column, determine if we want to keep it or drop it (due to it being
        # an unknown column)
        for i, (orig_column, cleaned_column) in enumerate(zip(orig_columns, cleaned_columns)):
            m = [c[1] for c in cleaned_columns_config if cleaned_column == c[0]]
            if len(m) == 0:
                unknown_columns.append(orig_column)
            else:
                new_columns.append(m[0])
                matched_with_config.append(i)
                
        missing_columns = [c[0] for i, c in enumerate(columns_config) if i not in matched_with_config]
        if len(missing_columns) > 0:
            columns_are = "columns are" if len(missing_columns) != 1 else "column is"
            raise QPCRError(f"The following {columns_are} missing in the samples file:", missing_columns)
            
        df = df[[c for c in df.columns if c not in unknown_columns]]
        df.columns = new_columns        
        
        return df
    
    def get_sample_info(self, sample_id):
        """Get the full row for the sample from the samples log file. The row will contain
        all columns specified in the config file (eg. sampleDate, analysisDate, totalVolume, etc.)

        Args:
            sample_id (str): The sample ID to get the row for.

        Returns:
            pd.Series|None: The row in the samples log file for the specified sample ID. If multiple
                rows are found then the last one is returned.
        """
        sample_data = self.sampleslog_df[self.sampleslog_df[self.config["sample_id_col"]] == sample_id]
        if len(sample_data.index) > 0:
            return sample_data.iloc[-1]
        return None
        
    def get_sample_date(self, sample_id):
        """Get the sample date string, from the ODM samples table.
        """
        info = self.get_sample_info(sample_id)
        if info is None:
            return None
        return info[self.config["sample_date_col"]]
        
    def download_samples_file(self, samples_log_file):
        """Load the samples file, which contains sample dates, qpcr dates, sample extracted mass, sample volumes, etc.

        Args:
            samples_log_file (str): Path to the samples log file. This can be a remote file (eg. http/https, s3, gd)

        Raises:
            QPCRError: An error occurred trying to download and parse the samples file.
        """
        self.sampleslog_df = None
        try:
            samples_file = cloud_utils.download_file(samples_log_file)
            
            # Load the samples file
            xl = pd.ExcelFile(samples_file)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.sampleslog_df = xl.parse(xl.sheet_names[0])
                self.sampleslog_df.columns = [c.strip() for c in self.sampleslog_df.columns]
        except Exception as e:
            file_name_error = os.path.basename(samples_file) if samples_file else samples_log_file
            raise QPCRError(f"Could not load samples data file '{file_name_error}'")

        self.sampleslog_df = self.rename_columns(self.sampleslog_df, self.config["columns"])
        self.sampleslog_df = self.sampleids.make_all_sample_ids(self.sampleslog_df, self.config["sample_location_col"], self.config["sample_date_col"], target_sample_id_col=self.config["sample_id_col"], target_match_sample_id_col=self.config["match_sample_id_col"])
        self.sampleslog_df = self.sampleslog_df.drop_duplicates(subset=[self.config["match_sample_id_col"]])
        self.cast_columns(self.sampleslog_df)
            
    def join_and_cast(self, df, on):
        sampleslog_df = self.sampleslog_df
        keep_cols = []
        # Keep all columns in the samples log file that are not already in the target df
        for col in sampleslog_df.columns:
            if col not in df.columns or col == on:
                keep_cols.append(col)
        sampleslog_df = sampleslog_df[keep_cols]

        df = df.join(sampleslog_df.set_index(self.config["match_sample_id_col"]), on=on, how="left")
        self.cast_columns(df)
        return df
                    
    def cast_columns(self, df):
        """Cast columns to types specified in the config file (see cast_info in config file).
        """
        def _cast_number(x, default):
            try:
                x = float(x)
                if pd.isna(x):
                    x = default
            except:
                x = default
            return x
        
        def _cast_string(x, default):
            return str(x) if x else default
        
        def _cast_date(x, default):
            try:
                x = pd.to_datetime(x).date()
            except:
                try:
                    x = pd.to_datetime(default).date()
                except:
                    x = default
            if x is None:
                x = pd.NaT
            return x
        
        def _cast_datetime(x, default):
            try:
                x = pd.to_datetime(x)
            except:
                try:
                    x = pd.to_datetime(default)
                except:
                    x = default
            if x is None:
                x = pd.NaT
            return x
        
        for cast_info in self.config.get("cast_info", []):
            func = None
            cur_default = cast_info["default"]
            cur_type = cast_info["type"]
            if cur_type == "number":
                func = _cast_number
            elif cur_type == "string":
                func = _cast_string
            elif cur_type == "date":
                func = _cast_date
            elif cur_type == "datetime":
                func = _cast_datetime
            else:
                raise ValueError(f"Unrecognized defaults type in QPCRSamplesLog config file: '{cur_type}' for columns {cur_columns}")
            
            cur_columns = cast_info["columns"]
            if not isinstance(cur_columns, (list, tuple)):
                cur_columns = [cur_columns]
            
            df[cur_columns] = df[cur_columns].applymap(lambda x: func(x, cur_default))
            
if __name__ == "__main__":
    if "get_ipython" in globals():
        opts = EasyDict({
            "config" : "qpcr_sampleslog.yaml",
            "sampleids_config" : "qpcr_sampleids.yaml",
            # "samples_log_file" : "/Users/martinwellman/Documents/Health/Wastewater/Code/COVID SAMPLE LOG SHEET-2-6.xlsx",
            "samples_log_file" : "https://docs.google.com/spreadsheets/d/1apOidERKMcMbRnBfGr7W4cjY7fC63wRd/edit#gid=339812442",
            "sites_file" : "qpcr_sites.xlsx",
            "sites_config" : "qpcr_sites.yaml",
        })
    else:
        args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        args.add_argument("--config", type=str, help="Configuration file", default="qpcr_sampleslog.yaml")
        args.add_argument("--samples_log_file", type=str, help="Configuration file", default="samples_log_sheet.xlsx")
        args.add_argument("--sampleids_config", type=str, help="Config file for the sample IDs.", required=False)
        args.add_argument("--sites_file", type=str, help="Excel file specifying all WW sites with information about each site.", required=False)
        args.add_argument("--sites_config", type=str, help="Config file for the sites file.", required=False)
        
        opts = args.parse_args()

    samples = QPCRSamplesLog(opts.config, opts.samples_log_file, opts.sampleids_config, opts.sites_config, opts.sites_file)
    # print(samples.sampleslog_df)
    sample_id = "vc3.05.02.22"
    print(f"Sample date form {sample_id}:", samples.get_sample_date(sample_id))

