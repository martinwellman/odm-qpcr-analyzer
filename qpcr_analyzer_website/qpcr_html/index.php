<!DOCTYPE html>
<html lang="en-us">

<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/utils.php";
require_once "includes/database.php";

safe_session_start();
if (!get_loggedin_user()) {
    session_destroy();
    // header("location: /login.php");
    require("login.php");
    exit;
}

if (get_param("login")) {
    if (get_param("login") !== get_loggedin_user()) {
        session_destroy();
        require("login.php");
        exit;
    }
}

update_user(NULL, [
    "last_access" => date("Y-m-d H:i:s")
]);

if (!is_verified()) {
    require("not_verified.php");
    exit;
}

?>

<head>
    <title>ODM QPCR Analyzer</title>

    <?php include("includes/header.php") ?>
    <link href="<?php mfile("/css/uploader.css") ?>" rel="stylesheet">

    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="/Formstone/dist/js/core.js"></script>
    <script src="/Formstone/dist/js/upload.js"></script>
    <script src="<?php mfile("/multiple-emails.js/multiple-emails.js") ?>"></script>
    <script src="https://cdn.jsdelivr.net/npm/js-cookie@3.0.0/dist/js.cookie.min.js"></script>
    <link href="/multiple-emails.js/multiple-emails.css" rel="stylesheet">
    <link href="/Formstone/dist/css/upload.css" rel="stylesheet">
</head>
<body>

<script>
    allowed_ext = [ "xlsx", "pdf" ];
    sid = generateSessionID();
    is_processing = false;

    currentDriveAccount = null;
    queryDict = {}
    location.search.substr(1).split("&").forEach(function(item) {queryDict[item.split("=")[0]] = item.split("=")[1]})

    originalDriveParent = "<?php print(get_user_data(NULL, "gdrive_parent")) ?>";
    originalRecipients = <?php print(json_encode(get_default_recipients())) ?>;

    $.fn.preloadImages = function() {
        this.each(function() {
            $("<img />")[0].src = this;
        });
    }

    // Preload the Google Signin button images, to prevent flicker when pressing the button
    $([
        "/images/google-signin/btn_google_signin_border_pressed_web@2x.png",
        "/images/google-signin/btn_google_signin_border_disabled_web@2x.png",
        "/images/google-signin/btn_google_signin_border_focus_web@2x.png",
        "/images/google-signin/btn_google_signin_border_normal_web@2x.png",
        // "/images/google-signin/btn_google_signin_dark_pressed_web@2x.png",
        // "/images/google-signin/btn_google_signin_dark_disabled_web@2x.png",
        // "/images/google-signin/btn_google_signin_dark_focus_web@2x.png",
        // "/images/google-signin/btn_google_signin_dark_normal_web@2x.png",
        // "/images/google-signin/btn_google_signin_light_pressed_web@2x.png",
        // "/images/google-signin/btn_google_signin_light_disabled_web@2x.png",
        // "/images/google-signin/btn_google_signin_light_focus_web@2x.png",
        // "/images/google-signin/btn_google_signin_light_normal_web@2x.png",
    ]).preloadImages();


    function generateSessionID() {
        d = new Date();
        date_str = d.getFullYear() + "-" + 
            ("0" + (d.getMonth()+1)).slice(-2) + "-" +
            ("0" + d.getDate()).slice(-2) + "-" + 
            ("0" + d.getHours()).slice(-2) + "_" +
            ("0" + d.getMinutes()).slice(-2) + "_" +
            ("0" + d.getSeconds()).slice(-2);
        return date_str + "-js-" + Math.random().toString(32).substr(2);
    }

    Formstone.Ready(function() {
        $(".upload").upload({
                action: "/action.php",
                maxSize: 1073741824,
                beforeSend: onBeforeSend,
                autoUpload: true
            }).on("start.upload", onStart)
            .on("complete.upload", onComplete)
            .on("filestart.upload", onFileStart)
            .on("fileprogress.upload", onFileProgress)
            .on("filecomplete.upload", onFileComplete)
            .on("fileerror.upload", onFileError)
            // .on("fileremove.upload", onFileRemove)
            .on("chunkstart.upload", onChunkStart)
            .on("chunkprogress.upload", onChunkProgress)
            .on("chunkcomplete.upload", onChunkComplete)
            .on("chunkerror.upload", onChunkError)
            .on("queued.upload", onQueued);

        $(".filelist.queue").on("click", ".cancel", onCancel);
        // $(".filelist.queue").on("click", ".remove", onRemove);
        $(".cancel_all").on("click", onCancelAll);
        // $(".start_all").on("click", onStart);
        $("#run_analyzer").on("click", onRunAnalyzer);
        $("#reset_form").on("click", onResetForm);

        updateFormstoneUI();
    });

    function onResetDriveFolder(e) {
        $("#drive-folder-id").val(originalDriveParent);
        updateDriveFolderUI();
    }

    function onViewDriveFolder(e) {
        var folderID = $("#drive-folder-id").val();
        window.open("https://drive.google.com/drive/u/2/folders/" + folderID, "_blank");
    }

    function onSaveDriveFolder(e) {
        var folderID = $("#drive-folder-id").val();

        <?php recaptcha_start(ACTION_QPCR_UPDATE_GOOGLE_DRIVE_PARENT) ?>
            $.ajax({
                url: "/action.php",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                type: "POST",
                data: {
                    "sid" : sid, 
                    "action" : "<?php print(ACTION_QPCR_UPDATE_GOOGLE_DRIVE_PARENT) ?>", 
                    "parent" : folderID, 
                    "g-recaptcha-response" : token 
                },
                dataType: "json",
                async: false,                
                error: function(response) {
                    alert("Error setting drive folder: " + response.responseText.trim());
                },
                success: function(response) {;
                    driveFolderChanged();
                    showError(response);
                }
            });
        <?php recaptcha_end() ?>
    }

    function updateRecipientsUI() {
        var recipients = JSON.parse($("#emails").val());
        var changed = false;
        if (recipients.length != originalRecipients.length) {
            changed = true;
        } else {
            for (var i=0; i<recipients.length; i++) {
                if (recipients[i] != originalRecipients[i]) {
                    changed = true;
                    break;
                }
            }
        }

        $("#save-recipient-emails").prop("disabled", !changed);
        $("#reset-recipient-emails").prop("disabled", !changed);        
    }

    function createMultipleEmails() {
        $(".multiple_emails-container").remove();
        $("#emails").multiple_emails({
            position: 'top', // Display the added emails above the input
            theme: 'bootstrap', // Bootstrap is the default theme
            checkDupEmail: true // Should check for duplicate emails added
        });
        $(".multiple_emails-input").attr("placeholder", "Enter email...");
        updateRecipientsUI();
    }


    function onResetRecipientEmails(e) {
        $("#emails").val(JSON.stringify(originalRecipients));
        createMultipleEmails();
    }

    function onSaveRecipientEmails(e) {
        var recipients = JSON.parse($("#emails").val());
        <?php recaptcha_start(ACTION_QPCR_UPDATE_DEFAULT_RECIPIENTS) ?>
            $.ajax({
                url: "/action.php",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                type: "POST",
                data: {
                    "sid" : sid, 
                    "action" : "<?php print(ACTION_QPCR_UPDATE_DEFAULT_RECIPIENTS) ?>", 
                    "recipients" : recipients.length ? recipients : null, 
                    "g-recaptcha-response" : token 
                },
                dataType: "json",
                async: false,
                success: function(response) {
                    recipientsSaved();
                    showError(response);
                },
                error: function(response) {
                    updateRecipientsUI();
                    alert("Error setting default recipients: " + response.responseText.trim());
                },
            });
        <?php recaptcha_end() ?>
    }

    function recipientsSaved() {
        originalRecipients = JSON.parse($("#emails").val());
        updateRecipientsUI();
    }

    function driveFolderChanged() {
        originalDriveParent = $("#drive-folder-id").val();
        updateDriveFolderUI();
    }

    function updateDriveFolderUI() {
        var currentDriveParent = $("#drive-folder-id").val();
        var disabled = currentDriveParent == originalDriveParent;
        $("#drive-folder-id-save").prop("disabled", disabled);
        $("#drive-folder-id-reset").prop("disabled", disabled)

        var viewDisabled = currentDriveParent.length == 0;
        $("#drive-folder-id-view").prop("disabled", viewDisabled)
    }

    function onCancel(e) {
        console.log("Cancel");
        var index = $(this).parents("li").data("index");
        $(this).parents("form").find(".upload").upload("abort", parseInt(index, 10));
        updateFormstoneUI();
    }

    function onCancelAll(e) {
        console.log("Cancel All");
        $(this).parents("form").find(".upload").upload("abort");
        updateFormstoneUI();
    }

    // function onRemove(e) {
    //   console.log("Remove");
    //   var index = $(this).parents("li").data("index");
    //   $(this).parents("form").find(".upload").upload("remove", parseInt(index, 10));
    // }

    function sleep(ms) {
        return new Promise(function(resolve) { setTimeout(resolve, ms); });
    }

    function onBeforeSend(formData, file) {
        console.log("Before Send");

        if (!validExtension(file.name))
            return false;

        formData.append("sid", sid);
        formData.append("action", "<?php print(ACTION_QPCR_UPLOAD_FILE) ?>");

        return formData;
    }

    function validExtension(file) {
        ext = file.toLowerCase().split(".").pop();
        for (var e=0; e<allowed_ext.length; e++) {
            if (ext == allowed_ext[e].toLowerCase()) {
                return true;
            }
        }
        return false;
    }

    function onQueued(e, files) {
        console.log("Queued");
        var html = '';
        var invalid = [];
        for (var i = 0; i < files.length; i++) {
            if (validExtension(files[i].name)) {
                html += '<li data-index="' + files[i].index + '"><span class="content"><span class="file">' + files[i].name + '</span><span class="cancel">Cancel</span><span class="progress">Queued</span></span><span class="bar"></span></li>';
            } else {
                invalid.push(files[i].name)
            }
        }

        $(this).parents("form").find(".filelist.queue").append(html);

        updateFormstoneUI();

        if (invalid.length > 0) {
            for (var i=0; i<invalid.length; i++)
                invalid[i] = "    • " + invalid[i];
            alert("The following files do not have an allowable extension and were not uploaded:\n\n" + invalid.join("\n") + "\n\nAllowable extensions are: " + allowed_ext.join(", "));
        }
    }

    function onResetForm(e, force) {
        <?php recaptcha_start(ACTION_QPCR_DELETE_CURRENT_DATA) ?>
            $.ajax({
                url: "/action.php",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                type: "POST",
                data: {
                    "sid" : sid, 
                    "action" : "<?php print(ACTION_QPCR_DELETE_CURRENT_DATA) ?>",
                    "g-recaptcha-response" : token 
                },
                dataType: "json",
                async: true,
                error: function(response) {
                    alert("Error clearing files: " + response.responseText.trim());
                },
            });
        <?php recaptcha_end() ?>

        sid = generateSessionID();
        $(".upload").upload("abort");        
        $(".form").find(".filelist.queue").html("");
        $(".form").find(".filelist.complete").html("");

        updateFormstoneUI();
    }

    function showProcessing(show) {
        if (show) {
            $(".processing-message").show();
            $(".upload").hide();
        } else {
            $(".processing-message").hide();
            $(".upload").show();
        }
    }

    function onRunAnalyzer(e) {
        // if ($("#run_analyzer").hasClass("disabled")) {
        //     return;
        // }
        var emails = JSON.parse($("#emails").val());
        if (emails.length == 0) {
            alert("Please enter at least one email address to receive the generated report.");
            return;
        }

        var curDriveParent = $("#drive-folder-id").val();
        if (curDriveParent != originalDriveParent) {
            alert("You changed the Google Drive Folder ID but did not press the \"Save\" button. Press the \"Save\" or \"Reset\" button before running the analyzer.");
            return;
        }

        is_processing = true;

        var update_remote = $("#update_remote").is(":checked");
        var split_by_site = $("#split_by_site").is(":checked");
        var output_format = $("input[name=output_format]:checked").val()

        if (update_remote && !currentDriveAccount) {
            alert("You must select a Google Drive account if \"Update on Google Drive\" is selected.");
            return;
        }

        //  Collect all file names that have been uploaded
        var files = [];
        var file_els = $(".form").find(".filelist.complete").find("li").not(".error").find(".file");
        for (var i=0; i<file_els.length; i++) {
            files.push($(file_els[i]).text());
        }
        
        <?php recaptcha_start(ACTION_QPCR_RUN_ANALYZER) ?>
            $.ajax({
                url: "/action.php",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                type: "POST",
                data: {
                    "sid" : sid, 
                    "action" : "<?php print(ACTION_QPCR_RUN_ANALYZER) ?>", 
                    "to_emails" : emails, 
                    "files" : files, 
                    "split_by_site" : split_by_site, 
                    "output_format" : output_format,
                    "update_remote" : update_remote,
                    "g-recaptcha-response" : token
                },
                dataType: "json",
                success: function(response) {
                    // Note: analyzerStarted will handle displaying an error if there is one
                    analyzerStarted(response);
                },
                error: function(response) {
                    alert("Error running analyzer. " + response.responseText.trim());
                    is_processing = false; 
                    updateFormstoneUI();
                },
                async: true
            });
        <?php recaptcha_end() ?>
        updateFormstoneUI();
    }

    function updateFormstoneUI() {
        showProcessing(is_processing);
        queued_errors = $(".form").find(".filelist.queue").find("li").find(".error").length;
        complete_errors = $(".form").find(".filelist.complete").find("li").find(".error").length;
        queued = $(".form").find(".filelist.queue").find("li").not(".error").length;
        complete = $(".form").find(".filelist.complete").find("li").not("error").length;
        if (is_processing || queued > 0 || complete == 0) {
            $("#run_analyzer").prop("disabled", true);
        } else {
            $("#run_analyzer").prop("disabled", false);
        }
        if (queued + queued_errors == 0) {
            $(".queued_empty").show();
        } else {
            $(".queued_empty").hide();
        }
        if (complete + complete_errors == 0) {
            $(".uploaded_empty").show();
        } else {
            $(".uploaded_empty").hide();
        }
        if (is_processing || (queued == 0 && complete == 0)) {
            $("#reset_form").prop("disabled", true);
        } else {
            $("#reset_form").removeClass("disabled");
            $("#reset_form").prop("disabled", false);
        }
    }

    function showError(response) {
        if (!response)
            return false;
        
        if (typeof response == 'string')
            try {
                response = JSON.parse(response);
            } catch (e) {

            }
        if (response["full_abort"])
            onCancelAll();
        if (response["error"]) {
            alert("ERROR: " + response["error"]);
            return true;
        }
        return false;
    }

    function analyzerStarted(response) {
        is_processing = false;
        updateFormstoneUI();
        if (showError(response)) {
            return;
        }

        onResetForm(true);

        if (response && response["message"]) {
            alert(response["message"]);
            return;
        }

        alert("QPCR Analyzer could not be started for an unknown reason.");
        // response = GOOD;
        // alert(JSON.stringify(response));
        // if (response === "" || response.toLowerCase().indexOf("error") > -1) {
        //     alert(response || "Error: Unknown error starting analyzer.");
        //     return;
        // }
        updateFormstoneUI();
    }


    function onComplete(e) {
        console.log("Complete");
        // All done!
        updateFormstoneUI();
    }

    function onFileStart(e, file) {
        console.log("File Start");
        $(this).parents("form").find(".filelist.queue")
            .find("li[data-index=" + file.index + "]")
            .find(".progress").text("0%");
            updateFormstoneUI();
    }

    function onFileProgress(e, file, percent, evt) {
        console.log("File Progress " + percent);
        var $file = $(this).parents("form").find(".filelist.queue").find("li[data-index=" + file.index + "]");

        $file.find(".progress").text(percent + "%")
        $file.find(".bar").css("width", percent + "%");
        updateFormstoneUI();
        e.preventDefault();
    }

    function onFileComplete(e, file, response) {
        console.log("File Complete");

        if (showError(response)) {
            $(this).parents("form").find(".filelist.queue")
                .find("li[data-index=" + file.index + "]").addClass("error")
                .find(".progress").text(getShortError(response.trim()));
        } else {
            var $target = $(this).parents("form").find(".filelist.queue").find("li[data-index=" + file.index + "]");
            $target.find(".file").text(file.name);
            $target.find(".progress").remove();
            $target.find(".cancel").remove();
            $target.appendTo($(this).parents("form").find(".filelist.complete"));
        }
        updateFormstoneUI();
    }

    function getShortError(response) {
        msg = "Server Error";
        console.log(typeof response);
        if (typeof response == "string") {
            try {
                response = JSON.parse(response)
            } catch (e) {
                return response;
            }
        }
        if (response["short_error"])
                msg = response["short_error"];
        return msg;
    }

    function onFileError(e, file, error) {
        console.log("File Error");
        msg = getShortError(error);
        $(this).parents("form").find(".filelist.queue")
            .find("li[data-index=" + file.index + "]").addClass("error")
            .find(".progress").text("Error: " + msg);
            updateFormstoneUI();
    }

    function onFileRemove(e, file, error) {
        console.log("File Removed");
        $(this).parents("form").find(".filelist.queue")
            .find("li[data-index=" + file.index + "]").addClass("error")
            .find(".progress").text("Removed");
            updateFormstoneUI();
    }

    function onChunkStart(e, file) {
        console.log("Chunk Start");
    }

    function onChunkProgress(e, file, percent) {
        console.log("Chunk Progress");
    }

    function onChunkComplete(e, file, response) {
        console.log("Chunk Complete");
    }

    function onChunkError(e, file, error) {
        console.log("Chunk Error");
    }

    // function onStart(e, files) {
    //     console.log("Start");
    //     $(this).parents("form").find(".filelist.queue")
    //         .addClass("started")
    //         .find("li")
    //         .find(".progress").text("Waiting");
    //         updateFormstoneUI();
    // }

    function onStart(e) {
        console.log("Start Upload");
        $(this).parents("form").find(".upload").upload("start");
        updateFormstoneUI();
    }


    //////////////////////////////////////////////////////////////////////////////
    // Google Drive account

    function driveStart() {
        gapi.load('auth2', function() {
            auth2 = gapi.auth2.init({
                client_id: '467725694757-q6e3ndr09ffnr0ciabak30d249nhad47.apps.googleusercontent.com',
                // Scopes to request in addition to 'profile' and 'email'
                scope: 'https://www.googleapis.com/auth/drive'
            });
            $('#signinButton').prop("disabled", false);
            // $('#clearGoogleDrive').prop("disabled", false);
        });
    }

    function googleSignInCallback(authResult) {
        if (authResult['code']) {
            <?php recaptcha_start(ACTION_QPCR_DRIVE_REGISTER) ?>
                // Send the code to the server
                $.ajax({
                    url: '/action.php',
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    type: "POST",
                    dataType: "json",
                    data: { 
                        "sid" : sid, 
                        "authCode": authResult["code"], 
                        "action": "<?php print(ACTION_QPCR_DRIVE_REGISTER) ?>", 
                        "g-recaptcha-response" : token 
                    },
                    success: function(result) {
                        // Handle or verify the server response.
                        if (showError(result)) {
                            return;
                        }
                        updateDriveUI(result["email"], result["picture"], result["name"]);
                    },
                    error: function(result) {
                        alert("Error setting Google Drive account: " + response.responseText.trim());
                    },
                });
            <?php recaptcha_end() ?>
        } else {
            // There was an error.
            alert("Error authenticating");
        }
    }

    function updateRemoteUI() {
        var checked = $('#update_remote').is(":checked");
        if (checked) {
            $("#split_by_site").prop("checked", true);
            if ($("#ottawa_long_format").is(":checked")) {
                $("#ottawa_wide_format").prop("checked", true);
            }
        }
        $(".disable-update-remote").prop("disabled", checked).addClass(checked ? "disabled" : "").removeClass(checked ? "" : "disabled");

        if (checked)
            $("#update_remote_contents").show();
        else
            $("#update_remote_contents").hide();
    }

    $(document).ready(function() {
        updateRemoteUI();
        updateDriveFolderUI();
        updateRecipientsUI();
        
        $("#emails").on("change", updateRecipientsUI);

        createMultipleEmails();
        
        $("#drive-folder-id-save").on("click", onSaveDriveFolder);
        $("#drive-folder-id-reset").on("click", onResetDriveFolder);
        $("#drive-folder-id-view").on("click", onViewDriveFolder);
        $("#drive-folder-id").on("change", updateDriveFolderUI).on("input", updateDriveFolderUI);
        $("#save-recipient-emails").on("click", onSaveRecipientEmails);
        $("#reset-recipient-emails").on("click", onResetRecipientEmails);

        $('#logoutButton').on("click", function() {
            location.href = "/logout.php";
        })

        $('#signinButton').on("click", function() {
            auth2.grantOfflineAccess().then(googleSignInCallback);
        });

        $('#clearGoogleDrive').on("click", function() {
            if (confirm("Remove access to the Google Drive account?")) {
                <?php recaptcha_start(ACTION_QPCR_CLEAR_GOOGLE_DRIVE) ?>
                    $.ajax({
                        url: "/action.php",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest"
                        },
                        type: "POST",
                        data: {
                            "sid" : sid, 
                            "action" : "<?php print(ACTION_QPCR_CLEAR_GOOGLE_DRIVE) ?>", 
                            "g-recaptcha-response" : token 
                        },
                        dataType: "json",
                        async: false,
                        success: function(response) {
                            showError(response);
                            updateDriveUI(null);
                        },
                        error: function(response) {
                            alert("Error removing access to Google Drive account: " + response.responseText.trim());
                        },
                    });
                <?php recaptcha_end() ?>
            } else {
                // Nothing to do
            }
        })

        $('#update_remote').on("change", updateRemoteUI);

        updateDriveUI(
            "<?php print(get_user_google_data(NULL, "email")) ?>", 
            "<?php print(get_user_google_data(NULL, "picture")) ?>", 
            "<?php print(get_user_google_data(NULL, "name")) ?>"
            );
    });

    function updateDriveUI(email, picture, name) {
        currentDriveAccount = email;
        if (email) {
            // Has been signed in
            $(".signin-details").text(email);
            $("#signinButton").attr("value", "Change Drive Account");
            $("#clearGoogleDrive").prop("disabled", false);
            $("#drive-profile-image").attr("src", picture ? picture : "/images/blank.png");
            $("#drive-profile-image").attr("alt", name ? name : "Google Drive");
        } else {
            // Not signed in to any account
            $(".signin-details").text("None");
            $("#signinButton").attr("value", "Sign In With Google");
            $("#clearGoogleDrive").prop("disabled", true);
            $("#drive-profile-image").attr("src", "/images/blank.png");
            $("#drive-profile-image").attr("alt", "Google Drive");
        }
    }

    function getCurrentDriveAccount() {
        $(".signin-details")
    }

    //////////////////////////////////////////////////////////////////////////////

</script>
<script src="https://apis.google.com/js/client:platform.js?onload=driveStart" async defer></script>

<div class="main-container">
    <div class="uploader-container">
        <form action="#" method="GET" class="form">
        <div class="uploader-container-inner">
        <h1>ODM QPCR Analyzer</h1>
        <div class="target-container">
            <div class="processing-message fs-upload fs-light target-box">
                <img src="/images/loading.gif" alt="Processing..." class="processing-image" />
                <!-- <span style="padding: 0 0 0 10px; display:inline-block; vertical-align: middle; line-height:normal;">Processing</span> -->
            </div>
            <div class="upload fs-upload-element fs-upload fs-light target-box"></div>
        </div>
        <div class="filelists">
            <b>Uploaded:</b><br />
            <div class="uploaded_empty filelists_empty">Empty</div>
            <ol class="filelist complete"></ol>
            <b>Queued:</b><br />
            <div class="queued_empty filelists_empty">Empty</div>
            <ol class="filelist queue"></ol>
            <div class="analyzer_buttons">
            <input type="button" id="run_analyzer" class="button" value="Run Analyzer" />
            <input type="button" id="reset_form" class="button" value="Clear Files" />
            </div>
        </div>
        </div>
        </form>
    </div>
    <div class="options-container">
    <div class="options-container-inner">
    <h1>Settings</h1>
    <div class="line"></div>
    <b>User:</b> <span class="options-title-data current-user"><?php print($_SESSION["username"]) ?></span><br />
    <div class="settings-suboptions">
    <input type="button" id="logoutButton" class="button settings-button" value="Logout" />
    </div>
    <div class="line"></div>

    <div class="options-title">Recipient Email Addresses:</div>
    <div class="settings-suboptions settings-subgrouped">
    <input type="text" id="emails" placeholder="Email" value='<?php print(json_encode(get_default_recipients())) ?>' />
    <div class="space-small"></div>
    <input type="button" id="save-recipient-emails" class="button settings-button" value="Save Emails as Defaults" />
    <input type="button" id="reset-recipient-emails" class="button settings-button" value="Reset" />
    </div>

    <div class="line"></div>

    <input type="checkbox" id="split_by_site" class="disable-update-remote" /> <label for="split_by_site" class="disable-update-remote">Split output by site</label>

    <div class="line"></div>

    <?php
    foreach (OUTPUT_FORMATS as $output_format=>$settings) {
        $checked = isset($settings["default"]) ? "checked" : "";
        $disable_update_remote = isset($settings["lambda_remote_target"]) && get_setting($settings["lambda_remote_target"]) ? "" : "disable-update-remote";
        print("<input type='radio' id='{$output_format}' value='{$output_format}' name='output_format' class='{$disable_update_remote}' {$checked} /> <label class='{$disable_update_remote}' for='{$output_format}'>{$settings['description']}</label><br />");
    }
    ?>

    <div class="line"></div>

    <input type="checkbox" id="update_remote" /> <label for="update_remote">Update on Google Drive</label>

    <div class="settings-suboptions settings-subgrouped" id="update_remote_contents">
    <div class="options-title">Google Drive Account:</div>
    <div class="settings-suboptions" style="position: relative;">
    <img src="/images/blank.png" id="drive-profile-image" alt="Google Drive" />
    <span class="signin-details">Retrieving details...</span><br />
    <div class="space-tiny"></div>
    <input type="button" id="signinButton" class="button settings-button google-signin-button" value="Sign In With Google" disabled />
    <input type="button" id="clearGoogleDrive" class="button settings-button" value="Clear" disabled />
    </div>
    <div class="line"></div>
    <div class="options-title">Save in Drive Folder ID:</div>
    <div class="settings-suboptions">
    <input type="text" id="drive-folder-id" placeholder="Folder ID" value="<?php print(get_user_data(NULL, "gdrive_parent")); ?>" /><br />
    <div class="space-small"></div>
    <input type="button" id="drive-folder-id-save" class="button settings-button" value="Save" />
    <input type="button" id="drive-folder-id-reset" class="button settings-button" value="Reset" />
    <input type="button" id="drive-folder-id-view" class="button settings-button" value="View Folder" />
    </div>
    </div>

    <div class="line"></div>

    <b>Lambda Version:</b> <span class="options-title-data"><?php print(get_setting("QPCR_VERSION")); ?></span><br />
    <div class="line"></div>
    </div>
    </div>
</div>

<?php include("includes/footer.php") ?>

</body>
</html>
