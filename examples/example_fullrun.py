#%%

"""
example_fullrun.py
==================

This file demonstrates a minimal example run of of the QPCR Analyzer, showing how to use the following:

1. QPCRExtracter to extract data from a BioRad output file.
2. BioRadMapper to map the extracted file to ODM format.
3. QPCRPopulator to create the full QPCR report and QA/QC.

For a more complete example, which includes code to update reports on Google Drive and email the results, see the lambda_container.
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join("..", "qpcr_analyzer")))

from qpcr_extracter import QPCRExtracter
from qpcr_populator import QPCRPopulator
from wbe_odm.odm_mappers import biorad_mapper

input_files = [
    "data/biorad-sample-n1.pdf",
    "data/biorad-sample-n2.pdf",
    "data/biorad-sample-pmmov-b.pdf",
    "data/biorad-sample-pmmov.pdf",
]

sites_file = "../qpcr_analyzer/sites.xlsx"
sites_config = "../qpcr_analyzer/sites.yaml"

#########################################################
# 1. Run the extracter to extract data from the BioRad QPCR output files.
# The extracted output will is saved at output/odmdata/extracted-sample.xlsx
# The returned list extracter_output_files contains the extracted output file path
print("="*40)
print("Running QPCRExtracter")

extracter_output_file = "extracted-sample.xlsx"
extracter_output_dir = "output/extracted"
extracter_samples = "data/samples.xlsx"
extracter_config = "../qpcr_analyzer/qpcr_extracter_ottawa.yaml"

qpcr = QPCRExtracter(
    input_files, 
    extracter_output_file, 
    extracter_output_dir, 
    extracter_samples, 
    extracter_config, 
    sites_file=sites_file, 
    sites_config=sites_config, 
    upload_to=None, 
    overwrite=True, 
    save_raw=False)
extracter_input_files, extracter_output_files, extracter_raw_files, extracter_upload_files = qpcr.extract()
print("Finished running QPCRExtracter!")
print(f"The extracted file can be found at: {extracter_output_files}")

#########################################################
# 2. Run the BioRadMapper to convert QPCRExtracter's output to ODM format.
# The output ODM data file is saved at output/odmdata/odmdata-sample.xlsx
# The returned value mapper_output_file contains the ODM data file path.
print("="*40)
print("Running BioRadMapper")

mapper_dir = os.path.dirname(biorad_mapper.__file__)
mapper_config_file = os.path.join(mapper_dir, "biorad_mapper.yaml")
mapper_map_path = os.path.join(mapper_dir, "biorad_map.csv")
mapper_output_file = "output/odmdata/odmdata-sample.xlsx"

mapper = biorad_mapper.BioRadMapper(config_file=mapper_config_file)    
mapper.read(extracter_output_files[0],
            "",
            map_path=mapper_map_path,
            remove_duplicates=True,
            startdate=None, 
            enddate=None)
mapper_output_file, mapper_duplicates_file = mapper.save_all(mapper_output_file, duplicates_file=None)
print("Finished running BioRadMapper!")
print(f"The ODM output file can be found at: {mapper_output_file}")

#########################################################
# 3. Run the QPCRPopulator to generate the full report with QA/QC.
# The final report is saved at populated/populated-sample.xlsx
# The return value populator_output_files contains the final report path
# Grouping into separate files is based on populator_output_file. Try
# adding any of the tags {site_id}, {site_title}, {parent_site_id},
# {parent_site_title}, and {sample_type} to populator_output_file. These
# tags are defined in sites.xlsx
print("="*40)
print("Running QPCRPopulator")

populator_output_file = "output/populated/populated-sample.xlsx"
populator_template_file = "../qpcr_analyzer/qpcr_template_ottawa.xlsx"
populator_config = "../qpcr_analyzer/qpcr_populator_ottawa.yaml"
populator_qaqc_config = "../qpcr_analyzer/qaqc_ottawa.yaml"

qpcr = QPCRPopulator(input_file=mapper_output_file,
    template_file=populator_template_file, 
    target_file=populator_output_file, 
    overwrite=True, 
    config_file=populator_config, 
    qaqc_config_file=populator_qaqc_config,
    sites_config=sites_config,
    sites_file=sites_file,
    hide_qaqc=False)
populator_output_files = qpcr.populate()
print("Finished running QPCRPopulator!")
print(f"Your final report can be found at: {populator_output_files}")
