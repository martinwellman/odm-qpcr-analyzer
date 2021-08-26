<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once 'vendor/autoload.php';
require_once "includes/users.php";

define("DRIVE_SCOPE",                       "https://www.googleapis.com/auth/drive");

use Google\Client;
use Google\Google_Service_Oauth2;
use Google\Service\Oauth2;

$headers = getallheaders();
if (!isset($headers["X-Requested-With"]) || !$headers["X-Requested-With"]) {
    exit(403);
}

$authCode = file_get_contents('php://input');

# Exchange auth code for access token and refresh token
$client = new Google\Client();
$client->setAuthConfig(CLIENT_SECRET_FILE);
$client->setScopes([DRIVE_SCOPE, "profile", "email"]);
$client->setRedirectUri(($_SERVER['HTTPS'] == "on" ? "https://" : "http://") . $_SERVER['SERVER_NAME']);
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
if (!in_array(DRIVE_SCOPE, $scopes)) {
    die(json_encode(["error" => "You must allow access to Google Drive. Please try again and be sure to select the checkbox next to 'See, edit, create, and delete all of your Google Drive files'."]));
}

$tokens = [
    "token" => $creds["access_token"],
    "refresh_token" => $creds["refresh_token"],
    "scopes" => $scopes,
    "expiry" => gmdate("Y-m-d\TH:i:s\Z", $creds["created"] + $creds["expires_in"]),
];

if (!is_dir($USER_DIR))
    mkdir($USER_DIR, 0770, true);

# Save access and refresh token
$fp = fopen($USER_DIR . TOKENS_FILE, "w");
fwrite($fp, json_encode($tokens));
fclose($fp);

# Get and save user info (email, name, etc)
$service = new Google\Service\Oauth2($client);
$userInfo = $service->userinfo->get();
$fp = fopen($USER_DIR . USERINFO_FILE, "w");
fwrite($fp, json_encode($userInfo));
fclose($fp);

print(json_encode([
    "email" => $userInfo["email"],
]));

