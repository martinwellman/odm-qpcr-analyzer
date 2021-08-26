<?php

require_once "includes/users.php";

$userInfo = get_gdrive_user_info();
$userEmail = $userInfo ? $userInfo->email : NULL;

print(json_encode([
    "email" => $userEmail
]));