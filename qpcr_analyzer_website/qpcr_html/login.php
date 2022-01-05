<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/database.php";

safe_session_start();
if (!empty($_SESSION["username"])) {
    header("location: /");
    exit;
}

require("includes/login_execute.php");

?>
<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer Login</title>
    <?php include("includes/header.php") ?>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>

</head>
<body>


<div class="main-container">
    <div class="general-inner flex-general-margin">
    </div>
    <div class="general-inner flex-general-contents">
        <h1>ODM QPCR Analyzer for COVID-19</h1>
        <p>
            <img src="/images/odm-logo.png" alt="ODM" style="float: right; width: 200px; height: 200px; margin: 0 0 10px 10px;">
            The ODM QPCR Analyzer provides scientists a fast, free, and easy way to calculate coronavirus levels in wastewater based on BioRad QPCR data files. Along with
            copies per copies, copies per liter, and copies per extracted mass calculations, reports include calibration curves along with a full QA/QC involving
            hundreds of individual tests. The output Excel documents are color-coded to mark where QA/QC tests fail, along with a description of each test. QA/QC includes outlier
            checks, calibration curve slope, efficiency, and intercept tests, inhibition controls, NTC/EB checks, various Ct range tests, and LOD/LOQ checks. Reports are sent by email and optionally
            saved in the cloud, such as on Google Drive.
        </p>
        <p>
            The Analyzer sits on top of the Open Data Model for Wastewater-based Surveillance, a free and open model for storing, validating, and sharing wastewater
            surveillance data. The ODM can be found at the <a href="https://github.com/Big-Life-Lab/ODM" target="_blank">ODM GitHub Repo</a>.
        </p>
        <p>
            We also provide our own services to customize output to each individual lab's needs. For details, please contact <?php print(obfuscate_email(get_setting("CONTACT_EMAIL"))) ?>.
        </p>
        <?php require("includes/login_form.php"); ?>
    </div>
    <div class="general-inner flex-general-margin">
    </div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
