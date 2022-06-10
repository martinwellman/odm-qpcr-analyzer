#%%
"""
# qpcr_extracter.py

Extracts data tables from QPCR output files. These are PDF or Excel files and automatically
detects which machine (eg. BioRad, LightCycler) the output belongs to.

## Usage

    extracter = QPCRExtracter("qpcr_extracter.yaml",
        format_configs=[
            "qpcr_extracter_biorad.yaml",
            "qpcr_extracter_lightcycler.yaml",
            "qpcr_extracter_ariamx.yaml",
            "qpcr_extracter_qiaquant.yaml",
        ])
    output_files, raw_files = extracter.extract(input_files,    # list of BioRad PDF/Excel files
        output_dir,                                             # Where to save the extracted data
        raw_dir)                                                # Where to save the raw data (intermediate extracted file)
"""

import camelot
import random
from easydict import EasyDict
import pandas as pd
import yaml
import argparse
from datetime import datetime
import os
import shutil
import re

from excel_file_utils import fix_xlsx_file, xls_to_xlsx

class QPCRExtracter(object):
    def __init__(self, config, format_configs):
        with open(config, "r") as f:
            self.config = yaml.safe_load(f)
            
        self.format_configs = []
        for format_config in format_configs:
            with open(format_config, "r") as f:
                self.format_configs.append(yaml.safe_load(f))

    def extract(self, input_files, output_dir, raw_dir, merged_file_name=None):
        """Run a full extraction on the input files passed to the constructor.
        Args:
            input_files (str|list[str]): BioRad files to extract the data from.
            output_dir (str): Directory to save the final extracted files to.
            raw_dir (str): Directory to save the raw data to. These are intermediate files which have
                minimal processing of the inputs. Excel inputs are cleaned to remove extra data, PDFs are
                cleaned to extract the Quantification Data tables (and saved as Excel files).
            merged_file_name (str|None): Excel file name (without the path) to save the merged DataFrame to.
                This will be saved in the directory output_dir. The merged DataFrame contains all records extracted from 
                the input_files. If None then a merged file name will be generated automatically (see the Returns section 
                on how to get the merged file name)
                
        Returns:
            str: The full path to the output file that contains all outputs merged into a single file. This will
                be saved in output_dir. If nothing was subtracted then this is None.
            list[str]: List of full paths to the extracted Excel files, corresponding to each file in input_files.
                If extraction failed for a file then the corresponding element will be None.
            list[str]: List of full paths to the raw Excel files.
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        input_files = [input_files] if isinstance(input_files, str) else input_files
        extracted_files = []
        raw_files = []
        format_names = []
        all_dfs = []
        for input_file in input_files:
            file_ext = os.path.splitext(input_file.lower())[-1]
            
            # Make output and raw file paths, add .xlsx since all outputs are Excel files
            output_file = os.path.join(output_dir, os.path.basename(input_file))
            raw_file = os.path.join(raw_dir, os.path.basename(input_file))
            if file_ext != ".xlsx":
                output_file = f"{output_file}.xlsx"
                raw_file = f"{raw_file}.xlsx"
            
            if file_ext == ".pdf":
                cur_df, _, output_file, raw_file, format_name = self.convert_to_excel(input_file, output_file, raw_file)
                all_dfs.append(cur_df)
            elif file_ext == ".xlsx" or file_ext == ".xls":
                cur_df, _, output_file, raw_file, format_name = self.cleanup_excel(input_file, output_file, raw_file)
                all_dfs.append(cur_df)
            else:
                print(f"Unrecognized file extension in extracter for file {input_file}")
                output_file = None
                raw_file = None
                format_name = None
            extracted_files.append(output_file)
            raw_files.append(raw_file)
            format_names.append(format_name)

        # Merge all extracted DataFrames into a single file
        if len([df for df in all_dfs if df is not None]) > 0:
            dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            rnd = str(random.randint(1e10, 1e11-1))
            merged_file_name = os.path.basename(merged_file_name) if merged_file_name else f"extracted-merged-{dt}-{rnd}.xlsx"
            merged_file_name = os.path.join(output_dir, merged_file_name)
            merged_df = pd.concat(all_dfs)
            with pd.ExcelWriter(merged_file_name) as writer:
                merged_df.to_excel(writer, freeze_panes=(1, 0), index=False)
        else:
            merged_file_name = None
                
        return merged_file_name, extracted_files, raw_files, format_names
            
    def cleanup_excel(self, input_file, output_file, raw_file):
        """Cleanup a QPCR Excel file and save it to disk. Supports multiple formats (eg. BioRad, AriaMX,
        Qiaquant, Lightcycler)

        Args:
            input_file (str): The input Excel file to clean up (this is a BioRad output XLSX).
            output_file (str): File (with path) to save the final extraction to.
            raw_file (str): File (with path) for where to save the intermediate raw file, which is just the
                original table found in the input file.
            
        Returns:
            pd.DataFrame: The DataFrame of the fully processed data. (None if error)
            pd.DataFrame: The raw data, which is the same as raw_df but with the columns specified by
                format_config["delete_columns_from_raw"] removed. (None if error)
            str: Path of the output file (same as the output_file parameter). (None if error)
            str: Path of the raw file (same as the raw parameter). (None if error)
        """
        print(f"Cleaning {input_file}")
        
        def _cleanup_error():
            try:
                os.remove(output_file)
            except:
                pass
            try:
                os.remove(raw_file)
            except:
                pass
        
        try:
            # Copy the file to the raw file (unchanged)
            raw_dir = os.path.dirname(raw_file)
            if raw_dir:
                os.makedirs(raw_dir, exist_ok=True)
            if os.path.splitext(input_file)[-1] == ".xls":
                raw_file = xls_to_xlsx(input_file, raw_file) or raw_file
            else:
                shutil.copyfile(input_file, raw_file)
        except Exception as e:
            print(f"Exception copying input file to output file: {e}")
            _cleanup_error()
            return None, None, None, None, None
            
        # Fix the Excel file and load it. See fix_xlsx_file for details of what fixing does and why it's needed.
        raw_ext = os.path.splitext(raw_file)[-1]
        if raw_ext == ".xlsx":
            try:
                fix_xlsx_file(raw_file)
            except:
                print(f"Could not fix XLSX file {raw_file}")
                _cleanup_error()
                return None, None, None, None, None
        try:
            df = pd.read_excel(raw_file, header=None)
        except:
            print(f"Exception loading Excel file {raw_file}")
            _cleanup_error()
            return None, None, None, None, None

        # Keep on parsing (increasing skiprows on each step) until we find the header that has
        # all the required columns (the spreadsheet might start with a bunch of unrelated details)
        format_config = None
        for row_num, row_data in df.iterrows():
            cur_columns = [None if pd.isna(c) else str(c).strip() for c in row_data]
            # Strip off trailing empty column names
            while len(cur_columns) > 0:
                if cur_columns[-1]: break
                cur_columns = cur_columns[:-1]
            format_config = self.get_matching_config_from_columns(cur_columns)
            if format_config is not None:
                print(f"Extracter found input format: {format_config['qpcr_format_name']}")
                df = df[df.columns[:len(cur_columns)]]
                df = df.iloc[row_num+1:].reset_index(drop=True)
                df.columns = cur_columns
                break

        if format_config is None:
            print(f"Could not find required headers in input file: {input_file}")
            _cleanup_error()
            return None, None, None, None, None
            
        # Drop everything after (and including) the first blank row
        for idx, row in df.iterrows():
            non_empties = [c for c in row if c is not None and c != ""]
            if len(non_empties) == 0:
                df = df.drop(df.index[idx:], axis=0)
                
        return self.finalize_and_save_data(input_file, df, format_config, output_file, raw_file)

    def convert_to_excel(self, input_file, output_file, raw_file):
        """Convert a QPCR PDF input_file to an Excel file (output_file), by extracting the "Quantification Data" table.

        Args:
            input_file (str): The input PDF file to extract the data table from.
            output_file (str): File (with path) to save the final extraction to.
            raw_file (str): File (with path) for the intermediate raw file, which is just the
                original table found in the input file.

        Returns:
            pd.DataFrame: The DataFrame of the fully processed data. (None if error)
            pd.DataFrame: The raw data, which is the same as raw_df but with the columns specified by
                format_config["delete_columns_from_raw"] removed. (None if error)
            str: Path of the output file (same as the output_file parameter). (None if error)
            str: Path of the raw file (same as the raw parameter). (None if error)
            str: The name of the format of the Excel file (eg. BioRad, Qiaquant, AriaMX, LightCycler)
        """
        def _format_cell(c):
            if not isinstance(c, str):
                return c

            # For strings: Remove new lines and try to cast to a float.
            # If we can't cast then keep the string value instead
            c = c.replace("\n", " ").strip()

            try:
                v = float(c)
                c = c if v is None else v
            except:
                pass
                
            return c
        
        print(f"Reading PDF {input_file}...")
        try:
            tables = camelot.read_pdf(input_file,
                pages="all", 
                split_text=True,
                multiple_tables=True)
        except:
            print(f"Exception loading PDF file with Camelot: {input_file}")
            return None, None, None, None, None
        
        print("Extracting tables from PDF...")
        df = None
        format_config = None
        for table in tables:
            columns = [c.replace("\n", " ").strip() for c in table.df.loc[0].tolist()]
            
            # Based on the columns, get the format config. Note that once a matching format config is found we cannot change
            # to a different format config in all the remaining tables in the PDF
            cur_format_config = self.get_matching_config_from_columns(columns, format_configs=None if format_config is None else [format_config])
            if cur_format_config is None:
                continue
            format_config = cur_format_config
            
            # Clean up the table
            cur_df = table.df
            cur_df.columns = columns
            cur_df = cur_df.drop(0, axis=0)
            cur_df[cur_df == "N/A"] = None
            cur_df = cur_df.applymap(_format_cell)

            # Append the table to our DataFrame
            if df is None:
                df = cur_df.copy()
            else:
                df = pd.concat([df, cur_df], ignore_index=True)
                
        if df is None or len(df.index) == 0:
            return None, None, None, None, None

        return self.finalize_and_save_data(input_file, df, format_config, output_file, raw_file)
    
    def get_matching_config_from_columns(self, columns, format_configs=None):
        """Based on the columns, determine which QPCR output format we're working with. Output formats
        include BioRad, Lightcycler, and others. Each QPCR output has different columns.

        Args:
            columns (list[str]): The columns to test
            format_configs (list[dict], optional): All possible format configs to consider. These are dictionaries loaded from config
                files on disk. If None then use all the format_configs files passed to the constructor. Defaults to None.

        Returns:
            dict: The matching format config for the specified columns. None if no match was found.
        """
        if format_configs is None:
            format_configs = self.format_configs
        for format_config in format_configs:
            matches = [c for c in format_config["match_columns_in_raw"] if c in columns]
            if len(matches) == len(format_config["match_columns_in_raw"]):
                return format_config
        return None
    
    def apply_mappers(self, df, mappers):
        if mappers is None:
            return
        
        def _apply_mapper(v, m):
            if not isinstance(v, str):
                return v
            flags = re.IGNORECASE if m.get("ignore_case", False) else 0
            return re.sub(m["match"], m["replace"], v, flags=flags)
            
        for cur_map in mappers:
            columns = cur_map["columns"]
            if isinstance(columns, str):
                columns = [columns]
            target_columns = cur_map.get("target", columns)
            if isinstance(target_columns, str):
                target_columns = [target_columns]
            df[target_columns] = df[columns].applymap(lambda x: _apply_mapper(x, cur_map))
            
    def finalize_and_save_data(self, input_file, raw_df, format_config, output_file, raw_file):
        """Do some final processing of the DataFrame and save the results to disk.

        Args:
            input_file (str): The original file path that we loaded the data from. We do not read
                data from this file, as it has already been read to create raw_df. Instead we use it
                to set the plateID in the final DataFrame.
            raw_df (pd.DataFrame): The DataFrame containing the raw data extracted from the input file.
            format_config (dict): The configuration to process the DataFrame.
            output_file (str): Path to write the output to.
            raw_file (str): Path to write the raw data to. The raw data is raw_df, with possibly some
                columns removed specified by format_config["delete_columns_from_raw"]. If None then
                do not save to disk.

        Returns:
            pd.DataFrame: The DataFrame of the fully processed data. (None if error)
            pd.DataFrame: The raw data, which is the same as raw_df but with the columns specified by
                format_config["delete_columns_from_raw"] removed. (None if error)
            str: Path of the output file (same as the output_file parameter). (None if error)
            str: Path of the raw file (same as the raw parameter). (None if error)
        """
        # Delete columns from raw
        raw_df = raw_df.drop(format_config.get("delete_columns_from_raw", []), axis=1, errors="ignore")
        
        # Copy over all columns we want to keep
        df = pd.DataFrame(columns=[c["target"] for c in format_config["extract_columns"]])
        for col_info in format_config["extract_columns"]:
            if col_info["origin"] in raw_df.columns:
                df[col_info["target"]] = raw_df[col_info["origin"]]
                
        df["qpcrFormat"] = format_config["qpcr_format_name"]
        df["plateID"] = re.sub("[^A-Za-z0-9]", "_", os.path.basename(input_file))
                                
        # Apply all mappers for the current format
        self.apply_mappers(df, format_config.get("mappers", None))
        # Apply all the global mappers
        if self.config:
            self.apply_mappers(df, self.config.get("mappers", None))
                                
        print(f"Saving extracted file to {output_file}")
        dirname = os.path.dirname(output_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with pd.ExcelWriter(output_file) as writer:
            df.to_excel(writer, freeze_panes=(1, 0), index=False)
        
        print(f"Saving raw file to {raw_file}")
        dirname = os.path.dirname(raw_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with pd.ExcelWriter(raw_file) as writer:
            raw_df.to_excel(writer, freeze_panes=(1, 0), index=False)
        
        return df, raw_df, output_file, raw_file, format_config["qpcr_format_name"]

if __name__ == "__main__":
    if "get_ipython" in globals():
        opts = EasyDict({
            "input_files" : [                
                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/other/2022-05-06 N2 (AriaMX output) - N1.xlsx",
                "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/2021-08-19/qPCR-2021-08-19_N1_O_CSC_H_VC_GAT_13 SAMPLES_KB.xlsx",
                "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/2021-08-19/qPCR-2021-08-19_N2_O_CSC_H_VC_GAT_13 SAMPLES_KB.pltd.xlsx",
                "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/biorad-ottawa/2021-08-19/qPCR-2021-08-19_PEPPER_O_CSC_H_VC_GAT_13 SAMPLES_KB.pltd.xlsx",

                # "/Users/martinwellman/Documents/Health/Wastewater/Additional Labs Info/2022-05-06 N2 (AriaMX output).xlsx",
                # "/Users/martinwellman/Documents/Health/Wastewater/Additional Labs Info/2022-03-24 N1 (Qiaquant output).xls",

                # "/Users/martinwellman/Documents/Health/Wastewater/Code/inputs/lightcycler/LightCycler PDF output example.PDF",
            ],
            "raw_dir" : "/Users/martinwellman/Documents/Health/Wastewater/Code/output/raw",
            "output_dir" : "/Users/martinwellman/Documents/Health/Wastewater/Code/output",
            "config" : "/Users/martinwellman/Documents/Health/Wastewater/Code/odm-qpcr-analyzer/qpcr_analyzer/qpcr_extracter.yaml",
            "format_configs" : [
                "qpcr_extracter_biorad.yaml",
                "qpcr_extracter_lightcycler.yaml",
                "qpcr_extracter_ariamx.yaml",
                "qpcr_extracter_qiaquant.yaml",
            ],
        })
    else:
        args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        args.add_argument("--config", type=str, help="Main config file", default="qpcr_extracter.yaml")
        args.add_argument("--format_configs", nargs="+", type=str, help="Configuration files for all supported QPCR formats", default=["qpcr_extracter_biorad.yaml"])
        args.add_argument("--input_files", nargs="+", type=str, help="Input file to analyze", required=True)
        args.add_argument("--output_dir", type=str, help="Location to save final extracted results", default="results")
        args.add_argument("--raw_dir", type=str, help="Location to save raw intermediate extracted files", default="results_raw")
        opts = args.parse_args()

    tic = datetime.now()
    print("Starting extracter at:", tic)
    qpcr = QPCRExtracter(opts.config, opts.format_configs)
    merged_file, output_files, raw_files, format_names = qpcr.extract(opts.input_files, output_dir=opts.output_dir, raw_dir=opts.raw_dir, merged_file_name="extracted-merged.xlsx")
    print("Output files:", output_files)
    print("Raw files:", raw_files)
    print("Merged file:", merged_file)
    toc = datetime.now()
    print("Started at:", tic)
    print("Ended at:", toc)
    print("Total duration:", toc - tic)
    
