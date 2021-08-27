#%%
"""
# gdrive_utils.py

Library for downloading from and uploading to Google Drive.

The Google Drive credentials and access token must be set with one of the set_creds and set_token functions (eg. set_creds_file and
set_token_file).

All remote paths are relative to either the user's root folder, or the folder ID specified by drive_set_root_id (or in
some cases the root_id passed to a function)

## Usage

set_creds_and_token_files(creds_file, token_file)
local_file = drive_download("/remote/path/to/file.xlsx")
drive_upload(local_file, "/remote/path/to/file_copy.xlsx")

## Installation

Install Google client library:

    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import os
import io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import json

SCOPES = [
    'https://www.googleapis.com/auth/drive',
]

_credentials_file = "credentials.json"
_token_file = "token.json"
_credentials_data = None
_token_data = None

_drive_root_id = None

# See set_allow_flow: If True, then when we authenticate the user we allow blocking for user input if required (eg. to
# get the access/refresh token). If False then we raise an exception if user input is required, so we can continue execution.
allow_flow = True

def set_creds_file(credentials):
    global _credentials_file, _credentials_data
    _credentials_file = credentials
    if _credentials_file:
        _credentials_data = None

def set_token_file(token):
    global _token_file, _token_data
    _token_file = token
    if _token_file:
        _token_data = None

def set_creds_data(credentials):
    """Set credentials, either as a dictionary or a JSON-encoded string.
    """
    global _credentials_file, _credentials_data
    _credentials_data = credentials
    if _credentials_data:
        _credentials_file = None
        if isinstance(_credentials_data, str):
            _credentials_data = json.loads(_credentials_data)

def set_token_data(token):
    """Set access token, either as a dictionary or a JSON-encoded string.
    """
    global _token_file, _token_data
    _token_data = token
    if _token_data:
        _token_file = None
        if isinstance(_token_data, str):
            _token_data = json.loads(_token_data)

def set_creds_and_token_files(credentials, token):
    set_creds_file(credentials)
    set_token_file(token)

def set_creds_and_token_data(credentials, token):
    set_creds_data(credentials)
    set_token_data(token)

def set_partial_token_data_file(tokens_file):
    """See set_partial_token_data: Sets the partial token using a file instead of an already loaded JSON string or dictionary.
    """
    with open(tokens_file, "r") as f:
        set_partial_token_data(f.read())

def set_partial_token_data(tokens):
    """Set the access token data, using a dictionary or JSON-encoded string that contains the "token" and "refresh_token" fields, but
    not other required fields such as the client_id. The missing fields are instead retrieved from the credentials set by
    a set_creds call.
    """
    global _credentials_datam, _credentials_file
    if isinstance(tokens, str):
        tokens = json.loads(tokens)
    if _credentials_data is None:
        with open(_credentials_file, "r") as f:
            creds = json.load(f)
    else:
        creds = _credentials_data
    token_data = creds["installed"] if "installed" in creds else creds["web"]
    token_data.update(tokens)
    set_token_data(token_data)

def set_allow_flow(allow):
    """Disable or enable app login flow, which requires user input. If set to False then rather than waiting for user input
    a RuntimeError exception is raised.
    """
    global allow_flow
    allow_flow = allow

def test_access_token():
    """Test if the access token and credentials are valid and will us to access the Google Drive service.

    Returns
    -------
    True if we can access Google Drive service, False if we can't (typically means the access token has
    expired and needs refreshing).
    """
    try:
        _ = get_drive_service()
        return True
    except:
        return False

def get_drive_service():
    """Get a Google Drive service for making Google Drive API calls.
    """
    creds = None
    if _token_file and os.path.exists(_token_file):
        creds = Credentials.from_authorized_user_file(_token_file, SCOPES)
    elif _token_data:
        creds = Credentials.from_authorized_user_info(_token_data, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not allow_flow:
                raise RuntimeError("Token or credentials not available for OAuth2.0")
            if _credentials_file:
                flow = InstalledAppFlow.from_client_secrets_file(_credentials_file, SCOPES)
            elif _credentials_data:
                flow = InstalledAppFlow.from_client_config(_credentials_data, SCOPES)
            creds = flow.run_local_server(port=0)
        if _token_file:
            try:
                with open(_token_file, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Error saving OAuth2.0 token to disk: {e}")
    
    service = build("drive", "v3", credentials=creds)
    return service

def drive_get_root_id():
    """Get the folder ID of the current root to use for all Google Drive access. This is either the
    user's account root folder, or the folder set with the previous call to drive_set_root_id.
    """
    global _drive_root_id
    if _drive_root_id:
        return _drive_root_id
    else:
        return get_drive_service().files().get(fileId='root').execute()['id']

def drive_set_root_id(drive_root_id):
    """Set the root folder ID for all Google Drive access. Set to empty/None to use the user's account root folder.
    """
    global _drive_root_id
    _drive_root_id = drive_root_id

def drive_download_from_id(file_id, local_dir, file_name=None):
    """Download the specified file_id from Google Drive. It is saved to the local directory local_dir, either with
    the same filename as the source file, or named file_name if specified.
    """
    if not file_id:
        return None

    file_name = file_name or drive_get_file_name(file_id)
    if file_name is None:
        return None

    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done == False:
        status, done = downloader.next_chunk()
        progress = int(status.progress() * 100)
        print(f"Download {progress}%")
    
    # Save locally
    local_dir = local_dir or ""
    if local_dir:
        os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, file_name)
    with open(local_path, "wb") as f:
        f.write(fh.getbuffer())
    return local_path

def drive_download(path, local_dir, file_name=None, root_id=None):
    """Download the specified file (path) from the current Google Drive account, and save it at local_dir. 
    The path parameter is relative to folder with the specified root_id, or the user's root folder or the root specified in
    drive_set_root_id if root_id is not specified. If file_name is specified then save it with that filename (in local_dir),
    otherwise the filename in path is used.
    """
    return drive_download_from_id(drive_get_file_id(path, root_id), local_dir, file_name=file_name)

def get_mime_type(file):
    """Get the MIME-type of the specified file. It uses the file's extension.

    Currently supported: xlsx, pdf, csv.
    """
    ext = os.path.splitext(file)[1].lower()
    return {
        ".xlsx" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf" : "application/pdf",
        ".csv" : "text/csv",
    }.get(ext, None)

def drive_upload(local_file, remote_file, root_id=None):
    """Upload a file. Specifying root_id as a folder ID will upload to remote_file relative to the new root_id.
    All remote directories to remote_file will be created if they do not exist.
    """
    remote_file_name = os.path.basename(remote_file)
    parent = drive_create_folder(os.path.dirname(remote_file), root_id)
    existing_id = drive_get_file_id(remote_file_name, parent)
    media = MediaFileUpload(local_file, mimetype=get_mime_type(local_file))
    if existing_id is not None:
        file = get_drive_service().files().update(media_body=media, fileId=existing_id).execute()
    else:
        file_metadata = {
            "parents" : [parent],
            "name" : remote_file_name,
        }
        file = get_drive_service().files().create(body=file_metadata, media_body=media, fields="id").execute()
    if file is None:
        return None
    return file.get("id")
    
def drive_get_file_name(file_id):
    """Get the file name of a Google drive file.
    """
    try:
        response = get_drive_service().files().get(fileId=file_id).execute()
    except:
        return None
    return response.get("name", None)

def drive_get_file_id(path, root_id=None):
    """Get the Google file ID of the specified Google Drive file (path).
    """
    files = drive_get_files_in_folder(os.path.dirname(path), root_id)
    if files is None:
        return None
    name = os.path.basename(path)
    matches = [f.get("id", None) for f in files if f.get("name") == name]
    return matches[0] if len(matches) > 0 else None

def drive_get_folder_id(path, root_id=None):
    """Get the Google Drive folder ID of the specified file (path) on Google Drive.
    """
    parent = root_id or drive_get_root_id()
    page_token = None
    service = get_drive_service()
    path_comps = path.split("/")
    # Descend the path one path component at a time. If any component doesn't
    # exist on Google Drive then return None
    while len(path_comps) > 0:
        if not path_comps[0]:
            path_comps.pop(0)
            continue
        found = False

        # List all files in parent
        q = f"'{parent}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
        while True:
            response = service.files().list(q=q, spaces="drive", fields="nextPageToken, files(id, name)", pageToken=page_token).execute()
            # Find the file named path_comps[0]
            for file in response.get("files", []):
                if file.get("name") == path_comps[0]:
                    # Found the directory, continue descent
                    parent = file.get("id")
                    found = True
                    break
            page_token = response.get("nextPageToken", None)
            if page_token is None or found:
                break
        
        if not found:
            return None
        path_comps.pop(0)

    return parent

def drive_get_files_in_folder(path, root_id=None):
    """Get a list of all files in the specified Google Drive path. Each returned element is a
    dictionary with the fields "id", "name", and "parents".
    """
    parent = drive_get_folder_id(path, root_id)
    page_token = None
    service = get_drive_service()
    files = []
    while True:
        q = f"'{parent}' in parents and trashed=false"
        try:
            response = service.files().list(q=q, spaces="drive", fields="nextPageToken, files(id, name, parents)", pageToken=page_token).execute()
        except:
            return None
        page_token = response.get('nextPageToken', None)
        for file in response.get("files", []):
            files.append(file)
        break
    return files

def drive_create_folder(path, root_id=None):
    """Create the specified folder (path) on Google Drive.
    """
    comps = path.split("/")
    parent = root_id or drive_get_root_id()

    # Determine which components in the path already exist. parent is
    # the id of the last one.
    last_exist_idx = -1
    for i in range(len(comps)):
        cur_path = comps[i]
        cur_id = drive_get_folder_id(cur_path, parent)
        if cur_id is None:
            break
        last_exist_idx = i
        parent = cur_id

    # Create folders starting at index last_exist_idx, in parent
    create_folders = comps[last_exist_idx+1:]
    if len(create_folders) == 0:
        return parent    
    for folder in create_folders:
        if not folder:
            continue
        file_metadata = {
            "name" : folder,
            "parents" : [parent],
            "mimeType" : "application/vnd.google-apps.folder",
        }

        file = get_drive_service().files().create(body=file_metadata, fields="id").execute()
        parent = file.get("id")
    
    return parent

def drive_get_user_permission_id():
    """Get the permission ID associated with the current Drive user. This can be used to
    see what types of permissions (eg. write permission) the user has for accessing certain files.
    """
    service = get_drive_service()
    about = service.about().get(fields="user").execute()
    return about["user"]["permissionId"]

def drive_get_user_email_address():
    """Get the current user's email address.
    """
    service = get_drive_service()
    about = service.about().get(fields="user").execute()
    return about["user"]["emailAddress"]

def drive_has_write_permission(file_id):
    """Check if the current user has write permission to the specified Google Drive file ID.
    """
    try:
        user_permission_id = drive_get_user_permission_id()
        service = get_drive_service()
        page_token = None
        while True:
            file_permissions = service.permissions().list(fileId=file_id, fields="nextPageToken, permissions", pageToken=page_token).execute()
            for permissions in file_permissions["permissions"]:
                permission_id = permissions["id"]
                permission_info = service.permissions().get(fileId=file_id, permissionId=permission_id).execute()
                permission_kind =  permission_info["kind"]
                permission_role = permission_info["role"]
                permission_type = permission_info["type"]

                if (permission_id == user_permission_id or permission_type == "anyone") and permission_kind == "drive#permission" and permission_role in ["writer", "owner"]:
                    return True
            page_token = file_permissions.get("nextPageToken", None)
            if page_token is None:
                break
    except Exception as e:
        print(f"EXCEPTION trying to determine if Google user has write permission for file {file_id}")
    
    return False

