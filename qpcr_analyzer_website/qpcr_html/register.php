<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/database.php";
require_once "includes/utils.php";

safe_session_start();
if (!empty($_SESSION["username"])) {
    header("location: /");
    exit;
}

$username = $email = $password = $confirm_password = "";
$username_err = $email_err = $password_err = $confirm_password_err = $global_err = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $username = $_POST["username"];
    $email = trim($_POST["email"]);
    $password = $_POST["password"];
    $confirm_password = $_POST["confirm_password"];

    // Check for existing user
    if (!$username) {
        $username_err = "Username required";
    } elseif ($username_errors = validate_username($username)) {
        $username_err = implode("<br />", $username_errors);
    } elseif (user_exists($username)) {
        $username_err = "Username not available";
    }

    // Check valid email
    if (!$email) {
        $email_err = "Email required";
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $email_err = "Invalid email";
    }

    // Check password is valid
    if ($pwd_errors = validate_password($password)) {
        $password_err = implode("<br />", $pwd_errors);
    }

    // Check passwords match
    if ($password != $confirm_password) {
        $confirm_password_err = "Passwords do not match";
    }

    if (!verify_recaptcha(ACTION_REGISTER, false)) {
        $global_err = "reCAPTCHA failed!";
    }

    if (!$username_err && !$email_err && !$password_err && !$confirm_password_err && !$global_err) {
        if (add_user($username, $email, $password)) {
            safe_session_start();
            $_SESSION["username"] = $username;
            header("location: /");
            exit;
        } else {
            $global_err = "An unknown error occurred while adding the user";
        }
    }
}

function show_errors($errors) {
    if ($errors) {
        print("<div class=\"errors\">{$errors}</div>");
    }
}
?>
<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer Registration</title>
    <?php include("includes/header.php") ?>
</head>
<body>

<script>
    function onRegisterSubmit(token) {
        $("#register-form").submit();
    }
</script>

<div class="main-container">
    <div class="general-inner flex-general-margin"></div>
    <div class="general-inner flex-general-contents">
        <form action="register.php" method="POST" class="form" id="register-form">
        <h1>Register</h1>
        <p>
            New accounts will need to be verified before they can be used. During the current testing phase we will
            only accept and verify accounts from known users.
        </p>
        <div class="form-row">
            <label for="username">Username</label>
            <input type="text" name="username" id="username" value="<?php print($username) ?>" />
            <?php show_errors($username_err) ?>
        </div>
        <div class="space-medium"></div>
        <div class="form-row">
            <label for="email">Email Address</label>
            <input type="text" name="email" id="email" value="<?php print($email) ?>" />
            <?php show_errors($email_err) ?>
        </div>
        <div class="space-medium"></div>
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
            <input type="submit" value="Submit" class="button <?php print_if_recaptcha(ACTION_REGISTER, "g-recaptcha") ?>" data-sitekey="<?php print(RECAPTCHA_V3_SITE_KEY) ?>" data-callback="onRegisterSubmit" data-action="<?php print(ACTION_REGISTER) ?>" />
            <?php show_errors($global_err) ?>
        </div>

        <div class="space-medium"></div>
        Already have an account? <a href="/login.php">Login</a>
        <div class="space-small"></div>
        </form>
    </div>
    <div class="general-inner flex-general-margin"></div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
