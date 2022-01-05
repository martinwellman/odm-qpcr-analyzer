<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/database.php";
require_once "includes/utils.php";

$password = $confirm_password = "";
$password_err = $confirm_password_err = $global_err = "";

function show_errors($errors) {
    if ($errors) {
        print("<div class=\"errors\">{$errors}</div>");
    }
}

safe_session_start();

$reset_key = get_param("key");
$reset_username = get_param("run");
if ($reset_key) {
    session_destroy();
    safe_session_start();
}


if (!empty($_SESSION["username"]) && user_exists(($_SESSION["username"]))) {
    header("location: /");
    exit;
}

$username = get_param("username");
$reset_sent = FALSE;
if ($username) {
    if (verify_recaptcha(ACTION_RESET_PASSWORD, false)) {
        set_password_reset($username);
        $reset_sent = TRUE;
    } else {
        $global_err = "reCAPTCHA failed!";
    }
}

?>
<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer Password Reset</title>
    <?php include("includes/header.php") ?>
</head>
<body>

<script>
    function onResetSubmit(token) {
        $("#reset-form").submit();
    }
</script>

<div class="main-container">
    <div class="general-inner flex-general-margin"></div>
    <div class="general-inner flex-general-contents">
        <form action="<?php print($_SERVER["SCRIPT_NAME"]) ?><?php if ($reset_key && $reset_username) print("?key=" . $reset_key . "&run=" . $reset_username); ?>" id="reset-form" method="POST" class="form">
        <h1>Reset Password</h1>
        <?php
        $show_reset_form = TRUE;
        if ($reset_sent) {
            $show_reset_form = FALSE;
        ?>
            <p>
            A password reset email has been sent to the address associated with the user <?php print($username) ?>. Click the link in the email to choose a new password.
            </p>
        <?php
        } elseif ($reset_key) {
            if (verify_password_reset($reset_username, $reset_key)) {
                $show_reset_form = FALSE;
                if ($_SERVER["REQUEST_METHOD"] == "POST") {
                    if (!empty($_POST["password"]))
                        $password = $_POST["password"];
                    if (!empty($_POST["confirm_password"]))
                        $confirm_password = $_POST["confirm_password"];
                
                    // Check password is valid
                    if ($pwd_errors = validate_password($password)) {
                        $password_err = implode("<br />", $pwd_errors);
                    }

                    // Check passwords match
                    if ($password != $confirm_password) {
                        $confirm_password_err = "Passwords do not match";
                    }

                    if (!verify_recaptcha(ACTION_NEW_PASSWORD, false)) {
                        $global_err = "reCAPTCHA failed!";
                    }
                }

                if ($password && !$password_err && !$confirm_password_err && !$global_err) {
                    update_user($reset_username, [
                        "password" => $password,
                        "password_reset_key" => NULL,
                        "password_reset_time" => NULL
                    ]);
                    ?>
                    <p>Your password has been successfully reset! You can now <a href="/login.php">login</a> with your new password.</p>
                    <?php
                } else {
                    ?>
                    <p>
                    Enter a new password below<?php if ($reset_username) print(" for user {$reset_username}") ?>.
                    </p>
                    <div class="form-row">
                        <label for="password">Password</label>
                        <input type="password" name="password" id="password" value="<?php print($password) ?>" />
                        <?php show_errors($password_err) ?>
                    </div>
                    <div class="space-medium"></div>
                    <div class="form-row">
                        <label for="confirm_password">Confirm Password</label>
                        <input type="password" name="confirm_password" id="confirm_password" value="<?php print($confirm_password) ?>" />
                        <?php show_errors($confirm_password_err) ?>
                    </div>
                    <div class="space-medium"></div>
                    <div class="form-row">
                        <input type="submit" value="Submit" class="button <?php print_if_recaptcha(ACTION_NEW_PASSWORD, "g-recaptcha") ?>" data-sitekey="<?php print(RECAPTCHA_V3_SITE_KEY) ?>" data-callback="onResetSubmit" data-action="<?php print(ACTION_NEW_PASSWORD) ?>" />
                        <?php show_errors($global_err) ?>
                    </div>
                    <?php
                }
            } else {
                $show_reset_form = TRUE;
                ?>
                <p>
                The password reset key does not exist or has expired.
                </p>
                <?php
            }
        }
        if ($show_reset_form) {
        ?>
            <p>
                Enter your username below to reset a forgotten password.
            </p>
            <div class="form-row">
                <input type="text" name="username" id="username" />
                <?php show_errors($global_err) ?>
            </div>
            <div class="space-medium"></div>
            <div class="form-row">
                <input type="submit" value="Submit" class="button <?php print_if_recaptcha(ACTION_RESET_PASSWORD, "g-recaptcha") ?>" data-sitekey="<?php print(RECAPTCHA_V3_SITE_KEY) ?>" data-callback="onResetSubmit" data-action="<?php print(ACTION_RESET_PASSWORD) ?>" />
            </div>
        <?php
        }
        ?>
        </form>
    </div>
    <div class="general-inner flex-general-margin"></div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
