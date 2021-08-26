# ODM QPCR Analyzer Website

The QPCR Analyzer website allows users to upload BioRad files and launch the QPCR Analyzer on AWS Lambda to receive reports by email. The website requires that the QPCR Analyzer Lambda function has already been set up. See [lambda_container](../lambda_container) for details on setting up the Lambda function.

The website will eventually be replaced with a more feature-rich "Conductor", and so little attention to security and feature implementation has been made. The deployed website should be password protected by your web server software, such as Apache or NGINX.

The website is currently deployed on the Cryotoad website at [https://qpcr.cryotoad.com](https://qpcr.cryotoad.com). This site is password protect.

## Installation

Formstone is used for the upload form. To install Formstone, from within the `qpcr_html` directory run:

    git clone \
        --depth 1  \
        --filter=blob:none  \
        --sparse \
        https://github.com/Formstone/Formstone.git
    cd Formstone
    git sparse-checkout set dist

Multiple-emails.js is used to allow users to enter email addresses. To install multiple-emails, from within the `qpcr_html` directory run:

    git clone https://github.com/pierresh/multiple-emails.js.git

The Google API Client and AWS PHP SDK must be installed with [Composer](https://getcomposer.org). To install Composer, from the `qpcr_analyzer_website` directory run:

    php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
    php -r "if (hash_file('sha384', 'composer-setup.php') === '756890a4488ce9024fc62c56153228907f1545c228516cbf63f885e036d37e9a59d27d63f46af1d4d07ee0f76181c7d3') { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;"
    php composer-setup.php
    php -r "unlink('composer-setup.php');"

To instsall the Google API Client and the AWS PHP SDK, from the same `qpcr_analyzer_website` directory, run:

    COMPOSER=../composer.json php composer.phar install --working-dir qpcr_html

## Settings Files

...