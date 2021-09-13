#%%

"""
Cloud utilities.

Mainly for downloading and uploading files.
"""

import boto3
import os
import requests
import tempfile
import gdrive_utils
import re
import shutil

S3_PREFIX = "s3://"
HTTP_PREFIX = "http://"
HTTPS_PREFIX = "https://"
GDRIVE_PREFIX = "gd://"

def is_s3(file):
    return get_prefix(file).lower() == S3_PREFIX.lower()

def is_gdrive(file):
    return get_prefix(file).lower() == GDRIVE_PREFIX.lower()

def is_http_or_https(file):
    return is_http(file) or is_https(file)

def is_http(file):
    return get_prefix(file).lower() == HTTP_PREFIX.lower()

def is_https(file):
    return get_prefix(file).lower() == HTTPS_PREFIX.lower()

def is_local(file):
    return not get_prefix(file)

def bucket_and_key(file):
    comps = file[len(S3_PREFIX):].split("/")
    bucket = comps[0]
    key = "/".join(comps[1:])
    return bucket, key

def remove_prefix(file):
    if not file:
        return ""
    return re.sub("^[A-Za-z]*://", "", file)

def get_prefix(file):
    match = re.search("^[A-Za-z0-9]*://", file)
    return "" if match is None else match[0].lower()

def prefix_and_domain_and_path(file):
    proto = ""
    if is_http(file):
        prefix = HTTP_PREFIX
    elif is_https(file):
        prefix = HTTPS_PREFIX
    elif is_gdrive(file):
        prefix = GDRIVE_PREFIX
    else:
        return None, None, None

    comps = file[len(prefix):].split("/")
    domain = comps[0]
    path = "/".join(comps[1:])

    return prefix, domain, path

def download_file(download_path, target_path=None, target_dir=None, preserve_directory_structure=True):
    """Download a remote file. If it is not remote (ie. not gd, s3, http, or https) and is a local file
    instead, then no downloading occurs, and if target_path or target_dir are set then we copy the
    file to the new location and return that path. If local but target_path and target_dir are not set,
    then we simply return download_path.

    Parameters
    ----------
    download_path : str
        The path of the file to download. Can be s3://, http://, https://, or a path to a local file.
    target_path : str
        If set, then use this as the local filename and path to save to. If None then
        a local path based on download_path will be created. (target_dir is ignored if target_path is
        specified)
    target_dir : str
        Local location to save the file, will be saved with the same filename in download_path. If None 
        then a path in the temporary directory is created based on download_path. (if target_path is set
        then this is ignored)
    preserve_directory_structure : bool
        If True (and target_path is not specified), then the directory path in download_path is preserved in 
        the target_dir (ie. we will create subdirectories to match the directory structure)
    
    Returns
    -------
    str
        Local path where the downloaded file was saved. If an error downloading occurred then None is returned.
    """
    def _get_local_target_path(target_path, remote_path):
        """Get a local path from a remote path, preserving directory structure if required.

        Parameters
        ----------
        target_path : str
            If set, then we'll return this unmodified as the local target path.
        remote_path : str
            The full path of the remote file to retrieve excluding the protocol.
            (eg. for http://domain.com/myfile.xlsx, it should be "download.com/myfile.xlsx")
        
        Returns
        -------
        str
            A path and filename to use to save the remote file locally. If target_path is set then
            this is simply target_path. If it is not set then we create a path rooted in target_dir
            or tempdir (if target_dir is None). If preserve_directory_structure is True then we keep the
            directory structure of remote_path, if it is False we remove the directory structure.
        """
        if target_path is None:
            td = target_dir
            if td is None:
                td = tempfile.gettempdir()
            if preserve_directory_structure:
                target_path = os.path.join(td, os.path.dirname(remote_path), os.path.basename(remote_path))
            else:
                target_path = os.path.join(td, os.path.basename(remote_path))
        return target_path

    if is_s3(download_path):
        print(f"Downloading {download_path}")
        bucket, key = bucket_and_key(download_path)
        target_path = _get_local_target_path(target_path, key)
        print(f"    => {target_path}")
        try:
            if os.path.dirname(target_path):
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
            s3 = boto3.client("s3")
            s3.download_file(bucket, key, target_path)
        except Exception as e:
            print(f"EXCEPTION downloading {download_path}: {e}")
            return None
        return target_path
    elif is_http_or_https(download_path):
        print(f"Downloading {download_path}")
        prefix, domain, path = prefix_and_domain_and_path(download_path)
        target_path = _get_local_target_path(target_path, path)
        print(f"    => {target_path}")
        try:
            if os.path.dirname(target_path):
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
            response = requests.get(download_path)
            if response.status_code == requests.codes.ok:
                with open(target_path, "wb") as f:
                    f.write(response.content)
            else:
                print(f"ERROR downloading {download_path}")
                return None
        except Exception as e:
            print(f"EXCEPTION downloading {download_path}: {e}")
            return None
        return target_path
    elif is_gdrive(download_path):
        print(f"Downloading from Google Drive {download_path}")
        try:
            remote_path = remove_prefix(download_path)
            target_path = _get_local_target_path(target_path, remote_path)
            print(f"    => {target_path}")
            target_path = gdrive_utils.drive_download(remote_path, os.path.dirname(target_path), os.path.basename(target_path))
        except Exception as e:
            print(f"EXCEPTION downloading {download_path}: {e}")
            return None

        return target_path
    else:
        if target_dir is None and target_path is None:
            return download_path

        print(f"Retrieving local file {download_path}")
        try:
            target_path = _get_local_target_path(target_path, download_path)
            print(f"    => {target_path}")
            if target_path != download_path:
                if os.path.dirname(target_path):
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(download_path, target_path)
        except Exception as e:
            print(f"EXCEPTION retrieving and copying local file {download_path}: {e}")
            return None
        return target_path

    return None
    
def upload_file(file_name, upload_path):
    """Upload a local file to the specified S3 or Google Drive path.

    Parameters
    ----------
    file_name : str
        The local file name to upload.
    upload_path : str
        The path to upload to. Must have s3:// or gd:// prefix.
    
    Returns
    -------
    bool
        True if the file was uploaded, False if it could not be uploaded.
    """
    if is_s3(upload_path):
        try:
            bucket, key = bucket_and_key(upload_path)
            s3 = boto3.client("s3")
            s3.upload_file(file_name, bucket, key)
            return True
        except Exception as e:
            print(f"Exception uploading {file_name}: {e}")
            return False
    elif is_gdrive(upload_path):
        try :
            upload_path = remove_prefix(upload_path)
            return gdrive_utils.drive_upload(file_name, upload_path)
        except Exception as e:
            print(f"Exception uploading to Google Drive: {file_name}: {e}")
            return False
    elif get_prefix(upload_path):
        raise ValueError(f"Upload path has unrecognized prefix: {upload_path}")
    else:
        try:
            if os.path.dirname(upload_path):
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            shutil.copy(file_name, upload_path)
            return True
        except Exception as e:
            print(f"Exception uploading {file_name} to local destination {upload_path}: {e}")
            return False

