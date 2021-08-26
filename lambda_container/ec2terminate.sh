#!/bin/bash

if [ -f "settings.sh" ]; then
    source settings.sh
fi
if [ "$AWS_ACCESS_KEY_ID" == "" ]; then
    echo "Settings have not been properly set, ensure that settings.sh has been populated!"
    exit 1
fi

# Terminate us
INSTANCE_ID_URL="http://169.254.169.254/latest/meta-data/instance-id"
INSTANCE_ID=$(wget -q -O - $INSTANCE_ID_URL)
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"
