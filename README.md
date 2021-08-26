# <img src="https://github.com/Big-Life-Lab/ODM/blob/018dc627d6d0842fd3d1d0b854471c225ae0eb82/img/ODM-logo.png" align="right" alt="" width="180"/> ODM QPCR Analyzer

The Open Data Model (ODM) for Wastewater-Based Surveillance is an open data model created to provide a common method for storing and sharing wastewater data for wastewater-based COVID-19 surveillance. For more information on the ODM, visit the [ODM Github Repo](https://github.com/Big-Life-Lab/ODM).

The ODM QPCR Analyzer is a tool that sits on top of the ODM and automates the analysis of QPCR results obtained from a BioRad QPCR machine. It also performs a full QA/QC on the obtained data. The tool also provides a means for the user to upload approved data to a Google Drive folder or AWS S3 bucket (HTTP and HTTPS targets will be added soon).

For a more complete look at the Analyzer and its various components with details on the code and how to customize the reports, see [ODM QPCR Analyzer Manual and Spec.docx](ODM%20QPCR%20Analyzer%20Manual%20and%20Spec.docx).

## Main Components

The ODM QPCR Analyzer has 3 main components:

1. The QPCR Analyzer itself, where most of the code resides. See [qpcr_analyzer](qpcr_analyzer) for details.
1. The Lambda Container, which contains all code for building and running the analyzer as an AWS Lambda Function in the cloud. See [lambda_container](lambda_container) for details.
1. A sample QPCR Analyzer website that allows users to upload PDFs and execute the Lambda Function. See [qpcr_analyzer_website](qpcr_analyzer_website) for details.

## Installation

To install the QPCR Analyzer on your computer run the following commands:

    git clone https://github.com/martinwellman/odm-qpcr-analyzer.git
    pip install -r odm-qpcr-analyzer/qpcr_analyzer/requirements.txt
    cd odm-qpcr-analyzer/qpcr_analyzer
    ./localfixes.sh

The script localfixes.sh applies changes to both OpenPYXL and Ghostscript. These changes will affect your local copies of the OpenPYXL and Ghostscript packages, but should not affect behavior of other scripts that use these packages. If you would like to prevent these changes from affecting other scripts, set up a separate virtual environment for the QPCR Analyzer with a tool such as pyenv. In the future, these changes will be moved to a separate GitHub repository. For details on what localfixes.sh does, see [qpcr_analyzer/README.md](qpcr_analyzer/README.md).

Install the [ODM-Import](https://github.com/jeandavidt/ODM-Import) repo (NOTE: This is temporarily set to the fork at [martinwellman/ODM-Import.git](https://github.com/martinwellman/ODM-Import.git), it will be changed back to jeandavidt/ODM-Import soon):

    git clone https://github.com/martinwellman/ODM-Import.git
    cd ODM-Import
    pip install -e .

The `ODM-Import` package has various tools and utilities for converting data files to ODM format. The mapper that the QPCR Analyzer uses is called `BioRadMapper`, found at [wbe_odm/odm_mappers/biorad_mapper.py](https://github.com/jeandavidt/ODM-Import/blob/main/wbe_odm/odm_mappers/biorad_mapper.py).

## Example

To see a bare-bones example of how to use the QPCR Analyzer see [examples/example_fullrun.py](examples/example_fullrun.py). This example extracts data from BioRad output files, maps that data to ODM format, and generates the final report along with QA/QC results. It uses sample BioRad files obtained from a lab based at uOttawa.

For a more complete example, including options for emailing the reports and updating files stored in the cloud, see the [lambda_container](lambda_container).

## Managing AWS Costs

It is recommended to regularly check your billing to ensure there are no unexpected AWS charges. This section describes the AWS services used and how to delete unused resources.

The Lambda container uses the following services on AWS:

- AWS S3
- AWS Lambda
- AWS SES
- AWS ECR
- AWS EC2

It also uses the Google Drive API.

### S3 File Structure

The file structure on S3 is as follows:

    s3bucket (eg. odm-qpcr-analyzer)
        - u (User data)
            - UserA
                - inputs
                - outputs
            - UserB
                - inputs
                - outputs
            ...
        - v (Analyzer version data)
            - 0.1.15
                - config
                - source
            - 0.1.16
                - config
                - source
            ...

### S3 Folder /v: Version Source Code and Config

Each version created with [makedockeronec2.sh](makedockeronec2.sh) has configuration files and source code uploaded to `/v/{version}`. Any old versions that are no longer used can be deleted. The `source` subfolder for a version can be deleted, it is only used while building the Lambda function Docker container, to transfer code from your local environment to EC2. The `config` subfolder should be preserved for versions still in use. It contains all configuration files for the Analyzer. You can update configuration files by uploading changes to the `config` subfolder. See the [S3 dashboard](https://console.aws.amazon.com/s3/home).

### S3 Folder /u: User Files

Each web user has their own data folder in /u/{user} (eg. /u/Martin). The `inputs` subfolder contains inputs uploaded from the website, while the `outputs` folder contains the outputs of the Analyzer. These folders can be deleted, although it is recommended to not delete recently added folders under `inputs` in case an analyzer run is currently in progress and still requires those input files (the subfolders have the date and time in their names, in Eastern time). See the [S3 dashboard](https://console.aws.amazon.com/s3/home).

### ECR Private Repositories

A private repository is added by the [makedockeronec2.sh](makedockeronec2.sh) script. Built Docker containers are added here. Any old and unused builds can be deleted to reduce costs. See the [ECR Dashboard](https://console.aws.amazon.com/ecr/repositories).

## EC2 Instances

All EC2 instances are terminated automatically when complete. The scripts use t2.micro instances by default, which are free-tier eligible. You may want to regularly monitor EC2 usage and check to make sure no stray instances have been left running. See the [EC2 Instances Dashboard](https://console.aws.amazon.com/ec2/v2/home#Instances:).

## EC2 Images and Snapshots

An EC2 AMI is created by [makeec2ami.sh](makeec2ami.sh). If you run this script multiple times then you may want to delete old AMIs that are no longer being used. See the [EC2 AMIs Dashboard](https://console.aws.amazon.com/ec2/v2/home#Images:sort=name).

EBS snapshots are also created for the AMI. Snapshots that are no longer used can be deleted. See the [EC2 EBS Snapshots Dashboard](https://console.aws.amazon.com/ec2/v2/home#Snapshots:sort=snapshotId).

