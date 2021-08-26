#!/bin/bash

# set -x

if [ -f "settings.sh" ]; then
    source settings.sh
fi
if [ "$AWS_ACCESS_KEY_ID" == "" ]; then
    echo "Settings have not been properly set, ensure that settings.sh has been populated!"
    exit 1
fi

echo "================================================================================"
echo "Making Lambda function Docker container"

# Make the Docker container image of our ODM QPCR Analyzer that will run on Lambda, push to Amazon ECR, and
# update the Lambda function to use the new image

# QPCR_VERSION must be set externally, either by concatenating it to the start of this script or through an export.
echo "Making version $QPCR_VERSION"

TAGS="Key=client,Value=${CLIENT_VALUE}"
FUNCTION_DESC="ODM QPCR Analyzer"

trim() {
    sed -e 's/^"//' -e 's/"$//' <<< $1
}

cd /home/ec2-user

########################################
# Container build

# Copy all source code/data
aws s3 cp s3://$ANALYZER_BUCKET/v/$QPCR_VERSION/source . --recursive

# Delete unwanted stuff
python3 -c "import pathlib; [p.unlink() for p in pathlib.Path('app').rglob('*.py[co]')]"
python3 -c "import pathlib; [p.rmdir() for p in pathlib.Path('app').rglob('__pycache__')]"

# Build container
sudo service docker start
docker build -t $FUNCTION_NAME .

########################################
# Push to repo and update/create Lambda function

# Create/get the repository
RESULT=$(aws ecr describe-repositories --repository-name $FUNCTION_NAME)
if [ "$?" == "0" ]; then
    IMAGE_URI=$(trim $(jq ".repositories[0].repositoryUri" <<< $RESULT))
else
    echo "Creating repository for $FUNCTION_NAME"
    RESULT=$(aws ecr create-repository --repository-name $FUNCTION_NAME --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE --tags $TAGS)
    IMAGE_URI=$(trim $(jq ".repository.repositoryUri" <<< $RESULT))
fi
REPO_URI=$(dirname $IMAGE_URI)
echo "Repository: $REPO_URI"
echo "Repository image: $IMAGE_URI"

# Push the image
aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $REPO_URI
docker rm -f $IMAGE_URI:$QPCR_VERSION
docker tag $FUNCTION_NAME $IMAGE_URI:$QPCR_VERSION
docker push $IMAGE_URI:$QPCR_VERSION

# Update the Lambda function to use the new image
aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $IMAGE_URI:$QPCR_VERSION
if [ "$?" != "0" ]; then
    echo "Creating new Lambda Function"
    aws lambda create-function --function-name $FUNCTION_NAME --package-type=Image --code ImageUri=$IMAGE_URI:$QPCR_VERSION --role $FUNCTION_ROLE --description "$FUNCTION_DESC" --timeout $FUNCTION_TIMEOUT --memory-size $FUNCTION_MEMORY --tags $TAGS
fi

