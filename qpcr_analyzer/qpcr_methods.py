#%%

import pandas as pd
import yaml
import argparse
from easydict import EasyDict
import re
from qpcr_utils import (
    QPCRError
)

TARGET_COLUMN = "target"
TARGET_ALIASES_COLUMN = "targetAliases"
DILUTION_FACTOR_COLUMN = "dilutionFactor"

class QPCRMethods(object):
    def __init__(self, config, methods_file): 
        with open(config, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.load_methods_file(methods_file)
        self.apply_defaults()
        
    def apply_defaults(self):
        for default_info in self.config["defaults"]:
            column = default_info["column"]
            default = default_info["default"]
            self.methods_df[column] = self.methods_df[column].fillna(default)
        
    def load_methods_file(self, methods_file):
        try:
            self.methods_df = pd.read_excel(methods_file, skiprows=1)
        except:
            raise QPCRError("Could not load methods file.")
        
        def _clean_column(c):
            return re.sub("[^A-Za-z0-9]", "", c.strip().lower())
        
        cleaned_columns = [_clean_column(c) for c in self.methods_df.columns]
        config_cleaned_columns = [_clean_column(c[0]) for c in self.config["columns"]]
        source_columns = []
        target_columns = []
        used_config_columns_indices = []
        for i, (cleaned_column, actual_column) in enumerate(zip(cleaned_columns, self.methods_df.columns)):
            if cleaned_column in config_cleaned_columns:
                column_index = config_cleaned_columns.index(cleaned_column)
                used_config_columns_indices.append(column_index)
                column_info = self.config["columns"][column_index]
                source_columns.append(actual_column)
                target_columns.append(column_info[1])
                
        missing_columns = [self.config["columns"][i][0] for i,c in enumerate(self.config["columns"]) if i not in used_config_columns_indices]
        if len(missing_columns) > 0:
            columns_are = "columns are" if len(missing_columns) != 1 else "column is"
            raise QPCRError(f"The following {columns_are} missing in the methods file:", missing_columns)
                
        self.methods_df = self.methods_df[source_columns]
        self.methods_df.columns = target_columns
        self.methods_df = self.methods_df.dropna(axis=0, how="all")
        
        self.methods_df = self.methods_df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        
    def get_row_for_target(self, target):
        target_nodil, dilution = self.split_target_and_dilution_factor(target)
        
        # Find a match for the match_target
        match_target = target_nodil.strip().lower()
        match = self.methods_df.loc[self.methods_df[TARGET_COLUMN].str.lower() == match_target]
        if match is not None and len(match.index) > 0:
            row = match.iloc[0].copy()
            row[DILUTION_FACTOR_COLUMN] = dilution
            return row
        
        # Find a match for the match_target in the aliases column
        for idx, row in self.methods_df.iterrows():
            if pd.isna(row[TARGET_COLUMN]):
                continue
            if match_target == row[TARGET_COLUMN].strip().lower():
                row = row.copy()
                row[DILUTION_FACTOR_COLUMN] = dilution
                return row
            aliases = row[TARGET_ALIASES_COLUMN]
            if not aliases:
                continue
            aliases = [a.strip().lower() for a in aliases.split(",")]
            if match_target in aliases:
                row = row.copy()
                row[DILUTION_FACTOR_COLUMN] = dilution
                return row
        
        return None
            
    def get_dilution_factor(self, target):
        row = self.get_row_for_target(target)
        if row is not None:
            return row["dilutionFactor"]
        return 1
    
    def split_target_and_dilution_factor(self, target):
        dilution = re.sub(r"[^\:]*\:([0-9\.]*)$", r"\1", target)
        try:
            dilution = float(dilution)
            if dilution == int(dilution):
                dilution = int(dilution)
        except Exception as e:
            dilution = 1
        target = re.sub(r"\:[0-9\.]*$", "", target)
        
        return target, dilution
        
if __name__ == "__main__":
    if "get_ipython" in globals():
        opts = EasyDict({
            "config" : "qpcr_methods.yaml",
            "methods_file" : "qpcr_methods.xlsx",
        })
    else:
        args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        args.add_argument("--config", type=str, help="Configuration file", default="qpcr_methods.yaml", required=True)
        args.add_argument("--methods_file", type=str, help="Methods Excel file", default="qpcr_methods.xlsx", required=True)
        
        opts = args.parse_args()

    methods = QPCRMethods(opts.config, opts.methods_file)
    
    r = methods.get_row_for_target("covN2")
    print(r)
    