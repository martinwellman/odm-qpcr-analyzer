<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/database.php";
require_once "includes/utils.php";

$global_err = "";

function show_errors($errors) {
    if ($errors) {
        print("<div class=\"errors\">{$errors}</div>");
    }
}

if (!get_loggedin_user() || !is_verified() || !is_admin_user()) {
    header("location: /");
    exit;
}

$verifyuser = get_param("verifyuser");
$un = get_param("un");
$verify = get_param("verify") == "on";
$notify_email = get_param("notify");
$recaptcha_response = get_param("g-recaptcha-response");
$email_sent_to = NULL;

if ($un) {
    if (verify_recaptcha(ACTION_VERIFY_ACCOUNT, false)) {
        update_user($un, [
            "verified" => $verify ? 1 : 0
        ]);
        if ($notify_email && $verify) {
            $url = get_protocol_and_domain();
            $msg_text = <<<EOM
Thank-you for signing with for the ODM QPCR Analyzer!

We're happy to inform you that your account "{$un}" has been verified and is now ready to use. To log in, follow the link below:

{$url}?login={$un}

If you require assistance please reply to this email.

Sincerely,
ODM QPCR Analyzer
EOM;
            $msg_html = str_replace("\n", "<br />", $msg_text);
            $email_sent_to = get_user_data($un, "email");
            send_email($email_sent_to, "ODM QPCR Analyzer Account Verified", $msg_html, $msg_text);
        }
    } else {
        $global_err = "reCAPTCHA failed!";
    }
}

?>
<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer Account Verifier</title>
    <?php include("includes/header.php") ?>
</head>
<body>

<script>
    function onVerifySubmit(token) {
        $("#verify-form").attr("action", "<?php print($_SERVER["SCRIPT_NAME"]) ?>?verifyuser=" + $("#un").val());
        $("#verify-form").submit();
    }
</script>

<div class="main-container">
    <div class="general-inner flex-general-margin"></div>
    <div class="general-inner flex-general-contents">
        <form action="<?php print($_SERVER["SCRIPT_NAME"]) ?>?verifyuser=<?php print($verifyuser) ?>" id="verify-form" method="POST" class="form">
        <h1>Verify Account</h1>
        <p>
            Enter the user to verify.
        </p>
        <div class="form-row">
            <input type="text" name="un" id="un" value="<?php print($verifyuser) ?>" />
        </div>
        <div class="space-small"></div>
        <div class="form-row">
            <input type="checkbox" name="verify" id="verify" style="float: left;" checked />
            <label for="verify">Verify</label>
        </div>
        <div class="space-small"></div>
        <div class="form-row">
            <input type="checkbox" name="notify" id="notify" style="float: left;" checked />
            <label for="notify">Notify by email</label>
        </div>
        <?php
            if ($verifyuser) {
        ?>
                <div class="space-medium"></div>
                <div class="form-row">
                <?php
                    if (user_exists($verifyuser)) {
                        print("User \"{$verifyuser}\" is currently ");
                        if (is_verified($verifyuser, true))
                            print("<b>verified</b>");
                        else
                            print("<b>not verified</b>");
                        print("<br />The user's email address is <b>" . get_user_data($verifyuser, "email") . "</b>");
                    } else {
                        print("User \"{$verifyuser}\" does not exist.");
                    }
                    if ($email_sent_to) {
                        print("<br />An email has been sent to <b>{$email_sent_to}</b> to notify them that their account was verified.");
                    }
                ?>
                </div>
        <?php
            }
        ?>
        <div class="space-medium"></div>
        <div class="form-row">
            <input type="submit" value="Submit" class="button <?php print_if_recaptcha(ACTION_VERIFY_ACCOUNT, "g-recaptcha") ?>" data-sitekey="<?php print(RECAPTCHA_V3_SITE_KEY) ?>" data-callback="onVerifySubmit" data-action="<?php print(ACTION_VERIFY_ACCOUNT) ?>" />
            <?php show_errors($global_err) ?>
        </div>
        </form>
    </div>
    <div class="general-inner flex-general-margin"></div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
