
        <script>
            function onLoginSubmit(token) {
                $("#login-form").submit();
            }
        </script>

        <h1>Login</h1>
        <form action="<?php print($_SERVER["SCRIPT_NAME"]) ?>" method="POST" id="login-form" class="form form-container">
        <div class="form-row">
            <label for="username">Username</label>
            <input type="text" name="username" id="username" value="<?php get_param("login") ? print(get_param("login")) : print($username) ?>" />
        </div>
        <div class="space-medium"></div>
        <div class="form-row">
            <label for="password">Password</label>
            <input type="password" name="password" id="password" />
            <?php show_login_errors($login_err) ?>
        </div>
        <div class="space-medium"></div>
        <div class="form-row">
            <input type="submit" value="Login" class="button <?php print_if_recaptcha(ACTION_LOGIN, "g-recaptcha") ?>" data-sitekey="<?php print(RECAPTCHA_V3_SITE_KEY) ?>" data-callback="onLoginSubmit" data-action="<?php print(ACTION_LOGIN) ?>" />
        </div>
        <div class="space-medium"></div>
        Don't have an account? <a href="/register.php">Create a new account</a><br />
        Forgot your password? <a href="/reset_password.php">Reset password</a><br />
        <div class="space-small"></div>
        </form>
