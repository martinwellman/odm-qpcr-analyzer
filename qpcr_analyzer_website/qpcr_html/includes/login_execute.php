<?php

require_once "includes/utils.php";

$login_err = "";
$username = $password = "";

$VARS = NULL;

if ($_SERVER["REQUEST_METHOD"] == "POST")
    $VARS = $_POST;
elseif ($_SERVER["REQUEST_METHOD"] == "GET")
    $VARS = $_GET;

if (isset($VARS["username"]) && isset($VARS["password"])) {
    $username = trim($VARS["username"]);
    $password = $VARS["password"];

    if (verify_recaptcha(ACTION_LOGIN, false)) {
        if (verify_user_password($username, $password)) {
            $_SESSION["username"] = $username;
            header("location: /");
            exit;
        } else {
            $login_err = "Username/password do not match";
        }
    } else {
        $login_err = "reCAPTCHA failed!";
    }
}

function show_login_errors($errors) {
    if ($errors) {
        print("<div class=\"errors\">{$errors}</div>");
    }
}

?>