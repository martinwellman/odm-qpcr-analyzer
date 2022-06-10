
# Lambda Container

The Lambda Container is all the code required to run the QPCR Analyzer as an AWS Lambda Function. Included here are shell scripts to build the Docker container on an AWS EC2 instance, upload the container to AWS ECR, and publish the container to AWS Lambda.

## Running the Shell Scripts

The scripts [copyfiles.sh](copyfiles.sh), [linkfiles.sh](linkfiles.sh), [makedockeronec2.sh](makedockeronec2.sh), [makeec2ami.sh](makeec2ami.sh), and [publish_version.sh](publish_version.sh) have been tested on MacOS 11.2.2 only. Ideally these would be rewritten in Python for broader support (contributions are welcome). The other scripts are run remotely on AWS Amazon Linux 2 instances so do not have requirements for your development environment.

## Verify Emails for AWS SES

The Lambda Container uses AWS SES to send emails. If your account is sandboxed, you will have to verify emails before you can send to them. Verification can be performed on specific emails and on entire domains (if you own the domain). To verify an email or domain, go to the **AWS Simple Email Service** dashboard and select "Domains" or "Email Addresses" under "Identity Management". For email verification you will have to click a link in an email sent to that address. For domain verification you will have to modify the domain's DNS entries.

There are two emails that should be modified in [source/app/app.py](source/app/app.py):

- **DEFAULT_FROM_EMAIL**: The email that is the sender for all outgoing emails from the Lambda function (ie. to send the reports)
- **ADMIN_EMAIL**: The administrator's email, that will also receive error reports.

Both of these emails must be verified.

## Initial Setup

Copy the file [settings.template.sh](settings.template.sh) to settings.sh and fill in the following variables in the new file:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SUBNET_ID`
- `SECURITY_GROUP_ID`
- `FUNCTION_ROLE`
- `ANALYZER_BUCKET`
- `KEY_NAME`
- `MAKER_IMAGE_ID`

### `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

You can create an AWS access key ID and secret access key by going to [Your Security Credentials](https://console.aws.amazon.com/iam/home#/security_credentials) in the IAM Dashboard.

### `SUBNET_ID`

This is the subnet ID on which to run your EC2 instances. To get your subnet ID, go to the [VPC Subnets Dashboard](https://console.aws.amazon.com/vpc/home#subnets:) in the AWS console. Select the subnet ID for your preferred availability zone. If you do not know which zone to use, a commonly used default is zone us-east-1a. It should be within the region specified by AWS_DEFAULT_REGION in settings.sh (which you can change). The subnet ID should look like subnet-12345678.

### `SECURITY_GROUP_ID`

This is the AWS security group to launch your EC2 instances with, it should look like sg-1234567890abcdef0. The security group defines which ports are open or closed. It is recommended to open the SSH port (port 22) for incoming traffic and open all ports for outgoing traffic. The SSH port will allow you to SSH into your instances for debugging purposes. To create a security group, from the EC2 Dashboard, go to [Network & Security -> Security Groups](https://console.aws.amazon.com/ec2/v2/home#SecurityGroups:).

### `FUNCTION_ROLE`

Your function role defines which access rights your Lambda Function will have. Function roles can be created in the IAM dashboard at [Access Management -> Roles](https://console.aws.amazon.com/iamv2/home#/roles). The following policies should be attached to this role:

- AmazonS3FullAccess
- AmazonSESFullAccess
- AWSLambdaBasicExecutionRole

The functional role is an ARN and should begin with “arn:aws:iam”


### `ANALYZER_BUCKET`

This is the S3 bucket name (eg. odm-qpcr-analyzer) where all files will be saved. This will include all source code that the container builder accesses, as well as all configuration files, inputs, and outputs from the QPCR Analyzer. A bucket can be created in the [S3 Dashboard](https://s3.console.aws.amazon.com/s3/home), be sure that it is NOT visible to the public.

### `KEY_NAME`

This is the key name used for authentication when you SSH into an instance. A key pair can be created from the EC2 dashboard under [Network & Security -> Key Pairs](https://ca-central-1.console.aws.amazon.com/ec2/v2/home#KeyPairs:).

### `MAKER_IMAGE_ID`

This is the AMI ID used for building the final Lambda function Docker container. The AMI is built by running the script [lambda_container/makeec2ami.sh](makeec2ami.sh). Before running makeec2ami.sh, you can leave this field blank until the AMI ID is available. See the next section for running makeec2ami.sh to retrieve the ID. The ID should look like ami-1234567890abcdef0.


## Creating The Maker

The purpose of the maker is to save a bit of build time when it comes to building the actual Lambda function Docker container. [lambda_container/makeec2ami.sh](makeec2ami.sh) will install packages with yum, install the AWS CLI, and install Docker on an AWS EC2 instance. It then creates the Maker AMI (out of itself) which can then be used in the future for building the Lambda function Docker container. You should first setup and enter all variables listed in [Initial Setup](#Initial_Setup), other than MAKER_IMAGE_ID. Once complete, execute:

    ./makeec2ami.sh

This will launch the EC2 instance and start the building process. The script will output details on how you can monitor progress of the AMI build. Once the AMI image has been made, you can obtain the AMI ID in the EC2 dashboard under [Images -> AMIs](https://console.aws.amazon.com/ec2/v2/home#Images:sort=name). Enter this ID in the settings.sh file of the previous section for MAKER_IMAGE_ID.

## Setting up the Source Files

The Lambda Container needs various files from qpcr_analyzer. To keep things organized, symbolic links are made to all required files in the qpcr_analyzer. To create these links, run:

    ./linkfiles.sh

Ensure that you are running the script from within the lambda_container directory.

## Build the Lambda Function Docker Container

To finally build the Docker container for the Lambda function and publish it, run the [lambda_container/makedockeronec2.sh](https://github.com/martinwellman/odm-qpcr-analyzer/blob/main/lambda_container/makedockeronec2.sh) script with the version alias to use, eg:

    ./makedockeronec2.sh 0.1.5

This script will upload all required files (including source and configuration files) to the S3 bucket specified in ANALYZER_BUCKET (in settings.sh). The script will then launch an instance of the AMI with ID MAKER_IMAGE_ID (in settings.sh). Once the instances has started, the script will output an SSH command that you can use to SSH into the instance, such as:

    ssh -i "odm-qpcr-analyzer-key.pem" \
        ec2-user@ec2-12-345-67-890.compute-1.amazonaws.com

Once logged in, you can view the progress of the build with the following command:

    sudo tail -f /var/log/cloud-init-output.log

Once the Docker container has been built it will be registered with the [AWS Elastic Container Registry](https://console.aws.amazon.com/ecr/repositories) and published to the Lambda Function. You can see your new Lambda Function by selecting it in the [AWS Lambda dashboard](https://console.aws.amazon.com/lambda/home#/functions) and viewing the “Aliases” or “Versions” tab.

In the future, after making changes to the QPCR Analyzer or Lambda Container code, you can increase the version number and run ./makedockeronec2.sh again. Using the same version will overwrite any existing functions with the same version. Overwriting can be performed safely provided that version has not yet been published to production.

## Code Flow

The entry-point of the Lambda function is the `handler()` function in [source/app/app.py](source/app/app.py):

1. handler():
    1. Get settings from the event, and download all input and config files from the S3 bucket (or elsewhere).
    1. Run QPCRUpdater on all input files if remote_target is set. The QPCRUpdater updates master output files on Google Drive or S3. For any files that the updater recognizes, it will update the remote targets. All other files (that the updater doesn't recognize) will be passed on to the extracter.
    1. Run QPCRExtracter to extract all data from the input.
    1. Run QPCRPopulator to create all the output reports.
    1. Run QPCRUpdater again on the QPCRPopulator output (if remote_target is set), to add any new reports to the remote targets.
    1. Create the email with all attachments and send it to the user.
