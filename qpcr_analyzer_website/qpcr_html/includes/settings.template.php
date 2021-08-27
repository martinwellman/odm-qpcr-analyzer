<?php

// Save this file as settings.php and fill in S3_BUCKET, CONTACT_EMAIL, LAMBDA_FUNCTION, LAMBDA_FROM_EMAIL, and AWS_REGION.
// Change other settings if desired.

require_once "users.php";

define('S3_BUCKET',                             "odm-qpcr-analyzer");

// Set ALLOWABLE_EMAILS to [] to allow any email as long as it or its domain has been verified by AWS SES. If ALLOWABLE_EMAILS contains emails and/or domains
// then recipient emails must match in *both* ALLOWABLE_EMAILS and AWS SES. Items without an @ (eg. cryofrog.com) are treated as wildcard domains.
define("ALLOWABLE_EMAILS",                      []);

define('AWS_REGION',                            "us-east-1");
define('S3_INPUTS_ROOT',                        "u/{$USERNAME}/inputs/");

define("ALLOW_POST",                            true);
define("ALLOW_GET",                             true);

define("CONTACT_EMAIL",                         "contact@example.com");

define("UPLOADS_DIR_MAXSIZE",                   2000);   // In MB
define("SESSION_DIR_MAXSIZE",                   500);    // In MB

// Sent to Lambda function
define("LAMBDA_FUNCTION",                       "odm-qpcr-analyzer");
define("LAMBDA_FROM_EMAIL",                     "ODM QPCR Analyzer <odm@example.com>");
define("LAMBDA_SAMPLES",                        "");
define("LAMBDA_SITES_FILE",                     "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/sites.xlsx");
define("LAMBDA_SITES_CONFIG",                   "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/sites.yaml");
define("LAMBDA_EXTRACTER_CONFIG",               "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_extracter_ottawa.yaml");
define("LAMBDA_QAQC_CONFIG",                    "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qaqc_ottawa.yaml");
define("LAMBDA_QAQC_CONFIG_WIDE",               "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qaqc_ottawa_wide_diff.yaml");
define("LAMBDA_QAQC_CONFIG_B117",               "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qaqc_ottawa_b117.yaml");
define("LAMBDA_POPULATOR_CONFIG",               "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_populator_ottawa.yaml");
define("LAMBDA_POPULATOR_CONFIG_WIDE",          "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_populator_ottawa_wide_diff.yaml");
define("LAMBDA_POPULATOR_CONFIG_B117",          "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_populator_ottawa_b117_diff.yaml");
define("LAMBDA_MAPPER_CONFIG",                  "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/biorad_mapper.yaml");
define("LAMBDA_MAPPER_MAP",                     "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/biorad_map.csv");
define("LAMBDA_POPULATOR_TEMPLATE",             "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_template_ottawa.xlsx");
define("LAMBDA_POPULATOR_TEMPLATE_WIDE",        "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_template_ottawa_wide.xlsx");
define("LAMBDA_POPULATOR_TEMPLATE_B117",        "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_template_ottawa_b117.xlsx");
define("LAMBDA_OUTPUT_PATH",                    "s3://".S3_BUCKET."/u/{$USERNAME}/outputs/");
define("LAMBDA_POPULATED_OUTPUT_FILE_ALL",      "Data - All.xlsx");
define("LAMBDA_POPULATED_OUTPUT_FILE_SPLIT",    "Data - {parent_site_title}.xlsx");
define("LAMBDA_REMOTE_TARGET_LONG",             "gd://long/{parent_site_title}/");
define("LAMBDA_REMOTE_TARGET_WIDE",             "gd://{parent_site_title}/");
define("LAMBDA_REMOTE_TARGET_B117",             "gd://B117/{parent_site_title}/");
define("LAMBDA_UPDATER_CONFIG",                 "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_updater.yaml");
define("LAMBDA_UPDATER_CONFIG_B117",            "s3://".S3_BUCKET."/v/".QPCR_VERSION."/config/qpcr_updater_b117.yaml");

define("OUTPUT_FORMATS",                [
    "ottawa_long_format" => [
        "description" => "Ottawa Long Format",
        "populator_config" => LAMBDA_POPULATOR_CONFIG,
        "populator_template" => LAMBDA_POPULATOR_TEMPLATE,
        "qaqc_config" => LAMBDA_QAQC_CONFIG,
        "updater_config" => "",
        "lambda_remote_target" => LAMBDA_REMOTE_TARGET_LONG,
    ],
    "ottawa_wide_format" => [
        "description" => "Ottawa Wide Format",
        "populator_config" => [LAMBDA_POPULATOR_CONFIG, LAMBDA_POPULATOR_CONFIG_WIDE],
        "populator_template" => LAMBDA_POPULATOR_TEMPLATE_WIDE,
        "qaqc_config" => [LAMBDA_QAQC_CONFIG, LAMBDA_QAQC_CONFIG_WIDE],
        "updater_config" => LAMBDA_UPDATER_CONFIG,
        "lambda_remote_target" => LAMBDA_REMOTE_TARGET_WIDE,
    ],
    "ottawa_b117_format" => [
        "description" => "Ottawa B117 Format",
        "populator_config" => [LAMBDA_POPULATOR_CONFIG, LAMBDA_POPULATOR_CONFIG_B117],
        "populator_template" => LAMBDA_POPULATOR_TEMPLATE_B117,
        "qaqc_config" => LAMBDA_QAQC_CONFIG_B117,
        "updater_config" => LAMBDA_UPDATER_CONFIG_B117,
        "lambda_remote_target" => LAMBDA_REMOTE_TARGET_B117,
    ],
]);

?>
