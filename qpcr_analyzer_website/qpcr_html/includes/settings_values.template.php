<?php

/*
Save this file as settings_values.php and fill in:

    - AWS_KEY
    - AWS_SECRET
    - AWS_REGION
    - S3_BUCKET
    - CONTACT_EMAIL
    - LAMBDA_FROM_EMAIL
    - LAMBDA_FUNCTION
    - LAMBDA_SAMPLES
    - LAMBDA_SITES_FILE

Change other settings if desired.
*/

require_once("includes/recaptcha_values.php");

define("ACCOUNTS_REQUIRE_VERIFICATION",         true);
define("NOTIFY_ADMIN_OF_NEW_ACCOUNTS",          true);

define("SETTINGS", [
    "AWS_KEY" =>                               "<AWS key>",
    "AWS_SECRET" =>                            "<AWS secret key>",
    "AWS_REGION" =>                            "us-east-1",

    "S3_BUCKET" =>                             "<S3 bucket>",

    "UPLOADS_TTL" =>                           60*60,     # In seconds
    "USER_QPCR_VERSION" =>                     "0.2.9",
    "ADMIN_QPCR_VERSION" =>                    "0.2.9",
    
    "QPCR_VERSION" =>                          NULL,      # Ignored: Custom value in get_setting
    "OUTPUT_DEBUG" =>                          NULL,      # Ignored: Custom value in get_setting
    
    "PRIVATE_DATA_ROOT" =>                     dirname(__FILE__) . "/../../qpcr_data/", 

    "GOOGLE_CLIENT_SECRET_FILE" =>             "[PRIVATE_DATA_ROOT]client_secret.json",
    "GOOGLE_DRIVE_SCOPE" =>                    "https://www.googleapis.com/auth/drive",

    // Set ALLOWABLE_EMAILS to [] to allow any email as long as it or its domain has been verified by AWS SES. If ALLOWABLE_EMAILS contains emails and/or domains
    // then recipient emails must match in *both* ALLOWABLE_EMAILS and AWS SES. Items without an @ (eg. cryofrog.com) are treated as wildcard domains.
    "ALLOWABLE_EMAILS" =>                      [],
    "ALLOW_ALL_EMAILS" =>                      true,
    
    "S3_INPUTS_ROOT" =>                        "u/[username]/inputs/",
    
    "CONTACT_EMAIL" =>                         "<Contact email (eg support email)>",
    
    "UPLOADS_DIR_MAXSIZE" =>                   2000,   // In MB
    "SESSION_DIR_MAXSIZE" =>                   500,    // In MB

    "CURRENT_USER_DIR" =>                      "[PRIVATE_DATA_ROOT]u/[username]/", 
    "CURRENT_USER_UPLOADS_ROOT" =>             "[CURRENT_USER_DIR]uploads/",
    
    "CLIENT_SECRET_FILE" =>                    "[PRIVATE_DATA_ROOT]client_secret.json",

    // Sent to Lambda function
    "LAMBDA_FUNCTION" =>                       "<Lambda function name>",
    "LAMBDA_FROM_EMAIL" =>                     "<Send reports from this email address>",
    "LAMBDA_FROM_NAME" =>                      "ODM QPCR Analyzer",
    "LAMBDA_FROM_NAME_AND_EMAIL" =>            "[LAMBDA_FROM_NAME] <[LAMBDA_FROM_EMAIL]>",
    "LAMBDA_SAMPLES" =>                        "<Lambda samples file>",
    "LAMBDA_SITES_FILE" =>                     "<Lambda sites file>",
    "LAMBDA_SITES_CONFIG" =>                   "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/sites.yaml",
    "LAMBDA_EXTRACTER_CONFIG" =>               "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_extracter_ottawa.yaml",
    "LAMBDA_QAQC_CONFIG" =>                    "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qaqc_ottawa.yaml",
    "LAMBDA_QAQC_CONFIG_WIDE" =>               "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qaqc_ottawa_wide_diff.yaml",
    "LAMBDA_QAQC_CONFIG_B117" =>               "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qaqc_ottawa_b117.yaml",
    "LAMBDA_POPULATOR_CONFIG" =>               "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_populator_ottawa.yaml",
    "LAMBDA_POPULATOR_CONFIG_WIDE" =>          "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_populator_ottawa_wide_diff.yaml",
    "LAMBDA_POPULATOR_CONFIG_B117" =>          "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_populator_ottawa_b117_diff.yaml",
    "LAMBDA_MAPPER_CONFIG" =>                  "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/biorad_mapper.yaml",
    "LAMBDA_MAPPER_MAP" =>                     "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/biorad_map.csv",
    "LAMBDA_POPULATOR_TEMPLATE" =>             "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_template_ottawa.xlsx",
    "LAMBDA_POPULATOR_TEMPLATE_WIDE" =>        "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_template_ottawa_wide.xlsx",
    "LAMBDA_POPULATOR_TEMPLATE_B117" =>        "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_template_ottawa_b117.xlsx",
    "LAMBDA_OUTPUT_PATH" =>                    "s3://[S3_BUCKET]/u/[username]/outputs/",
    "LAMBDA_POPULATED_OUTPUT_FILE_ALL" =>      "Data - All - {date} - {time}.xlsx",
    "LAMBDA_POPULATED_OUTPUT_FILE_SPLIT" =>    "Data - {parent_site_title} - {file_id}.xlsx",
    "LAMBDA_REMOTE_TARGET_LONG" =>             NULL,
    "LAMBDA_REMOTE_TARGET_WIDE" =>             "gd://::[gdrive_parent]::/{parent_site_title}/",
    "LAMBDA_REMOTE_TARGET_B117" =>             "gd://::[gdrive_parent]::/B117/{parent_site_title}/",
    "LAMBDA_UPDATER_CONFIG" =>                 "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_updater.yaml",
    "LAMBDA_UPDATER_CONFIG_B117" =>            "s3://[S3_BUCKET]/v/[QPCR_VERSION]/config/qpcr_updater_b117.yaml",
]);

define("OUTPUT_FORMATS",                [
    "ottawa_long_format" => [
        "description" => "Ottawa Long Format",
        "default" => TRUE,
        "populator_config" => "LAMBDA_POPULATOR_CONFIG",
        "populator_template" => "LAMBDA_POPULATOR_TEMPLATE",
        "qaqc_config" => "LAMBDA_QAQC_CONFIG",
        "updater_config" => "",
        "lambda_remote_target" => "LAMBDA_REMOTE_TARGET_LONG",
    ],
    "ottawa_wide_format" => [
        "description" => "Ottawa Wide Format",
        "populator_config" => ["LAMBDA_POPULATOR_CONFIG", "LAMBDA_POPULATOR_CONFIG_WIDE"],
        "populator_template" => "LAMBDA_POPULATOR_TEMPLATE_WIDE",
        "qaqc_config" => ["LAMBDA_QAQC_CONFIG", "LAMBDA_QAQC_CONFIG_WIDE"],
        "updater_config" => "LAMBDA_UPDATER_CONFIG",
        "lambda_remote_target" => "LAMBDA_REMOTE_TARGET_WIDE",
    ],
    "ottawa_b117_format" => [
        "description" => "Ottawa B117 Format",
        "populator_config" => ["LAMBDA_POPULATOR_CONFIG", "LAMBDA_POPULATOR_CONFIG_B117"],
        "populator_template" => "LAMBDA_POPULATOR_TEMPLATE_B117",
        "qaqc_config" => "LAMBDA_QAQC_CONFIG_B117",
        "updater_config" => "LAMBDA_UPDATER_CONFIG_B117",
        "lambda_remote_target" => "LAMBDA_REMOTE_TARGET_B117",
    ],
]);

?>
