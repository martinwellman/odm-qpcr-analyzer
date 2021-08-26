#%%
# %load_ext autoreload
# %autoreload 2

"""
run_mapper.py
=============

Sample code for running the BioRadMapper in the ODM-Import library.

The lab_data parameter passed to run_mapper is the output of QPCRExtracter. static_data is not used by the mapper but included here for completeness.
"""

from wbe_odm.odm_mappers import biorad_mapper
from easydict import EasyDict
import argparse
import os

def run_mapper(config_file, map_path, lab_data, static_data, remove_duplicates, start_date, end_date, output):
    mapper_dir = os.path.dirname(biorad_mapper.__file__)
    config_file = config_file or os.path.join(mapper_dir, "biorad_mapper.yaml")
    map_path = map_path or os.path.join(mapper_dir, "biorad_map.csv")
    mapper = biorad_mapper.BioRadMapper(config_file=config_file)    
    mapper.read(lab_data,
                static_data,
                map_path=map_path,
                remove_duplicates=bool(remove_duplicates),
                startdate=start_date, 
                enddate=end_date)
    output_file, duplicates_file = mapper.save_all(output, duplicates_file=remove_duplicates)
    print("Finished mapping!")
    return output_file, duplicates_file

if __name__ == "__main__":
    if "get_ipython" in globals():
        mapper_dir = os.path.dirname(biorad_mapper.__file__)
        opts = EasyDict({
            "config_file" : os.path.join(mapper_dir, "biorad_mapper.yaml"),
            "map_path" : os.path.join(mapper_dir, "biorad_map.csv"),
            "lab_data" : "/Users/martinwellman/Documents/Health/Wastewater/Code/extracted/merged-aug9.xlsx",
            "static_data" : "",
            "start_date" : "",
            "end_date" : "",
            "remove_duplicates" : "/Users/martinwellman/Documents/Health/Wastewater/Code/odmdata/dupes.xlsx",
            "output" : "/Users/martinwellman/Documents/Health/Wastewater/Code/odmdata/odm_merged-aug9.xlsx",
        })
    else:
        args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        args.add_argument("--config_file", type=str, help="Path to the mapper YAML config file. (Required)", required=True)
        args.add_argument("--map_path", type=str, help="Path to the mapper CSV file. (Required)", required=True)
        args.add_argument("--lab_data", type=str, help="Path to the lab data Excel file. (Required)", required=True)
        args.add_argument("--static_data", type=str, help="Path to the static data Excel file. (Optional)", default=None)
        args.add_argument("--start_date", type=str, help="Filter sample dates starting on this date (exclusive) (yyyy-mm-dd). (Optional)", default=None)
        args.add_argument("--end_date", type=str, help="Filter sample dates ending on this date (exclusive) (yyyy-mm-dd). (Optional)", default=None)
        args.add_argument("--remove_duplicates", type=str, help="If set then remove duplicates from all WW tables based on each table's primary key, and save the duplicates in this additional file. (Optional)", default=None)
        args.add_argument("--output", type=str, help="Path to the Excel output file. (Required)", required=True)
        opts = args.parse_args()

    run_mapper(
        config_file=opts.config_file,
        map_path=opts.map_path,
        lab_data=opts.lab_data,
        static_data=opts.static_data,
        remove_duplicates=opts.remove_duplicates,
        start_date=opts.start_date, 
        end_date=opts.end_date, 
        output=opts.output
    )
