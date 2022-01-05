<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/utils.php";

?>

<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer 404 Not Found</title>
    <?php include("includes/header.php") ?>
</head>
<body>



<div class="main-container">
    <div class="general-inner flex-general-margin">
    </div>
    <div class="general-inner flex-general-contents">
        <h1>Page Not Found</h1>
        <p>
            The page you requested does not exist. For further assistance please contact <?php print(obfuscate_email(get_setting("CONTACT_EMAIL"))) ?>.
        </p>
    </div>
    <div class="general-inner flex-general-margin">
    </div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
