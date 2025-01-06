#!/usr/bin/env python3

import os, posixpath, requests, re, sys
import tempfile
import argparse
import json
import subprocess
import time
from zipfile import ZipFile
import urllib.parse as url_parse
import time


def file_path(string):
    if os.path.isfile(string):
        return string
    else:
        raise Exception(string + " is not a valid path to a file.")

parser = argparse.ArgumentParser(description="Fetches Factorio update packages (e.g., for headless servers)")
parser.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                    help="Don't download files, just state which updates would be downloaded. "
                    "A nonzero exit code indicates no updates were found (or an exception occurred).")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help="Print URLs and stuff as they happen.")
parser.add_argument('-l', '--list-packages', action='store_true', dest='list_packages',
                    help="Print a list of valid packages (e.g., 'core-linux_headless64', etc.).")
parser.add_argument('-c', '--credentials-file', type=file_path, dest='credentials_file',
                    help="Path to server-settings.json or player-data.json, for loading credentials.")
parser.add_argument('-u', '--user',
                    help="Your Factorio service username, from server-settings.json or player-data.json.")
parser.add_argument('-t', '--token',
                    help="Your Factorio service token, also from server-settings.json or player-data.json.")
parser.add_argument('-p', '--package', default='core-linux_headless64',
                    help="Which Factorio package to look for updates for, "
                    "e.g., 'core-linux_headless64' for a 64-bit Linux headless Factorio. "
                    "Use '--list-packages' to fetch an updated list.")
parser.add_argument('-f', '--for-version',
                    help="Which Factorio version you currently have, e.g., '0.12.2'. If empty, "
                    "query the Factorio binary given in '--apply-to' for its version.")
parser.add_argument('-O', '--output-path', default=tempfile.gettempdir(),
                    help="Where to put downloaded files.")
parser.add_argument('-a', '--apply-to', type=file_path, dest='apply_to',
                    help="Apply the updates using the chosen binary.")
parser.add_argument('-D', '--delete-after-applying', action='store_true', dest='delete_after_apply',
                    help="Delete update archives after successfully applying their contents. "
                    "Ignored if '--apply-to' was not provided.")
parser.add_argument('-x', '--experimental', action='store_true', dest='experimental',
                    help="Download experimental versions, too (otherwise only stable updates are considered).")
parser.add_argument('-z', '--verify-zip', action='store_true', dest='verify_zip',
                    help="Verify the zip file after downloading.")
parser.add_argument('-I', '--ignore-existing', action='store_true', dest='ignore_existing_files',
                    help="Ignore files that have already been downloaded, and re-download them. "
                    "Use in case of a broken download that was wrongly retained.")


class DownloadFailed(Exception): pass


glob = { 'verbose': False }

def version_key(v):
    if v is None:
        return []
    return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]


def get_updater_data(user, token):
    payload = {'username': user, 'token': token, 'apiVersion': 2}
    r = requests.get('https://updater.factorio.com/get-available-versions', params=payload)
    if r.status_code != 200:
        raise DownloadFailed('Could not download version list.', r.status_code)
    if glob['verbose']:
        if token is not None:
            print(r.url.replace(token, '<secret>'))
        else:
            print(r.url)
    return r.json()


def pick_updates(updater_json, factorio_package, from_version, experimental=False):
    latest = [None, None]
    available_updates = {}
    current_version = from_version
    updates = []

    # Get latest stable version
    for row in updater_json[factorio_package]:
        if 'from' not in row:
            latest[0] = row['stable']
            continue

    # Get latest experimental version
    if experimental:
        for row in updater_json[factorio_package]:
            if 'from' in row:
                latest[1] = max(latest[1], row['to'], key=version_key)

    # Get available updates
    for row in updater_json[factorio_package]:
        # if from_version >= current_version...
        if 'from' in row and max(row['from'], current_version, key=version_key) == row['from']:
            # ...and not experimental and to_version <= last_stable
            if not experimental and min(row['to'], latest[0], key=version_key) == row['to']:
                # record this update
                available_updates[row['from']] = row['to']
            # ...or if experimental
            elif experimental:
                # record this update
                available_updates[row['from']] = row['to']

    # Create update list
    while current_version in available_updates:
        new_version = available_updates[current_version]
        if not experimental and max(current_version, latest[0], key=version_key) == current_version:
            break

        updates.append({'from': current_version, 'to': new_version})
        current_version = new_version

    return updates, latest


def get_update_link(username, token, package, update):
    payload = {'username': username,
               'token': token,
               'package': package,
               'from': update['from'],
               'to': update['to'],
               'apiVersion': 2}
    r = requests.get('https://updater.factorio.com/get-download-link', params=payload)
    if glob['verbose']:
        if token is not None:
            print(r.url.replace(token, '<secret>'))
        else:
            print(r.url)
    if r.status_code != 200:
        raise DownloadFailed('Could not obtain download link.', r.status_code, update)
    return r.json()[0]


def zip_valid(fpath):
    with ZipFile(fpath,'r') as zf:
        if zf.testzip() is not None:
            zf.close()
            os.unlink(fpath)
            return False
    return True


def fetch_update(output_path, url, ignore_existing_files, verify_zip):
    fname = posixpath.basename(url_parse.urlsplit(url).path)
    fpath = os.path.join(output_path, fname)

    if os.path.isfile(fpath) and ignore_existing_files is not True:
        if verify_zip:
            if zip_valid(fpath):
                if glob['verbose']:
                    print("File %s already exists and is a valid zip file" % fpath)
                return fpath # early out, we must've already downloaded it
            else:
                pass # fall through to try and download it again.
        else:
            if glob['verbose']:
                print("File %s already exists, assuming it's correct..." % fpath)
            return fpath # early out, we must've already downloaded it

    r = requests.get(url, stream=True)

    total_size = int(r.headers.get('content-length', 0)) # get content length
    downloaded_size = 0
    bar_width = 50     # could use os.get_terminal_size().columns to adapt the screen width
    start_time = time.time()  # time of start download
    with open(fpath, 'wb') as fd:
        for chunk in r.iter_content(8192):
            if chunk:
                fd.write(chunk)
                downloaded_size += len(chunk)

                # calculate download speed
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    download_speed = downloaded_size / elapsed_time

            if total_size == 0:
                bar_block = 0
            else:
                bar_block = int(bar_width * downloaded_size / total_size)

            print(f"\r[{'█' * bar_block}{' ' * (bar_width - bar_block)}] {downloaded_size / 2 ** 20:.2f}/{total_size / 2 ** 20:.2f} MiB  {download_speed / 2 ** 20:.2f} MiB/s", end='')

        fd.flush()
        fd.seek(0, os.SEEK_SET)

        print("\nDownload Success")
        if verify_zip:
            if not zip_valid(fd):
                raise RuntimeError('Downloaded file %s was not a valid zip file' % fpath)

    return fpath


def verbose_aware_exec(exec_args, verbose=False):
    try:
        captured = subprocess.check_output(exec_args, stderr=subprocess.STDOUT)
        if verbose:
            print(captured)
    except subprocess.CalledProcessError as ex:
        print(ex.output)
        raise


def find_version(args):
    if args.for_version is not None:
        return args.for_version

    if args.for_version is None and args.apply_to is not None:
        version_output = subprocess.check_output([args.apply_to, "--version"], universal_newlines=True)
        source_version = re.search(r"Version: (\d+\.\d+\.\d+)", version_output)
        if source_version:
            for_version = source_version.group(1)
            print("Auto-detected starting version as %s from binary." % for_version)
            return for_version


def announce_no_updates(args, for_version, latest):
    message = 'No updates available for version %s' % for_version
    if not args.experimental:
        if latest[0]:
            message += ' (latest stable is %s).' % latest[0]
        else:
            message += '.'
        message += ' Did you want `--experimental`?'
    else:
        message += ' (latest experimental is %s).' % latest[1]
    print(message)


def apply_update(args, update):
    if args.dry_run:
        print('Dry run: would have fetched update from %s to %s.' % (update['from'], update['to']))
        return

    url = get_update_link(args.user, args.token, args.package, update)
    if url is None:
        raise RuntimeError('Failed to obtain URL for update from %s to %s.' % (update['from'], update['to']))

    fpath = fetch_update(args.output_path, url, args.ignore_existing_files, args.verify_zip)
    if args.apply_to is None:
        print('Wrote %(fpath)s, apply with `factorio --apply-update %(fpath)s`' % {'fpath': fpath})
        return

    update_args = [args.apply_to, "--apply-update", fpath]
    print("Applying update with `%s`." % (" ".join(update_args)))
    verbose_aware_exec(update_args, args.verbose)

    if os.name == "nt":
        from psutil import process_iter

        print("Waiting for slave process to exit...")
        while any(p.name() == "Factorio.exe" for p in process_iter()):
            # Slave process is still running
            time.sleep(0.5)

    if args.delete_after_apply:
        print('Update applied, deleting temporary file %s.' % fpath)
        os.unlink(fpath)


def parse_credentials(credentials_file: str, user: str, token: str):
    """Get credentials from CLI arguments."""
    if credentials_file is not None:
        try:
            with open(credentials_file, 'r') as f:
                credentials_json = json.load(f)
            user = user or credentials_json.get('username') or credentials_json.get('service-username')
            token = token or credentials_json.get('token') or credentials_json.get('service-token')

            if user is None or token is None:
                print("WARNING: credentials file did not contain "
                      "username/token! Attempting to continue without...")
        except IOError:
            print("Can't read file %(fpath)s" % {'fpath': credentials_json})
            raise
        except json.JSONDecodeError:
            print("Can't decode JSON in %(fpath)s" % {'fpath': credentials_json})
            raise
    return (user, token)


def main():
    args = parser.parse_args()
    glob['verbose'] = args.verbose

    (args.user, args.token) = parse_credentials(args.credentials_file, args.user, args.token)
    j = get_updater_data(args.user, args.token)
    if args.list_packages:
        print('Available packages:')
        for package in j.keys():
            print("\t", package)
        return 0

    for_version = find_version(args)
    if not for_version:
        print("Unable to determine source version. Please provide either a "
            "starting version (with --for-version) or a Factorio binary (with "
            "--apply-to).")
        return 1

    updates, latest = pick_updates(j, args.package, for_version, args.experimental)

    if not updates:
        announce_no_updates(args, for_version, latest)
        # no update should not return "INVALIDARGUMENT", it should return SUCCESS
        return 0

    for u in updates:
        apply_update(args, u)

    # No updates remain; if an update failed, we will have exceptioned
    # out before getting here.
    # In dry-run mode, this simply signifies that updates were found.
    return 0


if __name__ == '__main__':
    sys.exit(main())
