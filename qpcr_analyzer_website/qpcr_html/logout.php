<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once "includes/database.php";

safe_session_start();
session_destroy();
// header("location: /login.php");
header("location: /");
exit;

?>