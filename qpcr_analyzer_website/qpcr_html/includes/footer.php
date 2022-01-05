<div class="footer">
    <div>
        <?php
        $script = $_SERVER["SCRIPT_NAME"];
        ?>
        <a href="/">Home</a><br />
        <?php if (!isset($_SESSION["username"])) { ?>
            <a href="/login.php">Login</a><br />
            <a href="/register.php">Register</a><br />
            <a href="/reset_password.php">Reset Password</a><br />
        <?php } ?>
        <a href="/privacy.php">Privacy Policy</a><br />
    </div>
    <div class="border-left">
        <a href="https://github.com/Big-Life-Lab/ODM" target="_blank">ODM on GitHub</a><br />
        <a href="https://github.com/martinwellman/odm-qpcr-analyzer" target="_blank">QPCR Analyzer on GitHub</a><br />
    </div>
    <div class="border-left">
        <?php if (isset($_SESSION["username"])) { ?>
            You are logged in as <?php print($_SESSION["username"]) ?>, <a href="/logout.php">Logout</a><br />
        <?php } ?>
        Support: <?php print(obfuscate_email(get_setting("CONTACT_EMAIL"))) ?><br />
    </div>
</div>
