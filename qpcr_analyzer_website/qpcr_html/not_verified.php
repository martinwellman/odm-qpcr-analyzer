<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/utils.php";
require_once "includes/database.php";

if (!get_loggedin_user() || is_verified()) {
    header("location: /");
    exit;
}

?>

<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer Verification In Progress</title>
    <?php include("includes/header.php") ?>
</head>
<body>



<div class="main-container">
    <div class="general-inner flex-general-margin">
    </div>
    <div class="general-inner flex-general-contents">
        <h1>Account Verification In Progress</h1>
        <p>
            Thank-you for registering with the ODM QPCR Analyzer. Your account, <?php print(get_loggedin_user()) ?>, is undergoing verification.
            You will not be able to use your account until verification is complete. We try to verify accounts or contact you by email within a day of creation,
            but depending on circumstances may take longer for some users. The ODM QPCR Analyzer is currently in the testing phase, during this phase we
            will typically only verify invited accounts. Once verified you will receive an email at <?php print(get_user_data(NULL, "email")) ?>.
        </p>
        <p>
            For further assistance please contact <?php print(obfuscate_email(get_setting("CONTACT_EMAIL"))) ?>.
        </p>
    </div>
    <div class="general-inner flex-general-margin">
    </div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
