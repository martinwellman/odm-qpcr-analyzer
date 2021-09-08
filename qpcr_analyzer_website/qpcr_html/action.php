<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require 'vendor/autoload.php';
require_once "includes/settings.php";
require_once "includes/users.php";
require_once "includes/awscreds.php";

use Aws\S3\S3Client;
use Aws\Lambda\LambdaClient;
use Aws\Ses\SesClient;

function clean_name($str) {
    return preg_replace("/[^A-Za-z0-9_\\.\\- ]/i", "_", $str);
}

function get_param($key) {
    if (ALLOW_POST && isset($_POST) && isset($_POST[$key]))
        return $_POST[$key];
    if (ALLOW_GET && isset($_GET) && isset($_GET[$key]))
        return $_GET[$key];
}

function dir_size($dir) {
    $size = 0;
    $files = glob(rtrim($dir, "/") . "/*");
    foreach ($files as $file) {
        if (is_file($file)) $size += filesize($file);;
        if (is_dir($file)) $size += dir_size($file);
    }
    return $size;
}

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

    $uploads_dir_size = dir_size(UPLOADS_ROOT) / (1024*1024);
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
            if ($new_session_size > SESSION_DIR_MAXSIZE || $new_uploads_size > UPLOADS_DIR_MAXSIZE) {
                $max_size = $new_session_size > SESSION_DIR_MAXSIZE ? 
                    SESSION_DIR_MAXSIZE : 
                    UPLOADS_DIR_MAXSIZE;
                $msg = $new_session_size > SESSION_DIR_MAXSIZE ?
                    "You have reached the maximum total upload size of" :
                    "The server has reached the maximum capacity of";
                die(json_encode([
                    "error" => $msg . " " . SESSION_DIR_MAXSIZE . " MB. No more files can be uploaded. Please contact " . CONTACT_EMAIL . " if you require assistance.",
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

    if (is_dir(UPLOADS_ROOT)) {
        $all_dirs = array_diff(scandir(UPLOADS_ROOT), array(".", ".."));
        foreach ($all_dirs as $dir) {
            if ($dir == $sid)
                continue;
            delete_data_with_sid($dir, UPLOADS_TTL);
        }
    }
}

function delete_data_with_sid($dataid, $ttl=NULL) {
    /**
     * Delete the data for the session ID $dataid, for the current user.
     */
    $path = UPLOADS_ROOT . $dataid;
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
    $all_files = array_diff(scandir($data_dir), array(".", ".."));
    foreach ($all_files as $file) {
        $cur_file = $data_dir . $file;
        if (is_file($cur_file)) {
            unlink($cur_file);
        }
    }
    rmdir($data_dir);
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

    $s3 = new S3Client([
        "region" => AWS_REGION,
        "version" => "latest",
        "credentials" => [
            "key" => AWS_KEY,
            "secret" => AWS_SECRET
        ]
    ]);

    $key = basename($file);
    $key = S3_INPUTS_ROOT . $sid . "/" . $key;

    $result = $s3->putObject([
        "Bucket" => S3_BUCKET,
        "Key" => $key,
        "SourceFile" => $file
    ]);

    return "s3://" . S3_BUCKET . "/" . $key;
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
        // Add the domain
        $domain = get_domain($email);
        if ($domain)
            array_push($identities, $domain);
    }

    $ses = new SesClient([
        "region" => AWS_REGION,
        "version" => "latest",
        "credentials" => [
            "key" => AWS_KEY,
            "secret" => AWS_SECRET
        ]
    ]);
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

        if (ALLOWABLE_EMAILS && count(ALLOWABLE_EMAILS) > 0) {
            if (!in_array($email, ALLOWABLE_EMAILS) && !in_array($domain, ALLOWABLE_EMAILS)) {
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
            $message = $message . "\n\nPlease remove the unverified addresses from the list of recipients, or contact " . CONTACT_EMAIL . " to get them verified.";
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
    global $data_dir, $USERNAME;

    $tokens = get_saved_tokens();

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

    $parent_drive_folder = get_setting("drive.parent");
    if (!$parent_drive_folder) $parent_drive_folder = "";
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

    $userInfo = get_gdrive_user_info();
    $descriptive_settings = [
        "User: " . $USERNAME,
        "Split by site: " . ($split_by_site ? "Yes" : "No"),
        "Output format: {$output_format_description}",
        "Update on Google Drive: " . ($update_remote ? "Yes ({$userInfo->email})" : "No"),
        "Parent Google Drive folder: " . ($update_remote ? $parent_drive_folder : "Not Used"),
        "Lambda version: " . QPCR_VERSION,
    ];

    $lambda = new LambdaClient([
        "region" => AWS_REGION,
        "version" => "latest",
        "credentials" => [
            "key" => AWS_KEY,
            "secret" => AWS_SECRET
        ]
        ]);

    $function_name = LAMBDA_FUNCTION . ":" . preg_replace("/[^A-Za-z0-9_-]/", "_", QPCR_VERSION);
    // $function_name = LAMBDA_FUNCTION;
    $result = $lambda->invoke([
        "FunctionName" => $function_name,
        "InvocationType" => "Event",
        "Payload" => json_encode([
            "inputs" => $uploaded_files,
            "from_email" => LAMBDA_FROM_EMAIL,
            "to_emails" => $to_emails,
            "username" => $USERNAME,
            "samples" => LAMBDA_SAMPLES,
            "sites_file" => LAMBDA_SITES_FILE,
            "sites_config" => LAMBDA_SITES_CONFIG,
            "extracter_config" => LAMBDA_EXTRACTER_CONFIG,
            "output_format" => $output_format,
            "output_format_description" => $output_format_description,
            "qaqc_config" => OUTPUT_FORMATS[$output_format]["qaqc_config"],
            "populator_config" => OUTPUT_FORMATS[$output_format]["populator_config"],
            "updater_config" => OUTPUT_FORMATS[$output_format]["updater_config"],
            "mapper_config" => LAMBDA_MAPPER_CONFIG,
            "mapper_map" => LAMBDA_MAPPER_MAP,
            "populator_template" => OUTPUT_FORMATS[$output_format]["populator_template"],
            "output_path" => LAMBDA_OUTPUT_PATH,
            "split_by_site" => $split_by_site,
            "tokens" => $tokens ? json_encode($tokens) : "",
            "remote_target" => $update_remote ? OUTPUT_FORMATS[$output_format]["lambda_remote_target"] : "",
            "populated_output_file" => $split_by_site ? LAMBDA_POPULATED_OUTPUT_FILE_SPLIT : LAMBDA_POPULATED_OUTPUT_FILE_ALL,
            "descriptive_settings" => $descriptive_settings,
            "parent_drive_folder" => $parent_drive_folder,
            "hide_qaqc" => false,
        ])
        ]);
        
    $recipients = make_bullet_list($to_emails);
    if ($recipients) {
        $recipients = "\n\nThe following recipients will receive the report:\n\n" . $recipients;
    }
    // $files_msg = make_bullet_list($uploaded_file_names);
    // if ($files_msg) {
    //     $files_msg = "\n\nThe following files have been uploaded:\n\n" . $files_msg;
    // }
    die(json_encode(["message" => "Analyzer started, this can take up to 10 minutes for 15 PDF files." . $recipients]));
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

$action = get_param("action");
if (!$action) {
    die("Error: No Action");
}

$sid = clean_name(get_param("sid"));
if (!$sid) {
    die("Error: No Session ID");
}
$data_dir = UPLOADS_ROOT . $sid . DIRECTORY_SEPARATOR;

if ($action == "uploadFile") {
    check_logged_in();
    delete_old_data();
    handle_uploads();
} elseif ($action == "runAnalyzer") {
    check_logged_in();
    run_analyzer();
} elseif ($action == "deleteCurrentData") {
    check_logged_in();
    delete_current_data();
} elseif ($action == "updateSettings") {
    check_logged_in();
    $new_settings = get_param("settings");
    update_settings($new_settings);
} else {
    die("Error: Unrecognized action " . $action);
}

die(json_encode(["success" => 1]));

?>


