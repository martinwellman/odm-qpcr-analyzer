<!DOCTYPE html>
<html lang="en-us">

<?php

require_once "includes/users.php";

function contactLink() {
    // Obfuscated contact link.
    return "<script>document.write('<'+'a'+' '+'h'+'r'+'e'+'f'+'='+\"'\"+'m'+'&'+'#'+'9'+'7'+';'+'i'+'l'+'t'+'o'+'&'+'#'+'5'+'8'+';'+'%'+
    '6'+'D'+'&'+'#'+'1'+'1'+'9'+';'+'e'+'l'+'%'+'6'+'C'+'m'+'a'+'n'+'&'+'#'+'6'+'4'+';'+'o'+'%'+'6'+'&'+
    '#'+'5'+'6'+';'+'%'+'7'+'2'+'i'+'&'+'#'+'4'+'6'+';'+'c'+'a'+\"'\"+'>'+'m'+'w'+'e'+'l'+'l'+'m'+'&'+'#'+
    '9'+'7'+';'+'&'+'#'+'1'+'1'+'0'+';'+'&'+'#'+'6'+'4'+';'+'o'+'h'+'r'+'i'+'&'+'#'+'4'+'6'+';'+'c'+'&'+
    '#'+'9'+'7'+';'+'<'+'/'+'a'+'>');</script><noscript>[Turn on JavaScript to see the email address]</noscript>";
}

function mfile($file) {
    $local_file = $file;
    if ($local_file[0] == "/")
        $local_file = $_SERVER['DOCUMENT_ROOT'] . $local_file;
    else
        $local_file = dirname($_SERVER['SCRIPT_FILENAME']) . DIRECTORY_SEPARATOR . $local_file;
    print($file . "?v=" . filemtime($local_file));
}
?>

<head>
    <title>ODM QPCR Analyzer</title>
    <link rel="shortcut icon" href="<?php mfile("/favicon.ico") ?>" />

    <link rel="icon" type="image/png" href="<?php mfile("/images/favicon-16x16.png") ?>" sizes="16x16" />
    <link rel="icon" type="image/png" href="<?php mfile("/images/favicon-32x32.png") ?>" sizes="32x32" />
    <link rel="icon" type="image/png" href="<?php mfile("/images/favicon-96x96.png") ?>" sizes="96x96" />
    <link rel="icon" type="image/png" href="<?php mfile("/images/favicon-192x192.png") ?>" sizes="192x192" />

    <link rel="apple-touch-icon" sizes="57x57" href="<?php mfile("/images/favicon-57x57.png") ?>" />
    <link rel="apple-touch-icon" sizes="60x60" href="<?php mfile("/images/favicon-60x60.png") ?>" />
    <link rel="apple-touch-icon" sizes="72x72" href="<?php mfile("/images/favicon-72x72.png") ?>" />
    <link rel="apple-touch-icon" sizes="76x76" href="<?php mfile("/images/favicon-76x76.png") ?>" /> 
    <link rel="apple-touch-icon" sizes="114x114" href="<?php mfile("/images/favicon-114x114.png") ?>" />
    <link rel="apple-touch-icon" sizes="120x120" href="<?php mfile("/images/favicon-120x120.png") ?>" />
    <link rel="apple-touch-icon" sizes="144x144" href="<?php mfile("/images/favicon-144x144.png") ?>" />
    <link rel="apple-touch-icon" sizes="152x152" href="<?php mfile("/images/favicon-152x152.png") ?>" />
    <link rel="apple-touch-icon" sizes="180x180" href="<?php mfile("/images/favicon-180x180.png") ?>" />
    <link rel="apple-touch-icon" sizes="256x256" href="<?php mfile("/images/favicon-256x256.png") ?>" />

    <meta name="msapplication-TileImage" content="<?php mfile("/images/favicon-270x270.png") ?>" />

    <meta name="viewport" content="width=device-width, initial-scale=1" />

    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="/formstone/dist/js/core.js"></script>
    <script src="/formstone/dist/js/upload.js"></script>
    <script src="<?php mfile("/multiple-emails/multiple-emails.js") ?>"></script>
    <script src="https://cdn.jsdelivr.net/npm/js-cookie@3.0.0/dist/js.cookie.min.js"></script>
    <link href="/multiple-emails/multiple-emails.css" rel="stylesheet">
    <link href="/formstone/dist/css/upload.css" rel="stylesheet">
    <link href="<?php mfile("/css/main.css") ?>" rel="stylesheet">
</head>
<body>

<script>
    allowed_ext = [ "xlsx", "pdf" ];
    sid = generateSessionID();
    is_processing = false;

    currentDriveAccount = null;
    queryDict = {}
    location.search.substr(1).split("&").forEach(function(item) {queryDict[item.split("=")[0]] = item.split("=")[1]})

    originalDriveParent = "<?php print(get_setting("drive.parent")) ?>";
    originalRecipients = <?php print(json_encode(get_setting("recipients", []))) ?>;

    function getCurrentUser() {
        return Cookies.get("user") || "";
    }

    function setCurrentUser(user) {
        Cookies.set("user", user, {expires:10*365});
    }

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
        $(".start_all").on("click", onStart);
        $(".run_analyzer").on("click", onRunAnalyzer);
        $(".reset_form").on("click", onResetForm);

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

        $.post({
            url: "/action.php?user=" + getCurrentUser(),
            data: {"sid" : sid, "action" : "updateSettings", "settings" : { "drive" : {"parent" : folderID}} },
            dataType: "json",
            async: false,
            success: driveFolderChanged,
            error: (response) => {
                alert("Error settings drive folder: " + JSON.stringify(response));
            },
        });
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
        $.post({
            url: "/action.php?user=" + getCurrentUser(),
            data: {"sid" : sid, "action" : "updateSettings", "settings" : { "recipients" : recipients.length ? recipients : null } },
            dataType: "json",
            async: false,
            success: recipientsSaved,
            error: (response) => {
                updateRecipientsUI();
                alert("Error settings default recipients: " + JSON.stringify(response));
            },
        });
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

    function onBeforeSend(formData, file) {
        console.log("Before Send");

        if (!validExtension(file.name))
            return false;

        // formData.append("test_field", "test_value");
        // return (file.name.indexOf(".jpg") < -1) ? false : formData; // cancel all jpgs
        formData.append("sid", sid);
        formData.append("action", "uploadFile");
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
        // if (!force && $(".reset_form").hasClass("disabled")) {
        //     return;
        // }

        $.ajax({
            url: "/action.php?user=" + getCurrentUser(),
            data: {"sid" : sid, "action" : "deleteCurrentData" },
            dataType: "json",
            async: true
        });

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
        // if ($(".run_analyzer").hasClass("disabled")) {
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
            alert("You must select a Google Drive account if \"Update Google Drive versions\" is selected.");
            return;
        }

        //  Collect all file names that have been uploaded
        var files = [];
        var file_els = $(".form").find(".filelist.complete").find("li").not(".error").find(".file");
        for (var i=0; i<file_els.length; i++) {
            files.push($(file_els[i]).text());
        }
        
        $.ajax({
            url: "/action.php?user=" + getCurrentUser(),
            data: {
                "sid" : sid, 
                "action" : "runAnalyzer", 
                "to_emails" : emails, 
                "files" : files, 
                "split_by_site" : split_by_site, 
                "output_format" : output_format,
                "update_remote" : update_remote,
                },
            dataType: "json",
            success: analyzerStarted,
            error: (response) => {
                alert("Error running analyzer. " + JSON.stringify(response));
                is_processing = false; 
                updateFormstoneUI();
            },
            async: true
        });
        updateFormstoneUI();
    }

    function updateFormstoneUI() {
        showProcessing(is_processing);
        queued_errors = $(".form").find(".filelist.queue").find("li").find(".error").length;
        complete_errors = $(".form").find(".filelist.complete").find("li").find(".error").length;
        queued = $(".form").find(".filelist.queue").find("li").not(".error").length;
        complete = $(".form").find(".filelist.complete").find("li").not("error").length;
        if (is_processing || queued > 0 || complete == 0) {
            $(".run_analyzer").prop("disabled", true);
        } else {
            $(".run_analyzer").prop("disabled", false);
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
            $(".reset_form").prop("disabled", true);
        } else {
            $(".reset_form").removeClass("disabled");
            $(".reset_form").prop("disabled", false);
        }
    }

    function showError(response) {
        if (!response)
            return false;
        
        if (typeof response == 'string')
            try {
                response = JSON.parse(response);
            } catch {

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
            } catch {
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
        });
    }

    function signInCallback(authResult) {
        if (authResult['code']) {
            // Send the code to the server
            $.ajax({
                type: 'POST',
                url: '/register.php?user=' + getCurrentUser(),
                // Always include an `X-Requested-With` header in every AJAX request,
                // to protect against CSRF attacks.
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                contentType: 'application/octet-stream; charset=utf-8',
                success: function(result) {
                    // Handle or verify the server response.
                    if (showError(result)) {
                        return;
                    }
                    try {
                        result = JSON.parse(result);
                    } catch (e) {
                        alert(result);
                    }
                    updateDriveUI(result["email"]);
                },
                error: function(result) {
                    showError(result);
                },
                processData: false,
                data: authResult['code']
            });
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

    function updateUserUI() {
        $('.current-user').text(getCurrentUser() || "");
    }

    $(document).ready(() => {
        if (getCurrentUser() == "") {
            $(".select-user-container").show();
            $(".main-container").hide();
        } else {
            $(".select-user-container").hide();
            $(".main-container").show();
        }

        // Reset cookie expiry
        setCurrentUser(getCurrentUser());
        updateRemoteUI();
        updateUserUI();
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

        $(".user-select").on("click", function(el) {
            setCurrentUser($(this).attr("data-username"));
        });

        $('#changeUserButton').on("click", function() {
            setCurrentUser("");
            location.reload();            
        })

        $('#signinButton').on("click", function() {
            // signInCallback defined in step 6.
            auth2.grantOfflineAccess().then(signInCallback);
        });

        $('#update_remote').on("change", updateRemoteUI);

        $.get(
            "/get_settings.php?user=" + getCurrentUser(),
            function(result) {
                try {
                    result = JSON.parse(result);
                } catch (e) {
                    alert(result);
                }
                email = result["email"];
                updateDriveUI(email);
            },
        )
    });

    function updateDriveUI(email) {
        currentDriveAccount = email;
        if (email) {
            $(".signin-details").text(email);
            $("#signinButton").attr("value", "Change Drive Account");
        } else {
            $(".signin-details").text("None");
            $("#signinButton").attr("value", "Sign In With Google");
        }
    }

    function getCurrentDriveAccount() {
        $(".signin-details")
    }

    //////////////////////////////////////////////////////////////////////////////

</script>
<script src="https://apis.google.com/js/client:platform.js?onload=driveStart" async defer></script>

<div class="select-user-container" style="display: none;">
    <div class="select-user-container-inner">
        <h1>Select User</h1>
        
        <?php 
        $users = get_known_users();
        if (count($users) > 0) {
            print("<ul>");
            foreach ($users as $userinfo) {
                $username = $userinfo["username"];
                print('<li><a href="/" class="user-select" data-username="' . $username . '">' . $username . '</a></li>');
            }
            print("</ul>");
        } else {
            print("Empty");
        }
        ?>
    </div>
</div>

<div class="main-container" style="display: none;">
<form action="#" method="GET" class="form form-container">
    <div class="uploader-container">
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
            <h5>Uploaded:</h5>
            <div class="uploaded_empty filelists_empty">Empty</div>
            <ol class="filelist complete"></ol>
            <h5>Queued:</h5>
            <div class="queued_empty filelists_empty">Empty</div>
            <ol class="filelist queue"></ol>
            <!-- <span class="start_all button">Start Upload</span> -->
            <div class="analyzer_buttons">
            <input type="button" class="run_analyzer button" value="Run Analyzer" />
            <input type="button" class="reset_form button" value="Clear Files" />
            </div>
            <!-- <span class="cancel_all">Cancel All</span> -->
        </div>
        </div>
    </div>
    <div class="options-container">
    <div class="options-container-inner">
    <h1>Settings</h1>
    <div class="line"></div>
    <b>User:</b> <span class="options-title-data current-user"></span><br />
    <div class="settings-suboptions">
    <input type="button" id="changeUserButton" class="button settings-button" value="Change User" />
    </div>
    <div class="line"></div>

    <div class="options-title">Recipient Email Addresses:</div>
    <div class="settings-suboptions settings-subgrouped">
    <input type="text" id="emails" placeholder="Email" value='<?php print(json_encode(get_setting("recipients", []))) ?>' />
    <div class="options-notes">Only approved email addresses are allowed. To approve your email contact <?php print(contactLink()) ?>.</div>
    <input type="button" id="save-recipient-emails" class="button settings-button" value="Save Emails as Defaults" />
    <input type="button" id="reset-recipient-emails" class="button settings-button" value="Reset" />
    </div>

    <div class="line"></div>

    <input type="checkbox" id="split_by_site" class="disable-update-remote" /> <label style="display:inline-block" for="split_by_site" class="disable-update-remote">Split output by site</label>

    <div class="line"></div>

    <input type="radio" id="ottawa_long_format" value="ottawa_long_format" name="output_format" class="disable-update-remote" checked /> <label class="disable-update-remote" style="display:inline-block" for="ottawa_long_format">Ottawa Long format</label><br />
    <input type="radio" id="ottawa_wide_format" value="ottawa_wide_format" name="output_format" /> <label style="display:inline-block" for="ottawa_wide_format">Ottawa Wide format</label><br />
    <input type="radio" id="ottawa_b117_format" value="ottawa_b117_format" name="output_format" /> <label style="display:inline-block" for="ottawa_b117_format">Ottawa B117 format</label><br />

    <div class="line"></div>

    <input type="checkbox" id="update_remote" /> <label style="display:inline-block" for="update_remote">Update on Google Drive</label>

    <div class="settings-suboptions settings-subgrouped" id="update_remote_contents">
    <div class="options-title">Google Drive Account:</div>
    <div class="settings-suboptions">
    <span class="signin-details">Retrieving details...</span><br />
    <input type="button" id="signinButton" class="button settings-button" value="Sign In With Google" disabled />
    </div>
    <div class="line"></div>
    <div class="options-title">Save in Drive Folder ID:</div>
    <div class="settings-suboptions">
    <input type="text" id="drive-folder-id" placeholder="Folder ID" value="<?php print(get_setting("drive.parent")); ?>" /><br />
    <input type="button" id="drive-folder-id-save" class="button settings-button" value="Save" />
    <input type="button" id="drive-folder-id-reset" class="button settings-button" value="Reset" />
    <input type="button" id="drive-folder-id-view" class="button settings-button" value="View Folder" />
    </div>
    </div>

    <div class="line"></div>

    <b>Lambda Version:</b> <span class="options-title-data"><?php print(QPCR_VERSION); ?></span><br />
    <div class="line"></div>
    </div>
    </div>
</form>
</div>

<div class="footer">
</div>

</body>
</html>
