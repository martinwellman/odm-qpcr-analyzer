#!/bin/bash

# Set up all file links, from the Lambda container directory to the QPCR Analyzer code. Should be run once when first
# setting up the project on your computer.

set -e

# Retrieve the QPCR Analyzer home directory
ANALYZER_DIR="$(cd "$(dirname "$0")/.."; pwd)"

echo "QPCR Analyzer directory:      ${ANALYZER_DIR}"

APP_DIR="source/app"

pushd "$APP_DIR"

# QPCR analyzer code
ln -sf "$ANALYZER_DIR/qpcr_analyzer/cloud_utils.py" cloud_utils.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/custom_functions.py" custom_functions.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/emailer.py" emailer.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/excel_calculator.py" excel_calculator.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/excel_file_utils.py" excel_file_utils.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/gdrive_utils.py" gdrive_utils.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter.py" qpcr_extracter.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_methods.py" qpcr_methods.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator.py" qpcr_populator.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_qaqc.py" qpcr_qaqc.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sampleids.py" qpcr_sampleids.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sampleslog.py" qpcr_sampleslog.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sites.py" qpcr_sites.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_updater.py" qpcr_updater.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_utils.py" qpcr_utils.py

# Config files
ln -sf "$ANALYZER_DIR/qpcr_analyzer/credentials.json" credentials.json
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qaqc_b117.yaml" qaqc_b117.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qaqc_wide_diff-2main-inh.yaml" qaqc_wide_diff-2main-inh.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qaqc_long-2main-inh.yaml" qaqc_long-2main-inh.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter.yaml" qpcr_extracter.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter_biorad.yaml" qpcr_extracter_biorad.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter_lightcycler.yaml" qpcr_extracter_lightcycler.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter_qiaquant.yaml" qpcr_extracter_qiaquant.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter_ariamx.yaml" qpcr_extracter_ariamx.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_methods.xlsx" qpcr_methods.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_methods.yaml" qpcr_methods.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator_b117_diff.yaml" qpcr_populator_b117_diff.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator_wide_diff-2main-inh.yaml" qpcr_populator_wide_diff-2main-inh.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator_long-2main-inh.yaml" qpcr_populator_long-2main-inh.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sampleids.yaml" qpcr_sampleids.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sampleslog.yaml" qpcr_sampleslog.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_template_b117.xlsx" qpcr_template_b117.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_template_wide-2main-inh.xlsx" qpcr_template_wide-2main-inh.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_template_long-2main-inh.xlsx" qpcr_template_long-2main-inh.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_updater_b117.yaml" qpcr_updater_b117.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_updater.yaml" qpcr_updater.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sites.xlsx" qpcr_sites.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sites.yaml" qpcr_sites.yaml

popd

