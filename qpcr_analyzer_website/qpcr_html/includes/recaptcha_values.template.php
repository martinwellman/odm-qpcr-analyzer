<?php

/*
Save this file as recaptcha_values.php and fill in:

    - RECAPTCHA_V3_SECRET_KEY
    - RECAPTCHA_V3_SITE_KEY

Change other settings if desired.
*/

define("USE_RECAPTCHA",                             true);
define("RECAPTCHA_V3_SECRET_KEY",                   "<Recaptcha v3 secret key>");
define("RECAPTCHA_V3_SITE_KEY",                     "<Recaptcha v3 site key>");
define("RECAPTCHA_URL",                             "https://www.google.com/recaptcha/api/siteverify");
define("DEFAULT_RECAPTCHA_THRESHOLD",               0.5);

define("ACTION_LOGIN",                              "login");
define("ACTION_REGISTER",                           "register");
define("ACTION_VERIFY_ACCOUNT",                     "verify_account");
define("ACTION_NEW_PASSWORD",                       "new_password");
define("ACTION_RESET_PASSWORD",                     "reset_password");
define("ACTION_QPCR_UPLOAD_FILE",                   "qpcr_upload_file");
define("ACTION_QPCR_RUN_ANALYZER",                  "qpcr_run_analyzer");
define("ACTION_QPCR_DELETE_CURRENT_DATA",           "qpcr_delete_current_data");
define("ACTION_QPCR_UPDATE_GOOGLE_DRIVE_PARENT",    "qpcr_update_google_drive_parent");
define("ACTION_QPCR_UPDATE_DEFAULT_RECIPIENTS",     "qpcr_update_default_recipients");
define("ACTION_QPCR_DRIVE_REGISTER",                "qpcr_drive_register");
define("ACTION_QPCR_CLEAR_GOOGLE_DRIVE",            "qpcr_clear_google_drive");

// Recaptcha settings for each available action. If an action or a particular setting is not available, then the constants
// USE_RECAPTCHA and DEFAULT_RECAPTCHA_THRESHOLD are used.
//  "USE_RECAPTCHA" => true | false: If true then this action requires reCAPTCHA, otherwise we do not use reCAPTCHA for it.
//  "RECAPTCHA_THRESHOLD" => float [0..1]: Recaptcha score threshold for a successful reCAPTCHA.
define("RECAPTCHA_SETTINGS",                    [
    // General operations
    ACTION_LOGIN => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_REGISTER => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_VERIFY_ACCOUNT => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_NEW_PASSWORD => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_RESET_PASSWORD => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],

    // QPCR Actions
    ACTION_QPCR_UPLOAD_FILE => [
        "USE_RECAPTCHA" => false, // **IMPORTANT: reCAPTCHA not supported for uploads. This should always be false!!!
    ],
    ACTION_QPCR_RUN_ANALYZER => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_QPCR_DELETE_CURRENT_DATA => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_QPCR_UPDATE_GOOGLE_DRIVE_PARENT => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_QPCR_UPDATE_DEFAULT_RECIPIENTS => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_QPCR_DRIVE_REGISTER => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
    ACTION_QPCR_CLEAR_GOOGLE_DRIVE => [
        "USE_RECAPTCHA" => true,
        "RECAPTCHA_THRESHOLD" => DEFAULT_RECAPTCHA_THRESHOLD,
    ],
]);

?>
