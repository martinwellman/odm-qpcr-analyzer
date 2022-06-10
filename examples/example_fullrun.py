#%%

"""
# example_fullrun.py

This file demonstrates a minimal example run of of the QPCR Analyzer, showing how to use the following:

1. QPCRExtracter to extract data from a BioRad output file.
2. QPCRPopulator to create the full QPCR report and QA/QC.

For a more complete example, which includes code to update reports on Google Drive and email the results, see the lambda_container.
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join("..", "qpcr_analyzer")))

from qpcr_extracter import QPCRExtracter
from qpcr_populator import QPCRPopulator

input_files = [
    "data/biorad-sample-n1.pdf",
    "data/biorad-sample-n2.pdf",
    "data/biorad-sample-pmmov-b.pdf",
    "data/biorad-sample-pmmov.pdf",
]

#########################################################
# 1. Run the extracter to extract data from the BioRad QPCR output files.
# The extracted output will is saved at output/odmdata/extracted-sample.xlsx
# The returned list extracter_output_files contains the extracted output file path
print("="*40)
print("Running QPCRExtracter")

extracter_output_file = "extracted-sample.xlsx"
extracter_output_dir = "output/extracted"
extracter_output_raw_dir = "output/extracted"
extracter_config = "../qpcr_analyzer/qpcr_extracter.yaml"
extracter_format_configs = [
    "../qpcr_analyzer/qpcr_extracter_biorad.yaml",
    "../qpcr_analyzer/qpcr_extracter_lightcycler.yaml",
]

extracter = QPCRExtracter(extracter_config, extracter_format_configs)
merged_extracted_file, extracter_output_files, extracter_raw_files, extracter_format_names = extracter.extract(
    input_files, 
    output_dir=extracter_output_dir, 
    raw_dir=extracter_output_raw_dir, 
    merged_file_name=extracter_output_file)

print("Finished running QPCRExtracter!")
print(f"The extracted file can be found at: {extracter_output_files}")

#########################################################
# 2. Run the QPCRPopulator to generate the full report with QA/QC.
# The final report is saved at populated/populated-sample.xlsx
# The return value populator_output_files contains the final report path
# Grouping into separate files is based on populator_output_file. Try
# adding any of the tags {site_id}, {site_title}, {parent_site_id},
# {parent_site_title}, and {sample_type} to populator_output_file. These
# tags are defined in qpcr_sites.xlsx
print("="*40)
print("Running QPCRPopulator")

# Long format
populator_output_file = "output/populated/populated-sample-long.xlsx"
populator_template_file = "../qpcr_analyzer/qpcr_template_long-2main-inh.xlsx"
populator_config = "../qpcr_analyzer/qpcr_populator_long-2main-inh.yaml"
populator_qaqc_config = "../qpcr_analyzer/qaqc_long-2main-inh.yaml"

# Wide format
# populator_output_file = "output/populated/populated-sample-wide.xlsx"
# populator_template_file = "../qpcr_analyzer/qpcr_template_wide-2main-inh.xlsx"
# populator_config = ["../qpcr_analyzer/qpcr_populator_long-2main-inh.yaml", "../qpcr_analyzer/qpcr_populator_wide_diff-2main-inh.yaml"]
# populator_qaqc_config = ["../qpcr_analyzer/qaqc_long-2main-inh.yaml", "../qpcr_analyzer/qaqc_wide_diff-2main-inh.yaml"]

populator_sampleids_config = "../qpcr_analyzer/qpcr_sampleids.yaml"
populator_sampleslog_config = "../qpcr_analyzer/qpcr_sampleslog.yaml"
populator_sampleslog_file = "data/qpcr_sampleslog.xlsx"

populator_sites_file = "../qpcr_analyzer/qpcr_sites.xlsx"
populator_sites_config = "../qpcr_analyzer/qpcr_sites.yaml"

populator_methods_file = "../qpcr_analyzer/qpcr_methods.xlsx"
populator_methods_config = "../qpcr_analyzer/qpcr_methods.yaml"

qpcr = QPCRPopulator(input_file=merged_extracted_file,
    template_file=populator_template_file, 
    target_file=populator_output_file, 
    overwrite=True, 
    config_file=populator_config, 
    qaqc_config_file=populator_qaqc_config,
    sites_config=populator_sites_config,
    sites_file=populator_sites_file,
    sampleids_config = populator_sampleids_config, 
    sampleslog_config = populator_sampleslog_config, 
    sampleslog_file = populator_sampleslog_file,
    methods_config = populator_methods_config,
    methods_file = populator_methods_file,
    hide_qaqc=False)
populator_output_files = qpcr.populate()
print("Finished running QPCRPopulator!")
print(f"Your final report can be found at: {populator_output_files}")
