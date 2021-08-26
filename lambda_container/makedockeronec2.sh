#!/bin/bash

if [ -f "settings.sh" ]; then
    source settings.sh
fi
if [ "$AWS_ACCESS_KEY_ID" == "" ]; then
    echo "Settings have not been properly set, ensure that settings.sh has been populated!"
    exit 1
fi

QPCR_VERSION=$1
if [ "$QPCR_VERSION" == "" ]; then
    printf "Please specify a version for the Lambda function on the command line, eg:\n"
    printf "     $0 0.1.0\n"
    exit -1
fi
echo "Making version $QPCR_VERSION"

INSTANCE_TYPE=t2.micro
RUN_SCRIPT=ec2makedocker.sh
PUBLISH_SCRIPT=publish_version.sh
TERMINATE_SCRIPT=ec2terminate.sh

TAG_SPECS="ResourceType=instance,Tags=[{Key=client,Value=${CLIENT_VALUE}}]"\ "ResourceType=volume,Tags=[{Key=client,Value=${CLIENT_VALUE}}]"

./copyfiles.sh $QPCR_VERSION

# Copy all source to S3 so the EC2 instance can download it
aws s3 rm s3://$ANALYZER_BUCKET/v/$QPCR_VERSION/source --recursive
aws s3 cp source s3://$ANALYZER_BUCKET/v/$QPCR_VERSION/source --recursive

# Create an EC2 instance
NEW_RUN_SCRIPT="~$RUN_SCRIPT$(date +%F_%H_%M_%S).sh"
touch "$NEW_RUN_SCRIPT"
chmod u+x "$NEW_RUN_SCRIPT"
cat settings.sh >> "$NEW_RUN_SCRIPT"
printf "\n\n" >> "$NEW_RUN_SCRIPT"
printf "QPCR_VERSION="$QPCR_VERSION"" >> "$NEW_RUN_SCRIPT"
printf "\n\n" >> "$NEW_RUN_SCRIPT"
# sed "s/<<QPCR_VERSION>>/$QPCR_VERSION/g" $RUN_SCRIPT >> "$NEW_RUN_SCRIPT"
cat "$RUN_SCRIPT" >> "$NEW_RUN_SCRIPT"
printf "\n\n" >> "$NEW_RUN_SCRIPT"
cat "$PUBLISH_SCRIPT" >> "$NEW_RUN_SCRIPT"
printf "\n\n" >> "$NEW_RUN_SCRIPT"
cat "$TERMINATE_SCRIPT" >> "$NEW_RUN_SCRIPT"
printf "\n\n" >> "$NEW_RUN_SCRIPT"

INSTANCE_ID=$(aws ec2 run-instances --image-id $MAKER_IMAGE_ID --count 1 --instance-type $INSTANCE_TYPE --key-name $KEY_NAME --subnet-id $SUBNET_ID --security-group-ids $SECURITY_GROUP_ID --user-data "file://$NEW_RUN_SCRIPT" --tag-specifications $TAG_SPECS --query "Instances[0].InstanceId")
INSTANCE_ID=$(sed -e 's/^"//' -e 's/"$//' <<< "$INSTANCE_ID")
rm "$NEW_RUN_SCRIPT"

printf "Retrieving public address for instance $INSTANCE_ID..."
while true; do
    PUBLIC_ADDRESS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicDnsName")
    PUBLIC_ADDRESS=$(sed -e 's/^"//' -e 's/"$//' <<< "$PUBLIC_ADDRESS")
    if [ "$PUBLIC_ADDRESS" != "" ]; then
        break
    fi
    printf "."
    sleep 1
done

printf "\n\n"
printf "Making Docker container for ODM QPCR Lambda Function on EC2\n"
printf "The instance will be automatically terminated once complete\n"
printf "Once started (<1 minute), you can SSH into the instance and view the progress with\n"
printf "    ssh -i \"$KEY_NAME.pem\" ec2-user@$PUBLIC_ADDRESS\n"
printf "    sudo tail -f /var/log/cloud-init-output.log\n"
# printf "Don't forget to run './publish_version.sh $QPCR_VERSION' once the Docker container is ready."
