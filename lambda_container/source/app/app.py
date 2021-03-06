#%%
# %load_ext autoreload
# %autoreload 2

"""
# app.py

Main Lambda function code for QPCR Analyzer.

The Lambda entry point is the function handler() below.

## Flow

1. handler()
    1. Get settings from the event, and download all input and config files
    2. Run QPCRUpdater on all input files if remote_target is set. For any files that the updater recognizes, it will
       update the remote targets. All other files (that the updater doesn't recognize) will be passed on to the extracter.
    3. Run QPCRExtracter to extract all data from the input.
    4. Run QPCRPopulator to create all the output reports.
    5. Run QPCRUpdater again on the QPCRPopulator output (if remote_target is set), to add any new reports to the remote
       targets.
    6. Create the email with all attachments and send it to the user.
"""

import os
import sys
import shutil
import importlib
from datetime import datetime
import re
import tempfile
import pytz
import traceback
import json
import uuid
import html
from zipfile import ZipFile
import cloud_utils
import gdrive_utils
from emailer import send_email, verify_emails
import yaml
from easydict import EasyDict
import traceback

gdrive_utils.set_allow_flow(False)

from qpcr_populator import QPCRPopulator
from qpcr_extracter import QPCRExtracter
from qpcr_updater import QPCRUpdater
from qpcr_utils import (
    QPCRError,
    cleanup_file_name,
    parse_values,
    )

SEND_EMAIL_ON_ERROR = True
DISABLE_ALL_EMAILS = False
TEMP_DIR = None            # Set to None (preferred) to get a new tempdir with tempfile.gettempdir()
OVERRIDE_RUNID = None      # Set to None (preferred) to create a new unique run ID
DELETE_TEMP_DIR = False     # Set to True (preferred) to delete the temp dir once done
UPLOAD_RESULTS = True      # Set to True to upload outputs to S3 for long-term storage
INCLUDE_STACK_TRACE_ON_ERROR = False  # Set to True to include a stack trace in the email when an error occurs
                                      # Note that for unknown errors the stack trace is ALWAYS included

# Will be retrieved from the passed in parameter "output_debug"
OUTPUT_DEBUG = False

# @TODO: Implement this
DELETE_INPUTS = True       # Set to True to delete the S3 inputs directory

ADMIN_EMAIL = "mwellman@ohri.ca"
DEFAULT_FROM_EMAIL = "ODM QPCR Analyzer <odm@cryotoad.com>"

GOOGLE_DOCS_URL = "https://docs.google.com/spreadsheets/d/{file_id}/"
EXTRACTED_FILE = "extracted-{datetime}-{num:03n}.xlsx"
DEFAULT_POPULATED_OUTPUT_FILE = None #"Data - {site_parent_title}.xlsx"
DEFAULT_EXTRACTER_CONFIG = None #"qpcr_extracter.yaml"
DEFAULT_EXTRACTER_FORMAT_CONFIGS = None
DEFAULT_POPULATOR_CONFIG = None #"qpcr_populator_long-2main-inh.yaml"
DEFAULT_UPDATER_CONFIG = None #"qpcr_updater.yaml"
DEFAULT_QAQC_CONFIG = None #"qaqc_long-2main-inh.yaml"
DEFAULT_POPULATOR_TEMPLATE = None #"qpcr_template_long-2main-inh.xlsx"
DEFAULT_SITES_FILE = None #"qpcr_sites.xlsx"
DEFAULT_SITES_CONFIG = None #"qpcr_sites.yaml"
DEFAULT_EMAIL_TEMPLATE_HTML = "email_template.html"
DEFAULT_EMAIL_TEMPLATE_TEXT = "email_template.txt"
DEFAULT_EMAIL_TEMPLATE_ERROR_HTML = "email_template_error.html"
DEFAULT_EMAIL_TEMPLATE_ERROR_TEXT = "email_template_error.txt"
DEFAULT_OUTPUT_PATH = "s3://odm-qpcr-analyzer/outputs"
DEFAULT_CREDENTIALS_FILE = "credentials.json"

DEFAULT_METHODS_CONFIG = None
DEFAULT_METHODS_FILE = None

DEFAULT_SAMPLEIDS_CONFIG = None
DEFAULT_SAMPLESLOG_CONFIG = None
DEFAULT_SAMPLESLOG_FILE = None

ERROR_SUBJECT = "Error from ODM QPCR Analyzer ({username}, {output_format_description})"
EMAIL_SUBJECT = "QPCR Reports ({username}, {output_format_description})"

RUNDATETIME = None 
RUNID = None 
INSTANCEID = cleanup_file_name("{}-{}".format(datetime.now().astimezone(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d-%H:%M:%S"), uuid.uuid4()))
# The number of times this instance has run. If AWS Lambda reuses a launched instance then we'll increment this. It is for information/debugging
# purposes
INSTANCERUNS = 0
USERNAME = None
OUTPUT_FORMAT = None
OUTPUT_FORMAT_DESCRIPTION = None

INPUTS_ZIP_FILE = "Inputs - {date} - {time}.zip"
EXTRACTED_ZIP_FILE = "Extracted - {date} - {time}.zip"

def make_zip_file(file_name, *files):
    """Make a zip file containing a list of files.
    """
    dir = os.path.dirname(file_name)
    if dir:
        os.makedirs(dir, exist_ok=True)
    with ZipFile(file_name, "w") as zip:
        for file in files:
            if file and os.path.exists(file):
                zip.write(file, os.path.basename(file))

def make_email_lists(items):
    """Make an HTML and plain text list of items, to be used in emails.
    """
    if not items or len(items) == 0:
        return "", ""
    htm = ["<li>{}</li>".format(html.escape(i if i else "\'blank\'")) for i in items]
    htm = "<ul>{}</ul>".format("".join(htm))
    text = [f"    - {i}" for i in items]
    text = "\r\n".join(text)
    return htm, text

def admin_email(admin_email=ADMIN_EMAIL):
    """Get the HTML and plain text of the admin email, to be used in emails.
    """
    return f'<a href=mailto:{admin_email}>{admin_email}</a>', admin_email

def remove_unknown_blocks(text, known_blocks):
    """Remove all blocks in the specified text that is not recognized (ie. is not in known_blocks)

    A block is marked by [[block_name]]block contents[[/block_name]].

    Parameters
    ----------
    text : str
        The text to remove the unknown blocks from.
    known_blocks : list[str]
        A list of all known block names.

    Returns
    -------
    str
        The text with all unknown blocks removed.
    """
    all_tags = re.findall("\\[\\[([A-Za-z_0-9]*)\\]\\]", text)
    for tag in all_tags:
        if tag not in known_blocks:
            text = remove_block(text, tag)
    return text

def parse_email_templates(email_template_html, email_template_text, messages=None, **kwargs):
    """Parse the email templates. We replace all the tags and all the blocks.

    Parameters
    ----------
    email_template_html : str
        The file name of the email template to use for the HTML version of the email.
    email_template_text : str
        The file name of the email template to use for the HTML version of the email.
    messages : list[str|list[str]]
        Additional messages to include in the [[messages]] block of the templates. Each message is a string or
        a list of strings. List of strings will be formatted as HTML list (<ul>) or text lists (- item a\n-item b...)
    kwargs : dict
        All tag values. Tags matching the keys and in curly braces will be replaced in the templates. eg. {settings}, {runtime}...
    """
    if email_template_text:
        with open(email_template_text, "r") as f:
            email_template_text = f.read()
    if email_template_html:
        with open(email_template_html, "r") as f:
            email_template_html = f.read()

    # Setup tag values
    tag_values = {}
    for key, val in kwargs.items():
        if isinstance(val, (list, tuple)):
            # Item 0 is the HTML list, Item 1 is the text list
            tag_values[str(key)] = make_email_lists(val) if len(val) > 0 else None
        else:
            tag_values[str(key)] = make_html_and_text(str(val)) if val else None # str(val) if val else None

    if messages:
        tag_values["messages"] = make_email_messages(*messages)

    if email_template_html:
        email_template_html = remove_unknown_blocks(email_template_html, tag_values.keys())
    if email_template_text:
        email_template_text = remove_unknown_blocks(email_template_text, tag_values.keys())

    # Replace tags in email templates
    for key, val in tag_values.items():
        tag = "{%s}" % key
        if isinstance(val, (list, tuple)):
            val_html, val_text = val[0], val[1]
        else:
            val_html = val_text = val
        if email_template_html:
            if val_html:
                email_template_html = email_template_html.replace(tag, val_html)
            else:
                email_template_html = remove_block(email_template_html, key)
        if email_template_text:
            if val_text:
                email_template_text = email_template_text.replace(tag, val_text)
            else:
                email_template_text = remove_block(email_template_text, key)

    # Remove remaining block tags
    match = f"\\[\\[/?[A-Za-z_0-9]*\\]\\]"
    if email_template_html:
        email_template_html = re.sub(match, "", email_template_html)
    if email_template_text:
        email_template_text = re.sub(match, "", email_template_text)

    return email_template_html or None, email_template_text or None

def remove_block(text, block_tag):
    """Remove the specified block from the template text.
    
    A block is marked by [[block_name]]block contents[[/block_name]].

    Parameters
    ----------
    text : str
        The template text to remove the block from.
    block_tag : str
        The name of the block to remove. We will search for [[block_tag]]contents[[/block_tag]] and remove it.
    """
    return re.sub(f"\\[\\[{block_tag}\\]\\](.|\\r|\\n)*\\[\\[/{block_tag}\\]\\]", "", text, flags=re.MULTILINE)

def add_email(email, emails):
    """Add an email address to a list of email addresses.
    """
    if not email:
        return emails
    
    if isinstance(email, str):
        email = [email]
    
    if emails is None:
        emails = []
    elif isinstance(emails, str):
        emails = [emails]
    
    email = email.copy()
    email.extend(emails)

    return email

def make_html_and_text(txt):
    """Create an HTML and text version of the txt. For the HTML version we replace new lines with <br /> tags.
    """
    htm = txt
    htm = htm.replace("\r\n", "<br />").replace("\n", "<br />")
    return htm, txt

def cast_to_bool(s):
    """Cast the specified value to a bool. It can be a string.
    """
    if isinstance(s, str):
        s = s.lower()
    return s in [True, "t", "true"]

def format_file_name(file, clean_name=True, **kwargs):
    """Format a file name by replacing all tags (eg. {date}) with values.

    Parameters
    ----------
    file : str
        The file name to format. Contains formatting tags passed to str.format
    clean_name : bool
        If True then cleanup the filename by replacing unknown characters, and removing paths by replacing
        backslashes with underscores.
    kwargs : dict
        All the tags and values for passing to str.format. In addition to these we add the tags date=RUNDATETIME(year-month-day),
        time=RUNDATETIME(time), datetime=RUNDATETIME(year and time).
    """
    name = parse_values(file, None,
        date=cleanup_file_name(RUNDATETIME.strftime("%Y-%m-%d")),
        time=cleanup_file_name(RUNDATETIME.strftime("%H:%M:%S")),
        datetime=cleanup_file_name(RUNDATETIME.strftime("%Y-%m-%d_%H:%M:%S")),
        **kwargs)[0]
    file_name = os.path.splitext(name)[0]
    name = "{}{}".format(cleanup_file_name(file_name) if clean_name else file_name, os.path.splitext(name)[1])
    return name

def make_email_messages(*messages):
    """Convert a list of messages (a combination of strings and lists) into HTML and text email contents.

    The strings in messages will be included in the HTML and text as strings, while the lists will be converted
    to HTML (ul) lists and text lists (a list of items). eg. ["Hi", "there", ["Jean-David", "Gauri", "Yusuf", "Doug], "Bye"]
    will be converted to HTML:

        Hi There
        <ul>
        <li>Jean-David</li>
        <li>Gauri</li>
        <li>Yusuf</li>
        <li>Doug</li>
        </ul>
        Bye

    The text version will be similar but without HTML tags.

    Parameters
    ----------
    messages : list[str|list[str]]
        All the messages we want to merge into HTML and text.

    Returns
    -------
    html : str
        The HTML version of all messages combined.
    text : str
        The text version of all messages combined.
    """
    htm = txt = ""

    if not messages or len(messages) == 0:
        return htm, txt

    new_messages = []

    # First combine all consecutive strings
    cur_str = ""
    for idx, message in enumerate(messages):
        if isinstance(message, str):
            space = " " if cur_str else ""
            cur_str = f"{cur_str}{space}{message}"
        else:
            if cur_str:
                new_messages.append(cur_str)
                cur_str = ""
            new_messages.append(message)
    if cur_str:
        new_messages.append(cur_str)

    # Combine all the messages, as a combination of lists and strings.
    prev_type = None
    for idx, msg in enumerate(new_messages):
        if isinstance(msg, (list, tuple)):
            cur_htm, cur_txt = make_email_lists(msg)
            cur_txt = f"\r\n\r\n{cur_txt}"
        elif isinstance(msg, str):
            cur_htm, cur_txt = make_html_and_text(msg)
            if idx > 0:
                cur_txt = f"\r\n\r\n{cur_txt}"
        
        space = ""
        htm = f"{htm}{space}{cur_htm}"
        txt = f"{txt}{space}{cur_txt}"
        # prev_type = type(msg)

    return htm, txt

def format_subject(subject):
    """Create an email subject line by formatting a string.
    """
    return subject.format(username=USERNAME, output_format=OUTPUT_FORMAT, output_format_description=OUTPUT_FORMAT_DESCRIPTION)

def send_error_email(to_emails, email_template_html, email_template_text, messages=None, include_stack_trace=False, **kwargs):
    """Send an error email.
    """
    if not SEND_EMAIL_ON_ERROR or DISABLE_ALL_EMAILS:
        return

    if include_stack_trace:
        stack_trace = traceback.format_exc().strip()        
        attachments = [{
            "contents" : stack_trace,
            "filename" : "stacktrace.txt",
        }]
    else:
        attachments = None
    
    email_html, email_text = parse_email_templates(email_template_html, email_template_text, messages=messages, **kwargs)
    send_email(DEFAULT_FROM_EMAIL, to_emails, format_subject(ERROR_SUBJECT), email_html, email_text, attachments=attachments)

def add_debug_info(info):
    """Add debug info to the passed in list. This includes the Python version number, versions of some packages, Lambda function version,
    and Lambda memory.
    """
    info.append("Python version: {}".format(sys.version_info))

    # Add all available version info of the required packages. Not all will be included,
    # only those whose import package name is the same as the package name in requirements.txt
    with open("requirements.txt", "r") as f:
        reqs = f.read().split("\n")
    new_info = []
    for req in reqs:
        if not req:
            continue
        try:
            module = importlib.import_module(req)
            new_info.append(f"Package {req}: {module.__version__}")
        except:
            # new_info.append(f"Package {req}: <unknown>")
            pass

    if "AWS_LAMBDA_FUNCTION_VERSION" in os.environ:
        new_info.append("Function version: {}".format(os.environ["AWS_LAMBDA_FUNCTION_VERSION"]))
    if "AWS_LAMBDA_FUNCTION_MEMORY_SIZE" in os.environ:
        new_info.append("Memory: {}".format(os.environ["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"]))

    info.extend(new_info)
    print("Added debug info:", new_info)

def handler(event, context):
    """Main handler for the Lambda function.
    """
    global RUNDATETIME, RUNID, INSTANCERUNS, TEMP_DIR, OVERRIDE_RUNID, USERNAME, OUTPUT_FORMAT, OUTPUT_FORMAT_DESCRIPTION, OUTPUT_DEBUG
    INSTANCERUNS += 1
    RUNDATETIME = datetime.now().astimezone(pytz.timezone("US/Eastern"))
    if OVERRIDE_RUNID is None:
        if RUNID is None:
            RUNID = INSTANCEID
        else:
            RUNID = cleanup_file_name("{}-{}".format(RUNDATETIME.strftime("%Y-%m-%d-%H:%M:%S"), uuid.uuid4()))
    else:
        RUNID = OVERRIDE_RUNID

    settings = []
    to_emails = [ADMIN_EMAIL]
    from_email = DEFAULT_FROM_EMAIL
    USERNAME = "<no user>"
    OUTPUT_FORMAT = "<no format>"
    OUTPUT_FORMAT_DESCRIPTION = "<no format>"
    OUTPUT_DEBUG = True
    temp_root = None
    start_time = datetime.now()
    executed_on = RUNDATETIME.strftime("%Y-%m-%d %H:%M:%S")
    email_template_error_text = DEFAULT_EMAIL_TEMPLATE_ERROR_TEXT
    email_template_error_html = DEFAULT_EMAIL_TEMPLATE_ERROR_HTML
    try:
        OUTPUT_DEBUG = event.get("output_debug", False)

        # For informational purposes. We show the settings in the report email.
        settings = event.get("descriptive_settings", [])
        if OUTPUT_DEBUG:
            add_debug_info(settings)
        
        input_files = event.get("inputs", None)
        populated_output_file = event.get("populated_output_file", DEFAULT_POPULATED_OUTPUT_FILE)
        output_path = event.get("output_path", DEFAULT_OUTPUT_PATH)
        to_emails = event.get("to_emails", None)
        from_email = event.get("from_email", DEFAULT_FROM_EMAIL) or DEFAULT_FROM_EMAIL
        USERNAME = event.get("username", USERNAME)
        OUTPUT_FORMAT = event.get("output_format", OUTPUT_FORMAT)
        OUTPUT_FORMAT_DESCRIPTION = event.get("output_format_description", OUTPUT_FORMAT_DESCRIPTION)
        to_emails, unverified_emails = verify_emails(to_emails)
        if len(to_emails) == 0:
            to_emails.append(ADMIN_EMAIL)
        remote_target = event.get("remote_target", None)
        hide_qaqc = event.get("hide_qaqc", False)

        if not input_files:
            raise QPCRError("No input files specified. Please upload some files before running the app.")
        elif not output_path:
            raise QPCRError("No output path specified")
        # elif not to_emails:
        #     raise QPCRError("No destination email address specified.")
        # elif not from_email:
        #     raise QPCRError("No from email specified")

        output_path = os.path.join(output_path, RUNID)
        temp_root = os.path.join(tempfile.gettempdir() if TEMP_DIR is None else TEMP_DIR, RUNID)
        os.makedirs(temp_root, exist_ok=True)
        
        def _download(files, description, exception_on_error=True):
            """Download one or more files. The return result is the local paths of the files from downloading.
            description is just for informational output (ie. if an error occurs).
            """
            if files is None:
                if exception_on_error:
                    raise QPCRError(f"File for {description} was not specified.")
                return None
            if isinstance(files, str):
                files = [files]
            results = []
            for file in files:
                result = cloud_utils.download_file(file, target_dir=temp_root)
                if exception_on_error and not result:
                    error_msg = f"Could not retrieve {description} file: {file}\n\nPlease ensure the file exists."
                    if cloud_utils.is_on_google_drive(file):
                        error_msg += " Since this file resides on Google Drive, make sure you have signed in with Google and your account has access to the file."
                    raise QPCRError(error_msg)
                results.append(result)
            if len(results) == 1:
                return results[0]
            return results

        # Get and set the credentials/tokens for Google Drive
        credentials_file = _download(event.get("credentials_file", DEFAULT_CREDENTIALS_FILE), "credentials file")
        tokens = event.get("tokens", None)
        if credentials_file:
            gdrive_utils.set_creds_file(credentials_file)
        if tokens:
            gdrive_utils.set_partial_token_data(tokens)

        # Download all the files
        print("-"*20)
        print("Downloading files...")
        email_template_text = _download(event.get("email_template_text", None) or DEFAULT_EMAIL_TEMPLATE_TEXT, "Text email template", exception_on_error=False)
        email_template_html = _download(event.get("email_template_html", None) or DEFAULT_EMAIL_TEMPLATE_HTML, "HTML email template", exception_on_error=False)
        email_template_error_text = _download(event.get("email_template_error_text", None) or DEFAULT_EMAIL_TEMPLATE_ERROR_TEXT, "Text error email template", exception_on_error=False)
        email_template_error_html = _download(event.get("email_template_error_html", None) or DEFAULT_EMAIL_TEMPLATE_ERROR_HTML, "HTML error email template", exception_on_error=False)
        sites_file = _download(event.get("sites_file", None) or DEFAULT_SITES_FILE, "site definitions")
        sites_config = _download(event.get("sites_config", None) or DEFAULT_SITES_CONFIG, "sites configuration")
        extracter_config = _download(event.get("extracter_config", None) or DEFAULT_EXTRACTER_CONFIG, "extracter config")
        extracter_format_configs = _download(event.get("extracter_format_configs", None) or DEFAULT_EXTRACTER_FORMAT_CONFIGS, "extracter format configs")
        populator_config = _download(event.get("populator_config", None) or DEFAULT_POPULATOR_CONFIG, "populator config")
        updater_config = _download(event.get("updater_config", None) or DEFAULT_UPDATER_CONFIG, "updater config", exception_on_error=remote_target)
        qaqc_config = _download(event.get("qaqc_config", None) or DEFAULT_QAQC_CONFIG, "QA/QC config")
        populator_template = _download(event.get("populator_template", None) or DEFAULT_POPULATOR_TEMPLATE, "populator template")

        sampleids_config = _download(event.get("sampleids_config", None) or DEFAULT_SAMPLEIDS_CONFIG, "sample IDs config")
        sampleslog_config = _download(event.get("sampleslog_config", None) or DEFAULT_SAMPLESLOG_CONFIG, "samples log config")
        sampleslog_file = _download(event.get("sampleslog_file", None) or DEFAULT_SAMPLESLOG_FILE, "samples log")

        methods_config = _download(event.get("methods_config", None) or DEFAULT_METHODS_CONFIG, "methods config")
        methods_file = _download(event.get("methods_file", None) or DEFAULT_METHODS_FILE, "methods")

        local_input_files = []
        # local_inputed_output_files is all input files (uploaded by the user) that are actually output files
        # (eg. in wide format). In this case we do not process these files, but instead append them to the output
        # on the remote target
        local_inputed_output_files = []

        # Download all input files
        for input_file in input_files:
            local_input_files.append(cloud_utils.download_file(input_file, target_dir=temp_root))

        # Get the updater to determine which input files should be used unmodified to append to the remote_targets.
        # ie. Find the input files that are already in the output format: We will not process these files, instead we will
        # append each row to the correct remote target output file based on its site ID column.
        updater = None
        if remote_target:
            print("-"*20)
            print("Identifying output files...")
            updater = QPCRUpdater(updater_config, 
                populator_config, 
                sites_config=sites_config, 
                sites_file=sites_file)
            is_output_files = updater.check_valid_inputs(local_input_files)

            # local_inputed_output_files: Already in the output format, so don't process these
            # local_input_files: These are real QPCR input files, so we process these
            local_inputed_output_files = [f for f,is_output in zip(local_input_files, is_output_files) if is_output]
            local_input_files = [f for f,is_output in zip(local_input_files, is_output_files) if not is_output]

        # Run extracter
        print("-"*20)
        print("Running extracter...")
        output_file = format_file_name(EXTRACTED_FILE, num=0)
        extracter = QPCRExtracter(
            extracter_config,
            extracter_format_configs)
        merged_extracted_file, extracted_files, raw_files, format_names = extracter.extract(
            local_input_files, 
            os.path.join(temp_root, os.path.dirname(output_file)), 
            os.path.join(temp_root, os.path.dirname(output_file), "raw"), 
            merged_file_name=output_file)

        # Run populator
        print("-"*20)
        print("Running populator...")
        # We add remote_target to the output path because grouping of sites depends on what
        # the output file name and path are. Sites with the same output file are grouped together. remote_target might
        # have tags (eg. {site_id}, {parent_site_title}, etc) that affect the filename and hence the grouop.
        output_file = os.path.join(temp_root, cloud_utils.remove_prefix(remote_target), populated_output_file)
        output_file = format_file_name(output_file, num=0, clean_name=False)
        populated_files = []
        output_files = []
        if merged_extracted_file:
            qpcr = QPCRPopulator(input_file=merged_extracted_file,
                template_file=populator_template, 
                target_file=output_file, 
                overwrite=False, 
                config_file=populator_config, 
                qaqc_config_file=qaqc_config,
                sites_config=sites_config,
                sites_file=sites_file,
                sampleids_config = sampleids_config, 
                sampleslog_config = sampleslog_config, 
                sampleslog_file = sampleslog_file,
                methods_config=methods_config,
                methods_file=methods_file,
                hide_qaqc=hide_qaqc)
            output_files = qpcr.populate()
        populated_files.extend(output_files)

        # Update remote target files on Google Drive with the new output from the populator
        updated_file_urls = []
        if updater is not None:
            print("-"*20)
            print("Updating on Google Drive...")
            _ = updater.update(local_inputed_output_files + populated_files, os.path.join(remote_target, populated_output_file))
            updated_targets = updater.save_and_upload()
            for updated_target in updated_targets:
                file_id = gdrive_utils.drive_get_file_id(cloud_utils.remove_prefix(updated_target))
                file_url = GOOGLE_DOCS_URL.format(file_id=file_id)
                updated_file_urls.append("{}: {}".format(os.path.basename(updated_target), file_url))
                
        # Upload all results to S3, for longer term storage
        if UPLOAD_RESULTS:
            print("-"*20)
            print("Uploading results...")
            upload_files = list(dict.fromkeys([*extracted_files, merged_extracted_file, *populated_files, *raw_files]))
            upload_files = [f for f in upload_files if f]
            for upload_file in upload_files:
                if not upload_file:
                    continue
                if cloud_utils.is_s3(output_path):
                    print(f"Uploading file {upload_file}")
                    try:
                        cloud_utils.upload_file(upload_file, os.path.join(output_path, os.path.basename(upload_file)))
                    except:
                        raise QPCRError(f"Could not upload file to {upload_file}.")
                else:
                    shutil.copy(upload_file, os.path.join(output_path, os.path.basename(upload_file)))

        attachments = populated_files.copy()

        # Create ZIP files of the input files and the files extracted from the BioRad PDFs. We'll attach these
        # to the email.
        print("-"*20)
        print("Creating ZIP files...")
        inputs_zip_file = None
        extracted_zip_file = None
        if len(local_inputed_output_files) > 0 or len(local_input_files) > 0:
            inputs_zip_file = os.path.join(temp_root, "zips", format_file_name(INPUTS_ZIP_FILE))
            make_zip_file(inputs_zip_file, *local_inputed_output_files, *local_input_files)
            attachments.append(inputs_zip_file)
        if len(raw_files) > 0:
            extracted_zip_file = os.path.join(temp_root, "zips", format_file_name(EXTRACTED_ZIP_FILE))
            make_zip_file(extracted_zip_file, *raw_files)
            attachments.append(extracted_zip_file)

        # attachments = list(dict.fromkeys([*populated_files, inputs_zip_file, extracted_zip_file]))
        attachments = list(dict.fromkeys(attachments))  # Will remove duplicates while maintaining order

        end_time = datetime.now()

        # Email results
        print("-"*20)
        print("Sending results...")
        if len(unverified_emails) > 0:
            print("WARNING: Not sending to unverified emails:", ", ".join(unverified_emails))
        if to_emails is not None and to_emails != "" and not DISABLE_ALL_EMAILS:
            input_files_with_format = [os.path.basename(f) for f in local_input_files]
            input_files_with_format = [f"{format_name}: {f}" if format_name else f for f, format_name in zip(input_files_with_format, format_names)]
            template_params = {
                "report_files" : [os.path.basename(f) for f in populated_files if f],
                "input_files" : input_files_with_format + [os.path.basename(f) for f in local_inputed_output_files if f],
                "raw_files" : [os.path.basename(f) for f in raw_files if f],
                "settings" : settings,
                "updated_files" : updated_file_urls,
                "inputs_zip_file" : os.path.basename(inputs_zip_file) if inputs_zip_file else None,
                "raw_zip_file" : os.path.basename(extracted_zip_file) if extracted_zip_file else None,
                "start_time" : start_time,
                "runtime" : end_time - start_time,
                "executed_on" : executed_on,
                "admin_email" : ADMIN_EMAIL,
                "runid" : RUNID,
                "instanceid" : INSTANCEID,
                "instanceruns" : INSTANCERUNS,
            }
            email_html, email_text = parse_email_templates(email_template_html, email_template_text, **template_params)
            send_email(from_email, to_emails, format_subject(EMAIL_SUBJECT), email_html, email_text, attachments)
    except QPCRError as e:
        # Custom errors: Text of the error is a string of a JSON array. Each item in the array is either text or an array
        # of text. The error email will have all text, separated by breaks, and all subarrays converted to pretty lists.
        print(f"Custom exception running app: {e}")
        
        comps = e.args
        if not comps:
            comps = [str(e)]
        end_time = datetime.now()
        print("Sending error email:", comps)
        if ADMIN_EMAIL not in to_emails:
            to_emails.append(ADMIN_EMAIL)
        send_error_email(to_emails, email_template_error_html, email_template_error_text, messages=comps, settings=settings, start_time=start_time, executed_on=executed_on, runtime=end_time - start_time, admin_email=ADMIN_EMAIL, runid=RUNID, instanceid=INSTANCEID, instanceruns=INSTANCERUNS, include_stack_trace=INCLUDE_STACK_TRACE_ON_ERROR)
        return {
            "statusCode" : 500
        }
    except Exception as e:
        # Unknown exception, show the full stack trace
        print(f"Unknown exception running app: {e}")
        traceback.print_exc()
        end_time = datetime.now()
        if ADMIN_EMAIL not in to_emails:
            to_emails.append(ADMIN_EMAIL)
        send_error_email(to_emails, email_template_error_html, email_template_error_text, messages=["Unknown error running app:", str(e)], settings=settings, start_time=start_time, executed_on=executed_on, runtime=end_time - start_time, admin_email=ADMIN_EMAIL, runid=RUNID, instanceid=INSTANCEID, instanceruns=INSTANCERUNS, include_stack_trace=True)
        return {
            "statusCode" : 500
        }
    finally:
        if temp_root and DELETE_TEMP_DIR:
            print(f"Deleting temporary folder {temp_root}")
            shutil.rmtree(temp_root)
        
    print("-"*20)
    print("Finished!")

    return {
        "statusCode" : 200
    }

if __name__ == "__main__" and "get_ipython" in globals():
    # For running in Jupyter notebook as main
    import json
    with open("../../../../event.yaml", "r") as f:
        data = EasyDict(yaml.safe_load(f))
    handler(data, None)
