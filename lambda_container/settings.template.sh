#!/bin/bash

# Be sure to fill these out!
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export SUBNET_ID=
export SECURITY_GROUP_ID=
export FUNCTION_ROLE=
export ANALYZER_BUCKET=
# This Image ID should be for the AMI created with makeec2ami.sh
export MAKER_IMAGE_ID=

export AWS_DEFAULT_REGION=us-east-1


export KEY_NAME=odm-qpcr-analyzer-key

# AWS Lambda settings
export FUNCTION_NAME=odm-qpcr-analyzer
export FUNCTION_TIMEOUT=900
# FUNCTION_MEMORY is the AWS Lambda RAM, but it also affects the instance type. More RAM will usually result in a faster instance
# but is also more expensive.
export FUNCTION_MEMORY=2048

# Value to use for all AWS tags, for the "client" key
export CLIENT_VALUE=odm