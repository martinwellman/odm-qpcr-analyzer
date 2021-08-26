#!/bin/bash

# Set up all file links, from the Lambda container directory to the QPCR Analyzer code. Should be run once when first
# setting up the project on your computer.

set -e

# Retrieve the QPCR Analyzer home directory and the ODM-Import wbe_odm directory
ANALYZER_DIR="$(cd "$(dirname "$0")/.."; pwd)"
WBE_ODM_DIR=$(python3 -c "import wbe_odm, os; print(os.path.dirname(wbe_odm.__file__));" 2> /dev/null)

if [ "$?" != "0" -o "$WBE_ODM_DIR" == "" ]; then
    echo "The ODM-Import package has not been installed. Please see https://github.com/martinwellman/odm-qpcr-analyzer for instructions."
    exit 1
fi

echo "QPCR Analyzer directory:      ${ANALYZER_DIR}"
echo "ODM-Import/wbe_odm directory: ${WBE_ODM_DIR}"

APP_DIR="source/app"

pushd "$APP_DIR"
# QPCR analyzer code
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator.py" qpcr_populator.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter.py" qpcr_extracter.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_qaqc.py" qpcr_qaqc.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_updater.py" qpcr_updater.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_sites.py" qpcr_sites.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_utils.py" qpcr_utils.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/cloud_utils.py" cloud_utils.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/gdrive_utils.py" gdrive_utils.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/emailer.py" emailer.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/fix_xlsx.py" fix_xlsx.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/excel_calculator.py" excel_calculator.py
ln -sf "$ANALYZER_DIR/qpcr_analyzer/custom_functions.py" custom_functions.py

# Config files
ln -sf "$WBE_ODM_DIR/odm_mappers/biorad_map.csv" biorad_map.csv
ln -sf "$WBE_ODM_DIR/odm_mappers/biorad_mapper.yaml" biorad_mapper.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_template_ottawa_b117.xlsx" qpcr_template_ottawa_b117.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_template_ottawa_wide.xlsx" qpcr_template_ottawa_wide.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_template_ottawa.xlsx" qpcr_template_ottawa.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qaqc_ottawa_b117.yaml" qaqc_ottawa_b117.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qaqc_ottawa_wide_diff.yaml" qaqc_ottawa_wide_diff.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qaqc_ottawa.yaml" qaqc_ottawa.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_extracter_ottawa.yaml" qpcr_extracter_ottawa.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator_ottawa.yaml" qpcr_populator_ottawa.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator_ottawa_wide_diff.yaml" qpcr_populator_ottawa_wide_diff.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_populator_ottawa_b117_diff.yaml" qpcr_populator_ottawa_b117_diff.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_updater.yaml" qpcr_updater.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/qpcr_updater_b117.yaml" qpcr_updater_b117.yaml
ln -sf "$ANALYZER_DIR/qpcr_analyzer/credentials.json" credentials.json
ln -sf "$ANALYZER_DIR/qpcr_analyzer/sites.xlsx" sites.xlsx
ln -sf "$ANALYZER_DIR/qpcr_analyzer/sites.yaml" sites.yaml
popd

