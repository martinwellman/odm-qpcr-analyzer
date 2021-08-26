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
    QPCR_VERSION="latest"
fi
echo "Copying files for version $QPCR_VERSION"

CONTENTS_DIR="source"
APP_DIR="$CONTENTS_DIR/app"

rm -Rf "$APP_DIR/__pycache__"


pushd "$CONTENTS_DIR"
# Delete existing files on S3
aws s3 rm s3://$ANALYZER_BUCKET/v/$QPCR_VERSION/config --recursive
# Upload config files to s3. Note -regex on Mac doesn't seem to support \(yaml\|xlsx\|csv\), so we split it up with -o (for or)
find . -regex ".*\.yaml" -o -regex ".*\.xlsx" -o -regex ".*\.csv" -o -regex ".*\.json" | xargs -I{} aws s3 cp {} s3://$ANALYZER_BUCKET/v/$QPCR_VERSION/config/
find . -regex ".*email_template.*\.[A-Za-z0-9]*" | xargs -I{} aws s3 cp {} s3://$ANALYZER_BUCKET/v/$QPCR_VERSION/config/
popd
