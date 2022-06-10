# <img src="https://github.com/Big-Life-Lab/ODM/blob/018dc627d6d0842fd3d1d0b854471c225ae0eb82/img/ODM-logo.png" align="right" alt="" width="180"/> ODM QPCR Analyzer

The Open Data Model (ODM) for Wastewater-Based Surveillance is an open data model created to provide a common method for storing and sharing wastewater data for wastewater-based COVID-19 surveillance. For more information on the ODM, visit the [ODM Github Repo](https://github.com/Big-Life-Lab/ODM).

The ODM QPCR Analyzer is a tool that sits on top of the ODM and automates the analysis of QPCR results obtained from a BioRad QPCR machine. It also performs a full QA/QC on the obtained data. The tool also provides a means for the user to upload approved data to a Google Drive folder or AWS S3 bucket (HTTP and HTTPS targets will be added soon).

For a more complete look at the Analyzer and its various components with details on the code and how to customize the reports, see [ODM QPCR Analyzer Manual and Spec.docx](ODM%20QPCR%20Analyzer%20Manual%20and%20Spec.docx).

## Main Components

The ODM QPCR Analyzer has 3 main components:

1. The QPCR Analyzer itself, where most of the code resides. See [qpcr_analyzer](qpcr_analyzer) for details.
1. The Lambda Container, which contains all code for building and running the analyzer as an AWS Lambda Function in the cloud. See [lambda_container](lambda_container) for details.
1. A Plotly Dash-based website that allows users to upload QPCR data files and execute the Lambda Function. See [odm-qpcr-analyzer-dash](https://github.com/martinwellman/odm-qpcr-analyzer-dash) for details (the repo is currently private).

## Installation

To install the QPCR Analyzer on your computer run the following commands:

    git clone https://github.com/martinwellman/odm-qpcr-analyzer.git
    pip install -r odm-qpcr-analyzer/qpcr_analyzer/requirements.txt
    cd odm-qpcr-analyzer/qpcr_analyzer
    ./localfixes.sh

The script [localfixes.sh](qpcr_analyzer/localfixes.sh) applies changes to OpenPYXL, Ghostscript, and PyCel. These changes will affect your local copies of the OpenPYXL, Ghostscript, and PyCel packages, but should not affect behavior of other scripts that use these packages. If you would like to prevent these changes from affecting other scripts, set up a separate virtual environment for the QPCR Analyzer with a tool such as pyenv. In the future, these changes will be moved to a separate GitHub repository. For details on what [localfixes.sh](qpcr_analyzer/localfixes.sh) does, see [qpcr_analyzer/README.md](qpcr_analyzer/README.md).

## Example

To see a bare-bones example of how to use the QPCR Analyzer see [examples/example_fullrun.py](examples/example_fullrun.py). This example extracts data from BioRad output files, maps that data to ODM format, and generates the final report along with QA/QC results. It uses sample BioRad files obtained from a lab based at uOttawa.

For a more complete example, including options for emailing the reports and updating files stored in the cloud, see the [lambda_container](lambda_container).

## TODO

- Finish [ODM QPCR Analyzer Manual and Spec.docx](ODM%20QPCR%20Analyzer%20Manual%20and%20Spec.docx).
- Get rid of [localfixes.sh](qpcr_analyzer/localfixes.sh), move the changes/fixes to separate GitHub repos for OpenPYXL and Ghostscript.
