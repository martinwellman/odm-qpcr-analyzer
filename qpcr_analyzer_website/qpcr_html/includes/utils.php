<?php

require_once("includes/settings.php");

$_RECAPTCHA_STARTEND_BLOCKS = [];

function split_chars($str) {
    $split = "";
    for ($i=0; $i<strlen($str); $i++) {
        $char = $str[$i];
        if (strlen($split) > 0)
            $split .= "+";
        if ($char == "'")
            $split .= "\"{$char}\"";
        else
            $split .= "'{$char}'";
    }
    return $split;
}

function obfuscate($str, $is_email = FALSE) {
    $obfuscated = "";
    for ($i=0; $i<strlen($str); $i++) {
        $char = $str[$i];
        if ($char == "<" || $char == ">") {
            $obfuscated .= $char;
        } else {
            switch (rand(0, $is_email ? 2 : 1)) {
                case 0:
                    $obfuscated .= $char;
                    break;
                case 1:
                    $obfuscated .= "&#" . mb_ord($char, "UTF-8") . ";";
                    break;
                case 2:
                    // Use %num (only works in quotes)
                    $obfuscated .= "%" . strtoupper(base_convert(ord($char), 10, 16));
                    break;
            }
        }
    }
    return split_chars($obfuscated);
}

function obfuscate_email($email, $text = NULL) {
    $text = $text ?? $email;
    $contents = split_chars("<a href='") . "+" . obfuscate("mailto:") . "+" . obfuscate($email, TRUE) . "+" . split_chars("'>") . "+" . obfuscate($text) . "+" . split_chars("</a>");
    
    return "<script>document.write(" . $contents . ");</script><noscript>[Email requires JavaScript]</noscript>";
}

function mfile($file) {
    $local_file = $file;
    if ($local_file[0] == "/")
        $local_file = $_SERVER['DOCUMENT_ROOT'] . $local_file;
    else
        $local_file = dirname($_SERVER['SCRIPT_FILENAME']) . DIRECTORY_SEPARATOR . $local_file;
    print($file . "?v=" . filemtime($local_file));
}

function verify_requested_with() {
    $headers = getallheaders();
    if (!isset($headers["X-Requested-With"]) || !$headers["X-Requested-With"]) {
        exit(403);
    }
}

function get_param($key) {
    if (isset($_POST) && isset($_POST[$key]))
        return $_POST[$key];
    if (isset($_GET) && isset($_GET[$key]))
        return $_GET[$key];
    $ajax = file_get_contents("php://input");
    if ($ajax && isset($ajax[$key]))
        return $ajax[$key];
    return NULL;
}

function clean_name($str) {
    return preg_replace("/[^A-Za-z0-9_\\.\\- ]/i", "_", $str);
}

function dir_size($dir) {
    $size = 0;
    $files = glob(rtrim($dir, "/") . "/*");
    foreach ($files as $file) {
        if (is_file($file)) $size += filesize($file);;
        if (is_dir($file)) $size += dir_size($file);
    }
    return $size;
}

function verify_recaptcha($action, $die_if_failed = true) {
    if (!uses_recaptcha($action))
        return true;

    $recaptcha_response = get_param("g-recaptcha-response");
    if ($recaptcha_response) {
        $data = file_get_contents(RECAPTCHA_URL . "?secret=" . RECAPTCHA_V3_SECRET_KEY . "&response=" . $recaptcha_response);
        $data = json_decode($data);
        if ($data->success && $data->action === $action && $data->score >= get_recaptcha_threshold($action)) {
            return true;
        }        
    }
    if ($die_if_failed)
        die("reCAPTCHA failed!");
    return false;
}

function print_if_recaptcha($action, $value) {
    if (uses_recaptcha($action))
        print($value);
}

function recaptcha_start($action) {
    global $_RECAPTCHA_STARTEND_BLOCKS;
    array_push($_RECAPTCHA_STARTEND_BLOCKS, $action);
    if (uses_recaptcha($action)) 
        print("grecaptcha.ready(function() {\ngrecaptcha.execute(\"" . RECAPTCHA_V3_SITE_KEY . "\", { action : \"{$action}\" }).then(function(token) {\n");
    else
        print("token = null;\n");
}

function recaptcha_end() {
    global $_RECAPTCHA_STARTEND_BLOCKS;
    $action = array_pop($_RECAPTCHA_STARTEND_BLOCKS);
    if (uses_recaptcha($action)) 
        print("});\n});\n");
}

?>