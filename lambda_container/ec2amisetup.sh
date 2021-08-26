#!/bin/bash

if [ -f "settings.sh" ]; then
    source settings.sh
fi
if [ "$AWS_ACCESS_KEY_ID" == "" ]; then
    echo "Settings have not been properly set, ensure that settings.sh has been populated!"
    exit 1
fi

# Create the AMI that creates the Lambda docker image. Rather than creating the Lambda docker image from
# scratch each time, we do some preliminary installation/setup and save it as an AMI, so that when we create
# the Docker image we can save time.

TAG_SPECS="ResourceType=image,Tags=[{Key=client,Value=${CLIENT_VALUE}}]"\ "ResourceType=snapshot,Tags=[{Key=client,Value=${CLIENT_VALUE}}]"
AMI_NAME="odm-qpcr-analyzer-docker-builder-$(date +'%Y-%m-%d_%H-%M-%S')"
AMI_DESC="Creates the ODM QPCR Analyzer image and deploys it to the Lambda function."

INSTANCE_ID_URL="http://169.254.169.254/latest/meta-data/instance-id"
INSTANCE_ID=$(wget -q -O - $INSTANCE_ID_URL)
HOME=/home/ec2-user
AMI_ID_FILE="$HOME/amiid.txt"
INSTANCE_ID_FILE="$HOME/instanceid.txt"

cd $HOME

# If we're the instance that creates the AMI image then wait until the AMI is complete then terminate.
# We start image creation at the end of this script, which will cause the instance to reboot. If the
# INSTANCE_ID_FILE and AMI_ID_FILEs have been created (see below), then it means we have already 
# initiated image creation and just need to wait for it to finish.
if [ -f "$INSTANCE_ID_FILE" ]; then
    SETUP_INSTANCE_ID=$(cat $INSTANCE_ID_FILE)
    AMI_ID=$(cat $AMI_ID_FILE)
    if [ "$SETUP_INSTANCE_ID" == "$INSTANCE_ID" ]; then
        echo "Waiting for AMI $AMI_ID to finish building"
        aws ec2 wait image-available --image-ids $AMI_ID

        # Terminate us
        echo "Terminating..."
        aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"
    fi

    exit 0
fi

cd $HOME

echo "Installing with yum..."

sudo yum update -y
sudo yum install -y jq
sudo yum install -y git
sudo yum install -y openssl-devel
# sudo yum groupinstall -y "Development Tools"

# Install pyenv
# curl https://pyenv.run | bash
# echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
# echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
# echo 'eval "$(pyenv init --path)"' >> ~/.profile
# echo 'eval "$(pyenv init -)"' >> ~/.bashrc
# echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
# source ~/.profile

# Install Python3.8
# pyenv install 3.8.7
# pyenv global 3.8.7

echo "Upgrading AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install --bin-dir /usr/bin --install-dir /usr/local/aws-cli --update

echo "Installing Docker..."
sudo amazon-linux-extras install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user
sudo docker info

sudo rm -Rf /var/lib/cloud/instances/$INSTANCE_ID

echo "Creating EC2 image of ourself..."
AMI_ID=$(aws ec2 create-image --instance-id "$INSTANCE_ID" --name "$AMI_NAME" --description "$AMI_DESC" --tag-specifications $TAG_SPECS)
AMI_ID=$(jq '.ImageId' <<< $AMI_ID)
AMI_ID=$(sed -e 's/^"//' -e 's/"$//' <<< $AMI_ID)

echo $AMI_ID > $AMI_ID_FILE
echo $INSTANCE_ID > $INSTANCE_ID_FILE

echo "Successfully started creation of AMI with the following details:"
echo "AMI Name:        $AMI_NAME"
echo "AMI Description: $AMI_DESC"
echo "AMI ID:          $AMI_ID"

echo ""
echo "Preparing AMI '$AMI_ID' for ODM QPCR Analyzer Docker building."

