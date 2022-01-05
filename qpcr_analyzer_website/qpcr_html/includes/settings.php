<?php

require_once "settings_values.php";
require_once "database.php";

function get_recaptcha_settings($action) {
    return isset(RECAPTCHA_SETTINGS[$action]) ? RECAPTCHA_SETTINGS[$action] : NULL;
}

function get_recaptcha_setting($action, $setting, $default = NULL) {
    $settings = get_recaptcha_settings($action);
    if (!$settings || !array_key_exists($setting, $settings))
        return $default;

    return $settings[$setting];
}

function uses_recaptcha($action) {
    if (!USE_RECAPTCHA)
        return FALSE;

    // Note: The default is to use reCAPTCHA
    $use = get_recaptcha_setting($action, "USE_RECAPTCHA");
    return $use === NULL ? TRUE : $use;
}

function get_recaptcha_threshold($action) {
    if (!USE_RECAPTCHA)
        return -1;

    $thresh = get_recaptcha_setting($action, "RECAPTCHA_THRESHOLD");
    return $thresh === NULL ? DEFAULT_RECAPTCHA_THRESHOLD : $thresh;
}

function get_setting($key) {
    if (is_array($key)) {
        // Recursively get each key in the array
        $results = [];
        foreach ($key as $curkey) {
            $value = get_setting($curkey);
            array_push($results, $value);
        }
        return $results;
    }

    if (!array_key_exists($key, SETTINGS))
        return NULL;

    $value = SETTINGS[$key];
    if ($key == "QPCR_VERSION")
        $value = is_admin_user() ? get_setting("ADMIN_QPCR_VERSION") : get_setting("USER_QPCR_VERSION");
    if ($key == "OUTPUT_DEBUG")
        $value = is_admin_user();
        
    if (is_string($value)) {
        // Replace all tags: words that are in square brackets. The word is a key in SETTINGS (ie. we call get_setting(word))
        
        // First do custom tags not found in SETTINGS
        if (get_loggedin_user())
            $value = str_replace("[username]", get_loggedin_user(), $value);
        $user_data = get_user_data();
        if (isset($user_data["gdrive_parent"]))
            $value = str_replace("[gdrive_parent]", $user_data["gdrive_parent"], $value);

        $offset = 0;
        while ($offset < strlen($value) && preg_match("/\[[A-Za-z0-9_]*\]/", $value, $matches, 0, $offset)) {
            $match = $matches[0];
            $pos = strpos($value, $match, $offset);
            $key = substr($match, 1, strlen($match)-2);
            if (array_key_exists($key, SETTINGS)) {
                // Replace the tag, and continue finding more tags without advancing the $offset, in case the
                // replacement has its own tags as well.
                $replace = get_setting($key);
                $value = str_replace($match, $replace, $value);
            } else {
                // For unrecognized keys, keep the string unchanged and advance to the next offset.
                $offset = $pos + 1;
            }
        }
    }

    return $value;
}


?>
