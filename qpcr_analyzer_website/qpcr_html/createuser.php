<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/users.php";

if (isset($_GET["user"])) {
    $user = $_GET["user"];
    $userdir = CREDENTIALS_ROOT . $user . "/";
    @mkdir($userdir, 0777, $recursive=true);
    print("User created: {$user}");
} else {
    print("user GET param must be set to create a new user");
}
?>