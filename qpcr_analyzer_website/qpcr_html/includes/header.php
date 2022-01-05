<?php
require_once("includes/database.php");
require_once("includes/utils.php");
safe_session_start();
?>

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
    <link href="<?php mfile("/css/main.css") ?>" rel="stylesheet">
<?php if (USE_RECAPTCHA) { ?>
    <script src="https://www.google.com/recaptcha/api.js?render=6LdCQ6IcAAAAAGbatQO4YdAQ4_EVxkWuzm97k-tJ"></script>
<?php } ?>
