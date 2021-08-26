#!/bin/bash

if [ -f "settings.sh" ]; then
    source settings.sh
fi
if [ "$AWS_ACCESS_KEY_ID" == "" ]; then
    echo "Settings have not been properly set, ensure that settings.sh has been populated!"
    exit 1
fi

if [ "$1" != "" ]; then
    QPCR_VERSION=$1
fi
if [ "$QPCR_VERSION" == "" ]; then
    printf "Please specify a version for the Lambda function on the command line, eg:\n"
    printf "     $0 0.1.0\n"
    exit -1
fi

echo "================================================================================"
echo "Publishing version $QPCR_VERSION"


trim() {
    sed -e 's/^"//' -e 's/"$//' <<< $1
}

ALIAS_NAME=$(sed -e "s/[^A-Za-z0-9_-]/_/g" <<< $QPCR_VERSION)

PREV_ALIAS_RESULT=$(aws lambda get-alias --function-name $FUNCTION_NAME --name $ALIAS_NAME 2> /dev/null)
PREV_ALIAS_VERSION=$(trim $(jq ".FunctionVersion" <<< $PREV_ALIAS_RESULT))

echo "Deleting existing alias '$ALIAS_NAME'"
aws lambda delete-alias --function-name $FUNCTION_NAME --name $ALIAS_NAME 2> /dev/null

if [ "$PREV_ALIAS_VERSION" != "" ]; then
    # Will fail if other aliases are attached to the version
    echo "Deleting version ('$PREV_ALIAS_VERSION') that previously had the alias '$ALIAS_NAME'"
    aws lambda delete-function --function-name $FUNCTION_NAME --qualifier $PREV_ALIAS_VERSION
fi

printf "Waiting for Lambda function update to complete and publishing new version..."
while true; do
    PUBLISH_RESULT=$(aws lambda publish-version --function-name $FUNCTION_NAME 2> /dev/null)
    if [ "$?" == "0" ]; then
        break
    fi
    printf "."
    sleep 2
done
printf "\n"
PUBLISH_VERSION=$(trim $(jq ".Version" <<< $PUBLISH_RESULT))

echo "Creating function alias '$ALIAS_NAME'"
aws lambda create-alias --function-name $FUNCTION_NAME --name $ALIAS_NAME --function-version $PUBLISH_VERSION

echo "Finished publishing function!"
