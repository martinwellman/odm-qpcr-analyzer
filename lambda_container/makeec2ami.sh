#!/bin/bash

if [ -f "settings.sh" ]; then
    source settings.sh
fi
if [ "$AWS_ACCESS_KEY_ID" == "" ]; then
    echo "Settings have not been properly set, ensure that settings.sh has been populated!"
    exit 1
fi

# "Amazon Linux 2 AMI (HVM), SSD Volume Type (64-bit x86)" in us-east-1
# IMAGE_ID=ami-0dc2d3e4c0f9ebd18
# "Amazon Linux 2 AMI (HVM) - Kernel 5.10, SSD Volume Type" in ca-central-1
IMAGE_ID=ami-0843f7c45354d48b5
INSTANCE_TYPE=t2.micro
RUN_SCRIPT=ec2amisetup.sh

NEW_RUN_SCRIPT="~$RUN_SCRIPT$(date +%F_%H_%M_%S).sh"
cp settings.sh "$NEW_RUN_SCRIPT"
printf "\n\n" >> "$NEW_RUN_SCRIPT"
cat $RUN_SCRIPT >> "$NEW_RUN_SCRIPT"

TAG_SPECS="ResourceType=instance,Tags=[{Key=client,Value=${CLIENT_VALUE}}]"\ "ResourceType=volume,Tags=[{Key=client,Value=${CLIENT_VALUE}}]"

INSTANCE_ID=$(aws ec2 run-instances --image-id $IMAGE_ID --count 1 --instance-type $INSTANCE_TYPE --key-name $KEY_NAME --subnet-id $SUBNET_ID --security-group-ids $SECURITY_GROUP_ID --user-data "file://$NEW_RUN_SCRIPT" --query "Instances[0].InstanceId" --tag-specifications $TAG_SPECS)
rm "$NEW_RUN_SCRIPT"
INSTANCE_ID=$(sed -e 's/^"//' -e 's/"$//' <<< "$INSTANCE_ID")

printf "Retrieving public address for instance $INSTANCE_ID..."
while true; do
    PUBLIC_ADDRESS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicDnsName")
    PUBLIC_ADDRESS=$(sed -e 's/^"//' -e 's/"$//' <<< "$PUBLIC_ADDRESS")
    if [ "$PUBLIC_ADDRESS" != "" ]; then
        break
    fi
    printf "."
    sleep 2
done

echo "Instance ID: $INSTANCE_ID"
echo "Public Address: $PUBLIC_ADDRESS"

printf "Making AMI for Docker container builder.\n"
printf "The instance will be automatically terminated once complete\n"
printf "Once started (<1 minute), you can SSH into the instance and view the progress with\n"
printf "    ssh -i \"$KEY_NAME.pem\" ec2-user@$PUBLIC_ADDRESS\n"
printf "    sudo tail -f /var/log/cloud-init-output.log\n"