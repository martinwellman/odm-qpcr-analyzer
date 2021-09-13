<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

// The root path of the website (in qpcr_html)
define("ROOT",                                      (dirname(__FILE__) . "/../"));
// Google apps client secret file for the QPCR Analyzer website project
define("CLIENT_SECRET_FILE",                        (ROOT . "../qpcr_other/client_secret.json"));
// Root directory where all user directories are placed.
define("USERS_ROOT",                                (ROOT . "../qpcr_other/u/"));
// Filenames of the user info file (Google Drive settings), tokens file (for Google Drive),
// and settings file (for miscellaneous user settings).
define("USERINFO_FILE",                             "user_info.json");
define("TOKENS_FILE",                               "tokens.json");
define("SETTINGS_FILE",                             "settings.json");

function clean_user_name($user) {
    $user = preg_replace("[^A-Za-z0-9-_\.]", "_", $user);
    return $user;
}

// $USERNAME = isset($_GET["user"]) && $_GET["user"] ? $_GET["user"] : DEFAULT_USER;
$USERNAME = isset($_COOKIE["user"]) && $_COOKIE["user"] ? $_COOKIE["user"] : "test";
$USERNAME = clean_user_name($USERNAME);
$USER_DIR = USERS_ROOT . $USERNAME . "/";

define("UPLOADS_ROOT",                              ROOT . "../qpcr_other/u/{$USERNAME}/uploads/");
define("UPLOADS_TTL",                               60*60);  # In seconds
define("QPCR_VERSION",                              ($USERNAME == "Martin" ? "0.1.33" : "0.1.33"));
define("OUTPUT_DEBUG",                              ($USERNAME == "Martin"));

function check_logged_in() {
    global $USERNAME;
    if (!$USERNAME) {
        die(json_encode(["error"=>"You are not logged in." . $USERNAME]));
    }
}

function get_saved_tokens() {
    // Retrieve the current user's Google Drive tokens.
    global $USER_DIR;
    if (!is_file($USER_DIR . TOKENS_FILE))
        return NULL;
    
    $fp = fopen($USER_DIR . TOKENS_FILE, "r");
    $tokens = fgets($fp);
    fclose($fp);
    return json_decode($tokens);
}

function get_gdrive_user_info() {
    // Get the user info associative array containing
    global $USER_DIR;
    if (is_file($USER_DIR . USERINFO_FILE)) {
        $fp = fopen($USER_DIR . USERINFO_FILE, "r");
        $data = json_decode(fgets($fp));
        return $data;
    }
    return NULL;
}

function get_known_users() {
    // Get an array of all users registered on the system.
    if (!is_dir(USERS_ROOT))
        return [];
    $files = scandir(USERS_ROOT);
    $users = [];
    // $has_default = false;
    foreach ($files as $file) {
        if ($file == "." || $file == "..")
            continue;
        if (is_dir(USERS_ROOT . $file)) {
            array_push($users, ["username" => $file]);
        }
    }
    // if (!$has_default)
    //     array_unshift($users, ["username" => DEFAULT_USER]);
    
    return $users;
}

function get_setting($key, $default=NULL) {
    // Get a user setting based on a single $key. The $key is a nested series of keys into the user settings
    // associative array (eg. drive.parent will fetch the Google Drive parent folder ID to upload to for
    // the user).
    $settings = get_settings();
    $keys = explode(".", $key);
    foreach ($keys as $key) {
        if (is_array($settings) && array_key_exists($key, $settings)) {
            $settings = $settings[$key];
        } else {
            return $default;
        }
    }
    return $settings;
}

function get_settings() {
    // Get all the settings of the user, as an associative array.
    global $USER_DIR;

    if (!is_file($USER_DIR . SETTINGS_FILE)) {
        return [];
    }

    $fp = fopen($USER_DIR . SETTINGS_FILE, "r");
    $data = json_decode(fgets($fp), true);
    fclose($fp);
    return $data;
}

function save_settings($settings) {
    // Save all the settings of a user.
    global $USER_DIR;

    $fp = fopen($USER_DIR . SETTINGS_FILE, "w");
    fwrite($fp, json_encode($settings));
    fclose($fp);
}

function update_settings($new_settings) {
    // Selectively update settings of a user, merging new settings with old settings.
    $settings = get_settings();
    merge_dicts($settings, $new_settings);
    save_settings($settings);
}

function merge_dicts(&$dict, $dict_diff) {
    // Merge two dictionaries (associative arrays). $dict_diff is added to $dict, overwriting any keys that already exist.
    foreach ($dict_diff as $key => $val) {
        if (array_key_exists($key, $dict) && is_array($val) && $val !== array() && array_keys($val) !== range(0, count($val)-1)) {
            if (!isset($dict[$key]))
                $dict[$key] = array();
            merge_dicts($dict[$key], $val);
        } else {
            $dict[$key] = $val;
        }
    }
}

?>
