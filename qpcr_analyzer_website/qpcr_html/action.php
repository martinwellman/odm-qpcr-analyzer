<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/utils.php";
require 'vendor/autoload.php';
require_once "includes/settings.php";

use Aws\S3\S3Client;
use Aws\Lambda\LambdaClient;
use Aws\Ses\SesClient;

verify_requested_with();
safe_session_start();
$username = $_SESSION["username"];

function handle_uploads() {
    /**
     * Handle BioRad file uploads.
     * 
     * Save all files in $_FILES to disk, but don't send to S3 yet.
     */
    global $sid, $data_dir;
    
    if (!isset($_FILES["file"])) {
        die(json_encode(["error" => "No files specified"]));
        // print("No files uploaded!\n");
        // return;
    }

    if (!is_dir($data_dir)) {
        @mkdir($data_dir, 0777, $recursive=true);
    }

    $uploads_dir_size = dir_size(get_setting("CURRENT_USER_UPLOADS_ROOT")) / (1024*1024);
    $session_dir_size = dir_size($data_dir) / (1024*1024);

    $files = [$_FILES["file"]];
    $num_files = count($files);

    for ($i=0; $i<$num_files; $i++) {
        $curfile = $files[$i];
        if (isset($curfile["name"]) && $curfile["name"] != "") {
            $file_name = $data_dir . clean_name($curfile["name"]);
            $tmp_name = $curfile["tmp_name"];

            $cur_size = filesize($tmp_name) / (1024*1024);
            $new_session_size = $session_dir_size + $cur_size;
            $new_uploads_size = $uploads_dir_size + $cur_size;

            // Make sure we won't exceed our disk quota
            $session_dir_maxsize = get_setting("SESSION_DIR_MAXSIZE");
            $uploads_dir_maxsize = get_setting("UPLOADS_DIR_MAXSIZE");
            if ($new_session_size > $session_dir_maxsize || $new_uploads_size > $uploads_dir_maxsize) {
                $max_size = $new_session_size > $session_dir_maxsize ? 
                    $session_dir_maxsize : 
                    $uploads_dir_maxsize;
                $msg = $new_session_size > $session_dir_maxsize ?
                    "You have reached the maximum total upload size of" :
                    "The server has reached the maximum capacity of";
                die(json_encode([
                    "error" => $msg . " " . $session_dir_maxsize . " MB. No more files can be uploaded. Please contact " . get_setting("CONTACT_EMAIL") . " if you require assistance.",
                    "short_error" => "Disk Space Error",
                    "full_abort" => true
                ]));
            }

            move_uploaded_file($tmp_name, $file_name);
        }
    }
}

function delete_old_data() {
    /**
     * Delete any data on the web server for the current user that is older than the UPLOADS_TTL (other than for the current session)
     */
    global $sid;

    if (is_dir(get_setting("CURRENT_USER_UPLOADS_ROOT"))) {
        $all_dirs = array_diff(scandir(get_setting("CURRENT_USER_UPLOADS_ROOT")), array(".", ".."));
        foreach ($all_dirs as $dir) {
            if ($dir == $sid)
                continue;
            delete_data_with_sid($dir, get_setting("UPLOADS_TTL"));
        }
    }
}

function delete_data_with_sid($dataid, $ttl=NULL) {
    /**
     * Delete the data for the session ID $dataid, for the current user.
     */
    $path = get_setting("CURRENT_USER_UPLOADS_ROOT") . $dataid;
    if (is_dir($path)) {
        $age = time() - filemtime($path);
        if ($ttl === NULL || $age > $ttl) {
            $all_files = array_diff(scandir($path), array(".", ".."));
            foreach ($all_files as $file) {
                unlink($path . DIRECTORY_SEPARATOR . $file);
            }
            rmdir($path);
        }
    }
}

function delete_current_data() {
    /**
     * Delete all the data (uploads) for the current session.
     */
    global $data_dir;
    if (is_dir($data_dir)) {
        $all_files = array_diff(scandir($data_dir), array(".", ".."));
        foreach ($all_files as $file) {
            $cur_file = $data_dir . $file;
            if (is_file($cur_file)) {
                unlink($cur_file);
            }
        }
        rmdir($data_dir);
    }
}

function upload_file($file) {
    /**
     * Upload a file to the S3 bucket.
     * 
     * Parameters
     * ----------
     * $file : str
     *      The local file to upload.
     * 
     * Returns
     * -------
     * The path to the file on S3.
     */
    global $sid;

    $s3 = new S3Client(get_aws_creds());

    $key = basename($file);
    $key = get_setting("S3_INPUTS_ROOT") . $sid . "/" . $key;

    $result = $s3->putObject([
        "Bucket" => get_setting("S3_BUCKET"),
        "Key" => $key,
        "SourceFile" => $file
    ]);

    return "s3://" . get_setting("S3_BUCKET") . "/" . $key;
}

function get_domain($email) {
    /**
     * Retrieve the domain (eg. cryofrog.com) of an email address.
     */
    $comps = explode("@", $email);
    if (count($comps) != 2)
        return NULL;
    return $comps[1];
}

function verify_emails($emails, $die_if_unverified=False) {
    /**
     * Ensure that all the specified emails have been verified for use with AWS SES. Split off the unverified emails
     * from the array and return separate arrays of verified and unverified emails.
     * 
     * Parameters
     * ----------
     * $emails : array
     *      Array of all emails to verify.
     * $die_if_unverified : bool
     *      If True then die (terminate the script) if there is an unverified email in $emails.
     * 
     * Returns
     * -------
     * Associative array containing the keys "verified" and "unverified". Both values are arrays of verified and
     * unverified emails from the original $emails list.
     */
    $identities = [];
    foreach ($emails as $email) {
        array_push($identities, $email);
        // Add the domain, so we can retrieve domain verification status as well as email verification status
        $domain = get_domain($email);
        if ($domain)
            array_push($identities, $domain);
    }

    if (get_setting("ALLOW_ALL_EMAILS"))
        return [
            "verified" => $emails,
            "unverified" => []
        ];

    $ses = new SesClient(get_aws_creds());
    $result = $ses->getIdentityVerificationAttributes([
        "Identities" => $identities
    ]);

    $attrs = $result["VerificationAttributes"];
    $verified = [];
    $unverified = [];

    // Go through each email, determine if it (or its domain) is verified.
    // Add verified emails to $verified, and unverified emails to $unverified
    foreach ($emails as $email) {
        $entry = NULL;
        $domain = get_domain($email);

        $allowable_emails = get_setting("ALLOWABLE_EMAILS");
        if ($allowable_emails && count($allowable_emails) > 0) {
            if (!in_array($email, $allowable_emails) && !in_array($domain, $allowable_emails)) {
                array_push($unverified, $email);
                continue;
            }
        }

        if (isset($attrs[$email]))
            $entry = $attrs[$email];
        elseif (isset($attrs[$domain]))
            $entry = $attrs[$domain];

        if ($entry) {
            $status = $entry["VerificationStatus"];
            if ($status == "Success") {
                array_push($verified, $email);
                continue;
            }
        }

        array_push($unverified, $email);
    }

    if ($die_if_unverified) {
        if (count($unverified) > 0) {
            $message = "The analyzer was not started because the following email addresses have not been verified:\n\n";
            $message = $message . make_bullet_list($unverified);
            $message = $message . "\n\nPlease remove the unverified addresses from the list of recipients, or contact " . get_setting("CONTACT_EMAIL") . " to get them verified.";
            die(json_encode(["error" => $message]));
        }
    }

    return [
        "verified" => $verified,
        "unverified" => $unverified
    ];
}

function run_analyzer() {
    /**
     * Run the Lambda function with the currently uploaded files and settings.
     */
    global $data_dir, $sid;

    $tokens = json_decode(get_user_data(get_loggedin_user(), "google_tokens"));

    $to_emails = get_param("to_emails");
    if (!$to_emails || count($to_emails) == 0) {
        die(json_encode(["error" => "Please enter at least one email address to receive the generated report."]));
    }
    $to_emails = verify_emails($to_emails, $die_if_unverified=true)["verified"];

    $files = get_param("files");
    if (!is_dir($data_dir) || !$files || count($files) == 0) {
        die(json_encode(["error" => "You must upload at least one file before starting the analyzer."]));
    }
    for ($i=0; $i<count($files); $i++) {
        $files[$i] = clean_name($files[$i]);
    }
    
    $update_remote = filter_var(get_param("update_remote"), FILTER_VALIDATE_BOOLEAN);
    $split_by_site = filter_var(get_param("split_by_site"), FILTER_VALIDATE_BOOLEAN);
    $output_format = get_param("output_format");
    $output_format_description = OUTPUT_FORMATS[$output_format]["description"];

    $parent_drive_folder = get_user_data(get_loggedin_user(), "gdrive_parent");
    if (!$parent_drive_folder)
        $parent_drive_folder = "";
    $parent_drive_folder = trim($parent_drive_folder);

    if ($update_remote && $parent_drive_folder == "") {
        die(json_encode(["error" => "You must specify a Google Drive folder to save to when \"Update on Google Drive\" is selected."]));
    }

    // Upload all files in $data_dir
    $all_files = array_diff(scandir($data_dir), array(".", ".."));
    $uploaded_files = [];
    $uploaded_file_names = [];
    foreach ($all_files as $file) {
        if (!in_array($file, $files)) {
            continue;
        }
        $path = $data_dir . $file;
        if (is_file($path)) {
            $s3_file = upload_file($path);
            array_push($uploaded_files, $s3_file);
            array_push($uploaded_file_names, $file);
        }
    }
    delete_current_data();

    $userInfo = json_decode(get_user_data(get_loggedin_user(), "google_userinfo"));
    $descriptive_settings = [
        "User: " . get_loggedin_user(),
        "Split by site: " . ($split_by_site ? "Yes" : "No"),
        "Output format: {$output_format_description}",
        "Update on Google Drive: " . ($update_remote ? "Yes ({$userInfo->email})" : "No"),
        "Parent Google Drive folder: " . ($update_remote ? $parent_drive_folder : "Not Used"),
        "Session ID: " . $sid,
        "Lambda version: " . get_setting("QPCR_VERSION"),
    ];

    $lambda = new LambdaClient(get_aws_creds());

    $function_name = get_setting("LAMBDA_FUNCTION") . ":" . preg_replace("/[^A-Za-z0-9_-]/", "_", get_setting("QPCR_VERSION"));

    // $function_name = get_setting("LAMBDA_FUNCTION");
    $result = $lambda->invoke([
        "FunctionName" => $function_name,
        "InvocationType" => "Event",
        
        "Payload" => json_encode([
            "inputs" => $uploaded_files,
            "from_email" => get_setting("LAMBDA_FROM_NAME_AND_EMAIL"),
            "to_emails" => $to_emails,
            "username" => get_loggedin_user(),
            "samples" => get_setting("LAMBDA_SAMPLES"),
            "sites_file" => get_setting("LAMBDA_SITES_FILE"),
            "sites_config" => get_setting("LAMBDA_SITES_CONFIG"),
            "extracter_config" => get_setting("LAMBDA_EXTRACTER_CONFIG"),
            "output_format" => $output_format,
            "output_format_description" => $output_format_description,
            "qaqc_config" => get_setting(OUTPUT_FORMATS[$output_format]["qaqc_config"]),
            "populator_config" => get_setting(OUTPUT_FORMATS[$output_format]["populator_config"]),
            "updater_config" => get_setting(OUTPUT_FORMATS[$output_format]["updater_config"]),
            "mapper_config" => get_setting("LAMBDA_MAPPER_CONFIG"),
            "mapper_map" => get_setting("LAMBDA_MAPPER_MAP"),
            "populator_template" => get_setting(OUTPUT_FORMATS[$output_format]["populator_template"]),
            "output_path" => get_setting("LAMBDA_OUTPUT_PATH"),
            "split_by_site" => $split_by_site,
            "tokens" => $tokens ? json_encode($tokens) : "",
            "remote_target" => $update_remote ? get_setting(OUTPUT_FORMATS[$output_format]["lambda_remote_target"]) : "",
            "populated_output_file" => $split_by_site ? get_setting("LAMBDA_POPULATED_OUTPUT_FILE_SPLIT") : get_setting("LAMBDA_POPULATED_OUTPUT_FILE_ALL"),
            "descriptive_settings" => $descriptive_settings,
            "parent_drive_folder" => $parent_drive_folder,
            "hide_qaqc" => false,
            "output_debug" => get_setting("OUTPUT_DEBUG"),
        ])
        ]);
        
    $recipients = make_bullet_list($to_emails);
    if ($recipients) {
        $recipients = " The following recipients will receive the report:\n\n" . $recipients;
    }
    // $files_msg = make_bullet_list($uploaded_file_names);
    // if ($files_msg) {
    //     $files_msg = "\n\nThe following files have been uploaded:\n\n" . $files_msg;
    // }
    die(json_encode(["message" => "Analyzer started." . $recipients]));
}

function make_bullet_list($list) {
    /**
     * Convert an array of text elements into a pretty test list with bullets.
     */
    $txt = "";
    for ($i=0; $i<count($list); $i++) {
        if ($txt)
            $txt = $txt . "\n";
        $txt = $txt . "    • " . $list[$i];
    }
    return $txt;
}

function drive_revoke() {
    $tokens = json_decode(get_user_data(NULL, "google_tokens"));
    $token = $tokens->token;
    $refresh_token = $tokens->refresh_token;

    $client = google_drive_client();
    $client->revokeToken($token);
    $client->revokeToken($refresh_token);

    update_user(get_loggedin_user(), [
        "google_tokens" => NULL,
        "google_userinfo" => NULL
    ]);
}

function google_drive_client() {
    $client = new Google\Client();
    $client->setAuthConfig(get_setting("GOOGLE_CLIENT_SECRET_FILE"));
    // $client->setScopes([get_setting("GOOGLE_DRIVE_SCOPE"), "profile", "email"]);
    // $client->setRedirectUri(get_protocol_and_domain());
    return $client;
}

function drive_register() {
    // $authCode = file_get_contents("php://input");
    $authCode = get_param("authCode");

    # Exchange auth code for access token and refresh token
    $client = new Google\Client();
    $client->setAuthConfig(get_setting("GOOGLE_CLIENT_SECRET_FILE"));
    $client->setScopes([get_setting("GOOGLE_DRIVE_SCOPE"), "profile", "email"]);
    $client->setRedirectUri(get_protocol_and_domain());
    $creds = $client->fetchAccessTokenWithAuthCode($authCode);
    
    if (!$creds) {
        die(json_encode(["error" => "Could not retrieve credentials."]));
    }
    
    if (!isset($creds["access_token"]) || !isset($creds["refresh_token"])) {
        die(json_encode(["error" => "Could not retrieve access and refresh tokens."]));
    }
    
    if (!isset($creds["scope"])) {
        die(json_encode(["error" => "No access provided by user."]));
    }
    
    $scopes = explode(" ", $creds["scope"]);
    if (!in_array(get_setting("GOOGLE_DRIVE_SCOPE"), $scopes)) {
        die(json_encode(["error" => "You must allow access to Google Drive. Please try again and be sure to select the checkbox next to 'See, edit, create, and delete all of your Google Drive files'."]));
    }
    
    $tokens = [
        "token" => $creds["access_token"],
        "refresh_token" => $creds["refresh_token"],
        "scopes" => $scopes,
        "expiry" => gmdate("Y-m-d\TH:i:s\Z", $creds["created"] + $creds["expires_in"]),
    ];
    
    # Get and save user info (email, name, etc)
    $service = new Google\Service\Oauth2($client);
    $userInfo = $service->userinfo->get();
    $userInfo = [
        "email" => isset($userInfo["email"]) ? $userInfo["email"] : NULL,
        "name" => isset($userInfo["name"]) ? $userInfo["name"] : NULL,
        "picture" => isset($userInfo["picture"]) ? $userInfo["picture"] : NULL
    ];

    update_user(get_loggedin_user(), [
        "google_tokens" => json_encode($tokens),
        "google_userinfo" => json_encode($userInfo)
    ]);
    
    die(json_encode([
        "email" => $userInfo["email"],
        "name" => $userInfo["name"],
        "picture" => $userInfo["picture"],
    ]));    
}

$sid = clean_name(get_param("sid"));
if (!$sid) {
    die("Error: No Session ID");
}

$data_dir = get_setting("CURRENT_USER_UPLOADS_ROOT") . $sid . DIRECTORY_SEPARATOR;

$action = get_param("action");
if (!$action) {
    die("Error: No Action");
}

verify_recaptcha($action, true);

if ($action == ACTION_QPCR_UPLOAD_FILE) {
    assert_logged_in_and_verified();
    delete_old_data();
    handle_uploads();
} elseif ($action == ACTION_QPCR_RUN_ANALYZER) {
    assert_logged_in_and_verified();
    run_analyzer();
} elseif ($action == ACTION_QPCR_DELETE_CURRENT_DATA) {
    assert_logged_in_and_verified();
    delete_current_data();
} elseif ($action == ACTION_QPCR_UPDATE_GOOGLE_DRIVE_PARENT) {
    assert_logged_in_and_verified();
    $parent = get_param("parent");
    update_user(get_loggedin_user(), [
        "gdrive_parent" => $parent
    ]);
} elseif ($action == ACTION_QPCR_UPDATE_DEFAULT_RECIPIENTS) {
    assert_logged_in_and_verified();
    $recipients = get_param("recipients");
    update_user(get_loggedin_user(), [
        "default_recipients" => is_array($recipients) ? implode(",", $recipients) : NULL
    ]);
} elseif ($action == ACTION_QPCR_DRIVE_REGISTER) {
    assert_logged_in_and_verified();
    drive_register();
} elseif ($action == ACTION_QPCR_CLEAR_GOOGLE_DRIVE) {
    assert_logged_in_and_verified();
    drive_revoke();
} else {
    die("Error: Unrecognized action " . $action);
}

die(json_encode(["success" => 1]));

?>


