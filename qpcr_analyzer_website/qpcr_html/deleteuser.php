<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/users.php";

$user = $_GET["user"];
if ($user) {
    $userdir = CREDENTIALS_ROOT . $user . "/";
    @rmdir($userdir);
    print("User deleted: {$user}");
} else {
    print("user GET param must be set to delete a user");
}
?>