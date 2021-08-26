#%%
"""
# emailer.py

Sends emails using AWS SES.

## Usage
    recipients = ["you@example.com", "person@gmail.com"]
    verified_recipients, unverified_recipients = verify_emails(recipients)
    send_email(
        "me@example.com",
        verified_recipients,
        "Hi there this is my subject!", 
        email_html = "<b>Hi this is a message</b>",
        email_text = "Hi this is a message",
        attachments = ["/path/to/attachment.txt", "/path/to/attachment2.zip"],
        aws_region = "us-east-1"
        )

"""

import boto3
from botocore.exceptions import ClientError
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

CHARSET = "UTF-8"

def send_email(sender, dest_emails, subject, email_html, email_text=None, attachments=None, aws_region="us-east-1"):
    """Send a multipart email with both an HTML and/or text part (both are optional), along with
    the specified list of files (list of paths).
    """
    if isinstance(dest_emails, str):
        dest_emails = [dest_emails]
    client = boto3.client("ses", region_name=aws_region)
    response = None
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(dest_emails)

        # Set up the body of the mesage (HTML and text)
        alt = MIMEMultipart("alternative")
        if email_text:
            text = MIMEText(email_text, "plain")
            alt.attach(text)
        if email_html:
            html = MIMEText(email_html, "html")
            alt.attach(html)
        msg.attach(alt)

        # Load and attach attachments
        if attachments:
            attachments = list(dict.fromkeys(attachments))
            for attachment in attachments:
                with open(attachment, "rb") as f:
                    part = MIMEApplication(f.read())
                    part.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment))
                msg.attach(part)

        response = client.send_raw_email(Source=sender, Destinations=dest_emails, RawMessage={"Data" : msg.as_string()})
    except ClientError as e:
        print(e.response["Error"]["Message"])
        raise e
    else:
        print("Email sent to", dest_emails, "with message ID", response["MessageId"] if response is not None else "<none>")


def _get_domain(email):
    """Get the domain of an email address (eg. gmail.com in hello@gmail.com)
    """
    comps = email.split("@")
    if len(comps) != 2:
        return None
    return comps[1]

def verify_emails(emails):
    """Split the list of emails into two lists, one of emails verified as recipients on SES and
    the other of emails not verified on SES. Those that are not verified can not receive emails.

    Parameters
    ----------
    emails : list | tuple | np.ndarray

    Returns
    -------
    list
        List of verified email addresses from emails.
    list
        List of unverified email addresses from emails.
    """
    # Add all identities, including the domains (to account for domain verification)
    if emails is None:
        return [], []

    if isinstance(emails, str):
        emails = [emails]

    identities = []
    for email in emails:
        identities.append(email)
        domain = _get_domain(email)
        if domain:
            identities.append(domain)

    client = boto3.client("ses")
    response = client.get_identity_verification_attributes(
        Identities = identities
    )

    attrs = response["VerificationAttributes"]
    verified = []
    unverified = []

    # Check the status of all emails
    for email in emails:
        entry = None
        domain = _get_domain(email)
        if email in attrs:
            entry = attrs[email]
        elif domain in attrs:
            entry = attrs[domain]
        
        if entry is not None:
            status = entry["VerificationStatus"]
            if status == "Success":
                verified.append(email)
                continue
        
        unverified.append(email)

    return verified, unverified
