<?php include("includes/utils.php") ?>
<!DOCTYPE html>
<html lang="en-us">

<head>
    <title>ODM QPCR Analyzer Privacy and Terms of Service</title>
    <?php include("includes/header.php") ?>
</head>
<body>



<div class="main-container">
    <div class="general-inner flex-general-margin">
    </div>
    <div class="general-inner flex-general-contents">
        <h1>Privacy Policy and Terms of Service</h1>
        <p>
            <img src="/images/odm-logo.png" alt="ODM" style="float: right; width: 200px; height: 200px; margin: 0 0 10px 10px;">
            All data submitted and generated by the ODM QPCR Analyzer remain the property of the user. We do not claim ownership
            over any data received, calculated, or sent out by the Analyzer, nor will we use any such data for purposes not 
            related to the Analyzer for generating the reports. We also will not distribute any data to individuals or organizations
            other than to the email addresses specified by the user on the website, unless otherwise specified by the user.
        </p>
        <p>
            During the current testing phase, we store all inputs (BioRad data files) and outputs (QPCR Excel reports) to a private
            and secure location in the cloud, in an Amazon Web Services S3 bucket. The inputs are stored to allow processing of the files by the Analyzer, while
            the outputs are stored in order to provide additional testing by the developers. Once testing has completed we will delete
            all the data and update the Analyzer to automatically delete the data when no longer needed, including both the inputs and outputs,
            unless otherwise specified by the user.
        </p>
        <p>
            Along with all data submitted and generated by the Analyzer and all account details such as email addresses and names, we will not share
            any of your information with a third party unless we are explicitly given permission to by the user. Recipients of the
            generated reports will be the only individuals receiving such information, and will be able to see the email addresses of all
            other recipients. During this testing phase the primary developer (Martin Wellman) may on occassion be included in emails
            that are automatically sent as a result of an error during execution.
        </p>
        <h2>Google API/Drive Usage</h2>
        <p>
            Users may optionally link (and unlink) their QPCR Analyzer account to a Google Drive account. Once logged in, you can link to a Google Drive 
            account by following the OAuth consent steps after pressing the "Sign in With Google" button at
            <a href="<?php print(get_protocol_and_domain()) ?>"><?php print(get_protocol_and_domain()) ?></a>.
        </p>
        <p>
            When linking to a Google Drive account you give the ODM QPCR Analyzer
            permission to store and retrieve data to any location that your Google Drive account has access to. We will only access and
            modify data that you have specified on the website (located at <a href="https://qpcr.cryotoad.com">qpcr.cryotoad.com</a> and 
            <a href="https://qpcr2.cryotoad.com">qpcr2.cryotoad.com</a>). Google Drive is used to store and retrieve QPCR reports generated by the
            ODM QPCR Analyzer as well as to store configuration files. The only user data we store is your basic profile information (your
            email address, name, and profile image). This information is used to populate the ODM QPCR Analyzer user interface to indicate
            to you which account you have linked to. This information will not be shared with any third party. We will not
            access your Google Drive account for any purposes outside of the ODM QPCR Analyzer. The use and transfer to any other app of any
            data received from Google APIs will adhere to the <a href="https://developers.google.com/terms/api-services-user-data-policy#additional_requirements_for_specific_api_scopes" target="_blank">Google API Services User Data Policy</a>, 
            including the Limited Use requirements.
        </p>
        <h2>Account Deletion Requests</h2>
        <p>
            Should you decide to stop using the ODM QPCR Analyzer, you are free to keep your account active. However, if you would
            like your account and all associated data (including Google Drive access/refresh tokens and email addresses) to be deleted,
            please contact <?php print(obfuscate_email("mwellman@ohri.ca", "mwellman@ohri.ca")) ?>.
        </p>
        <h2>Updates to the Privacy Policy and Terms of Service</h2>
        <p>
            We may revise this privacy policy from time to time by updating this page. For further clarifications, please contact
            <?php print(obfuscate_email("mwellman@ohri.ca", "mwellman@ohri.ca")) ?>.
        </p>
    </div>
    <div class="general-inner flex-general-margin">
    </div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>