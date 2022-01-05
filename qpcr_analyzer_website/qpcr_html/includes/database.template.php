<?php

/*
Save this file as database.php and fill in:

    - DB_PASSWORD
    - PASSWORD_RESET_KEY_SALT

Change other settings if desired.
*/

require_once "settings.php";

require_once "vendor/autoload.php";

use Aws\Ses\SesClient;
use Aws\Ses\Exception\SesException;

define("DB_HOST",                                       "127.0.0.1");
define("DB_USER",                                       "odm");
define("DB_PASSWORD",                                   "<Database password>");
define("DB_NAME",                                       "odm.qpcr_analyzer");

define("DB_USERTABLE",                                  "users");
define("PASSWORD_ALGO",                                 PASSWORD_BCRYPT);
define("PASSWORD_RESET_KEY_SALT",                       "<Password reset key salt>");

define("MIN_PASSWORD_LENGTH",                           8);
define("MAX_PASSWORD_LENGTH",                           128);
define("MIN_USERNAME_LENGTH",                           1);
define("MAX_USERNAME_LENGTH",                           128);
define("PASSWORD_RESET_EXPIRY_HOURS",                   24);

$conn = null;
try {
    $conn = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASSWORD);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $conn->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    die("Database connection error: " . $e->getMessage());
}

// Create the user table if it does not exist
$stmt = $conn->query("SHOW TABLES LIKE '" . DB_USERTABLE . "';");
if (empty($stmt->fetch())) {
    try {
        $sql = "CREATE TABLE `" . DB_USERTABLE . "` (
            `id` int(11) unsigned AUTO_INCREMENT UNIQUE PRIMARY KEY,
            `username` varchar(100) NOT NULL UNIQUE KEY,
            `account_type` varchar(64) NOT NULL DEFAULT 'user',
            `email` varchar(100) NOT NULL,
            `password` varchar(255) NOT NULL,
            `default_recipients` TEXT,
            `google_tokens` TEXT,
            `google_userinfo` TEXT,
            `gdrive_parent` varchar(255),
            `last_access` DATETIME,
            `password_reset_key` varchar(255),
            `password_reset_time` int,
            `verified` BOOL DEFAULT FALSE
        );";
        $res = $conn->exec($sql);
    } catch (PDOException $e) {
        die("Exception creating table " . DB_USERTABLE . ": " . $e->getMessage());
    }
}

function verify_password_reset($username, $reset_key) {
    global $conn;

    try {
        $sh = $conn->prepare("SELECT username,password_reset_key,password_reset_time FROM `" . DB_USERTABLE . "` WHERE username=:username");
        $sh->execute([
            ":username" => $username
        ]);
        $user_data = $sh->fetch();
        if ($user_data) {
            if (time() > $user_data["password_reset_time"] + PASSWORD_RESET_EXPIRY_HOURS*60*60) {
                // Reset key expired.
                update_user($user_data["username"], [
                    "password_reset_key" => NULL,
                    "password_reset_time" => NULL
                ]);
                return FALSE;
            }
            return password_verify($reset_key, $user_data["password_reset_key"]);
        }
    } catch (PDOException $e) {
        print("Exception getting password reset username: " . $e->getMessage());
        return NULL;
    }
    return FALSE;
}

function set_password_reset($username, $send_email = TRUE) {
    $username = $username ?? get_loggedin_user();

    if (user_exists($username)) {
        $password_reset_key = md5(PASSWORD_RESET_KEY_SALT . $username . time());
        update_user($username, [
            "password_reset_key" => password_hash($password_reset_key, PASSWORD_ALGO),
            "password_reset_time" => time()
        ]);
        if ($send_email) {
            $user_data = get_user_data($username);
            $to = $user_data["email"];
            $subject = "ODM QPCR Analyzer Password Reset";
            $url = get_protocol_and_domain() . "/reset_password.php?key={$password_reset_key}&run={$username}";
            $expiry = PASSWORD_RESET_EXPIRY_HOURS;
            $html_body = <<<EOM
<html>
<head></head>
<body>
<p>
A password reset was requested for this email address registered at the ODM QPCR Analyzer. Click the link below or cut and paste it into a browser to choose a new password:
</p>
<p>
<a href="{$url}">{$url}</a>
</p>
<p>
The reset request will expire in {$expiry} hours. If you do not wish to reset your password you can ignore this email.
</p>
</body>
</html>
EOM;
            $text_body = <<<EOM
A password reset was requested for this email address registered at the ODM QPCR Analyzer. Click the link below or cut and paste it into a browser to choose a new password:

{$url}

The reset request will expire in {$expiry} hours. If you do not wish to reset your password you can ignore this email.
EOM;
            send_email($to, $subject, $html_body, $text_body);
        }
        return TRUE;
    }

    return FALSE;
}

function delete_table($table) {
    global $conn;

    $sh = $conn->prepare("DROP TABLE `{$table}`");
    $sh->execute();
}

function get_default_recipients($username = NULL) {
    $username = $username ?? get_loggedin_user();

    $default_recipients = get_user_data($username, "default_recipients", []);
    if ($default_recipients)
        $default_recipients = explode(",", $default_recipients);
        return $default_recipients;
}

/**
 * Get all the user data (settings, username, hashed password, ...).
 * 
 * @param string $username The username to get the data for. If NULL then we get the current session's username.
 * @param string $key If set then retrieve this user setting, otherwise get all the user's data as an associative array.
 * @param any $default Default value to return if the $key cannot be found or the value is empty.
 * @return array Associative array of all the user's values if $key is empty, or the user's setting for $key if it is set.
 */
function get_user_data($username = NULL, $key = NULL, $default = NULL) {
    global $conn;

    try {
        $username = $username ?? get_loggedin_user();
        if (!$username)
            return $default;

        $sh = $conn->prepare("SELECT * FROM `" . DB_USERTABLE . "` WHERE username=:username");
        $sh->execute([
            ":username" => $username
        ]);
        $user_data = $sh->fetch();
        if ($key)
            return $user_data[$key] ?? $default;
        return $user_data ?? $default;
    } catch (PDOException $e) {
        print("User {$username} does not exist");
        return $default;
    }
}

function get_user_google_data($username, $key = NULL, $default = NULL) {
    $username = $username ?? get_loggedin_user();

    $user_data = get_user_data($username, "google_userinfo");
    if (!$user_data)
        return $default;

    $user_data = json_decode($user_data, TRUE);

    if ($key === NULL)
        return $user_data[$key];

    return !empty($user_data[$key]) && $user_data[$key] !== NULL ? $user_data[$key] : $default;
}

/**
 * Delete a user.
 */
function delete_user($username) {
    global $conn;

    $username = $username ?? get_loggedin_user();
    if (!$username)
        return FALSE;

    try {
        $sh = $conn->prepare("DELETE FROM `" . DB_USERTABLE . "` WHERE (username=:username);");
        $sh->execute([
            ":username" => $username
        ]);
        return TRUE;
    } catch (PDOException $e) {
        print("Exception deleting user {$username}: " . $e->getMessage());
        return FALSE;
    }
}

/**
 * Get the credentials for an AWS client.
 * 
 * Returns
 * -------
 * Associative array of credentials for constructing an AWS client.
 */
function get_aws_creds() {
    return [
        "region" => get_setting("AWS_REGION"),
        "version" => "latest",
        "credentials" => [
            "key" => get_setting("AWS_KEY"),
            "secret" => get_setting("AWS_SECRET")
        ]
        ];
}


/**
 * Send an email.
 */
function send_email($to, $subject, $html_body, $text_body) {
    try {
        $ses = new SesClient(get_aws_creds());

        $char_set = "UTF-8";

        $result = $ses->sendEmail([
            'Destination' => [
                'ToAddresses' => [$to],
            ],
            'ReplyToAddresses' => [get_setting("LAMBDA_FROM_NAME_AND_EMAIL")],
            'Source' => get_setting("LAMBDA_FROM_NAME_AND_EMAIL"),
            'Message' => [

                'Body' => [
                    'Html' => [
                        'Charset' => $char_set,
                        'Data' => $html_body,
                    ],
                    'Text' => [
                        'Charset' => $char_set,
                        'Data' => $text_body,
                    ],
                ],
                'Subject' => [
                    'Charset' => $char_set,
                    'Data' => $subject,
                ],
            ],
            // If you aren't using a configuration set, comment or delete the
            // following line
            // 'ConfigurationSetName' => $configuration_set,
        ]);
    } catch (SesException $e) {
        print("Exception sending email: " . $e->getAwsErrorMessage());
        return FALSE;
    }
}


/**
 * Add a user.
 */
function add_user($username, $email, $password) {
    global $conn;

    if (user_exists($username))
        return FALSE;

    try {
        $sh = $conn->prepare("INSERT INTO `" . DB_USERTABLE . "` (username,email,password,default_recipients,verified) VALUES (:username,:email,:password,:default_recipients,:verified)");
        $params = [
            ":username" => $username,
            ":email" => $email,
            ":default_recipients" => $email,
            ":password" => password_hash($password, PASSWORD_ALGO),
            ":verified" => ACCOUNTS_REQUIRE_VERIFICATION ? 0 : 1
        ];
        $sh->execute($params);
        create_user_dir($username);

        if (NOTIFY_ADMIN_OF_NEW_ACCOUNTS) {
            $msg = "A new user with username {$username} and email {$email} has signed up on the ODM QPCR Analyzer website. ";
            if (ACCOUNTS_REQUIRE_VERIFICATION && !get_user_data(NULL, "verified")) {
                $msg .= "This user requires verification before they can use the Analyzer. Follow the link below to verify the user:\n\n";
                $msg .= get_protocol_and_domain() . "/verify_account.php?verifyuser=" . $username;
            } else {
                $msg .= "This user does not require verification.";
            }
            send_email(get_setting("CONTACT_EMAIL"), "ODM QPCR Analyzer New User", str_replace("\n", "<br />", $msg), $msg);
        }

        return TRUE;
    } catch (PDOException $e) {
        print("Exception adding user ${username}: " . $e->getMessage());
        return FALSE;
    }
}

/**
 * Verify that the user exists and has the specified password.
 */
function verify_user_password($username, $password) {
    global $conn;

    $user_data = get_user_data($username);
    return $user_data && password_verify($password, $user_data["password"]);
}

/**
 * Verify that the user exists.
 */
function user_exists($username) {
    global $conn;

    return !empty(get_user_data($username));
}

/**
 * Change a user's password.
 */
function change_password($username, $password) {
    global $conn;

    return update_user($username, ["password" => $password]);
}

/**
 * Update the specified values for the user (eg. email, password, ...).
 * 
 * @param string $username The username to modify.
 * @param array $values Associative array of values to modify.
 * @return bool TRUE if values successfully changed, FALSE otherwise.
 */
function update_user($username, $values) {
    global $conn;

    $username = $username ?? get_loggedin_user();

    $fields = "";
    $params = [];
    foreach ($values as $key=>$value) {
        // Do not allow changing of user name
        if ($key == "username")
            continue;

        if ($fields) $fields = $fields . ",";
        $fields = $fields . $key . "=:" . $key;
        if ($key == "password")
            $value = password_hash($value, PASSWORD_ALGO);
        $params[":" . $key] = $value;
    };

    if (!array_key_exists(":username", $params))
        $params[":username"] = $username;

    if (!$fields)
        return FALSE;

    try {
        $sh = $conn->prepare("UPDATE `" . DB_USERTABLE . "` SET {$fields} WHERE username=:username;");
        $sh->execute($params);
        return TRUE;
    } catch (PDOException $e) {
        print("Exception updating user {$username}: " . $e->getMessage());
        return FALSE;
    }
}

/**
 * Make sure a password meets the minimum requirements (eg. minimum length, lowercase/uppercase letters, digits, special characters...)
 * 
 * @param string $password The password to check.
 * @return array An array of strings describing errors (eg. missing a number, too short, ...) or empty array if
 * no errors.
 */
function validate_password($password) {
    $errors = [];

    if (strlen($password) < MIN_PASSWORD_LENGTH)
        array_push($errors, "Password must be at least " . MIN_PASSWORD_LENGTH . " characters long");

    if (strlen($password) > MAX_PASSWORD_LENGTH)
        array_push($errors, "Password cannot be more than " . MAX_PASSWORD_LENGTH . " characters long");

    // Remove uppercase letters
    $less = preg_replace("/[A-Z]/", "", $password);
    if ($less == $password)
        array_push($errors, "Password must have at least one uppercase letter");
    $password = $less;
    
    // Remove lower case letters
    $less = preg_replace("/[a-z]/", "", $password);
    if ($less == $password)
        array_push($errors, "Password must have at least one lowercase letter");
    $password = $less;

    // Remove numbers
    $less = preg_replace("/[0-9]/", "", $password);
    if ($less == $password)
        array_push($errors, "Password must have at least one number");
    $password = $less;

    // Remove special characters
    $less = preg_replace("/[\W_]/", "", $password);
    if ($less == $password)
        array_push($errors, "Password must have at least one special character");
    $password = $less;

    // Anything that hasn't been removed is not allowed
    if ($password)
        array_push($errors, "Password has invalid characters: {$password}");

    return $errors;
}

function validate_username($username) {
    $errors = [];
    
    if (strlen($username) < MIN_USERNAME_LENGTH)
        array_push($errors, "Username must be at least " . MIN_USERNAME_LENGTH . " character" . (MIN_USERNAME_LENGTH == 1 ? "" : "s") . "long");

    if (strlen($username) > MAX_USERNAME_LENGTH)
        array_push($errors, "Username can not be more than " . MAX_USERNAME_LENGTH . " characters long");

    $less = preg_replace("/[A-Za-z0-9_]/", "", $username);
    if ($less)
        array_push($errors, "Username can only contain letters, numbers, and underscore");

    return $errors;
}

function get_loggedin_user() {
    return !empty($_SESSION["username"]) && user_exists($_SESSION["username"]) ? $_SESSION["username"] : NULL;
}

function assert_logged_in() {
    if (!get_loggedin_user()) {
        die(json_encode(["error"=>"You are not logged in."]));
    }
}

function assert_logged_in_and_verified() {
    assert_logged_in();
    if (!is_verified()) {
        die(json_encode(["error"=>"Your account is not yet verified."]));
    }
}

function create_user_dir($username = NULL) {
    if (!is_dir(get_setting("CURRENT_USER_DIR")))
        mkdir(get_setting("CURRENT_USER_DIR"), 0770, true);
}

function is_admin_user($username = NULL) {
    return get_user_data($username, "account_type") == "admin";
}

function is_verified($username = NULL, $ignore_global_verify_accounts = false) {
    if (!$ignore_global_verify_accounts && !ACCOUNTS_REQUIRE_VERIFICATION)
        return TRUE;
    return get_user_data($username, "verified");
}

/**
 * Start the user session if we haven't done so already.
 */
function safe_session_start() {
    // Calling session_start multiple times works fine, but outputs a debug notice
    if (session_id() == "")
        session_start();
}

/**
 * Get the full protocol and domain (without a trailing forward slash), eg. https://qpcr.cryotoad.com
 */
function get_protocol_and_domain() {
    return (isset($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] == "on" ? "https://" : "http://") . $_SERVER["SERVER_NAME"];
}


safe_session_start();
create_user_dir();

?>

