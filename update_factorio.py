#!/usr/bin/env python3

from __future__ import print_function
import os, posixpath, requests, re
import argparse, json
import subprocess
try:
    import urllib.parse as url_parse
except ImportError:
    import urlparse as url_parse


parser = argparse.ArgumentParser(description="Fetches Factorio update packages (e.g., for headless servers)")
parser.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                    help="Don't download files, just state which updates would be downloaded.")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help="Print URLs and stuff as they happen.")
parser.add_argument('-l', '--list-packages', action='store_true', dest='list_packages',
                    help="Print a list of valid packages (e.g., 'core-linux_headless64', etc.).")
parser.add_argument('-u', '--user',
                    help="Your Factorio service username, from player-data.json.")
parser.add_argument('-t', '--token',
                    help="Your Factorio service token, also from player-data.json.")
parser.add_argument('-p', '--package', default='core-linux_headless64',
                    help="Which Factorio package to look for updates for, "
                    "e.g., 'core-linux_headless64' for a 64-bit Linux headless Factorio. "
                    "Use '--list-packages' to fetch an updated list.")
parser.add_argument('-f', '--for-version',
                    help="Which Factorio version you currently have, e.g., '0.12.2'. If empty, "
                    "query the Factorio binary given in '--apply-to' for its version.")
parser.add_argument('-O', '--output-path', default='/tmp',
                    help="Where to put downloaded files.")
parser.add_argument('-a', '--apply-to', dest='apply_to',
                    help="Apply the updates using the chosen binary.")
parser.add_argument('-D', '--delete-after-applying', action='store_true', dest='delete_after_apply',
                    help="Delete update archives after successfully applying their contents. "
                    "Ignored if '--apply-to' was not provided.")
parser.add_argument('-x', '--experimental', action='store_true', dest='experimental',
                    help="Download experimental versions, too (otherwise only stable updates are considered).")


class DownloadFailed(Exception): pass


glob = { 'verbose': False, 'user': '', 'token' : '' }

def version_key(v):
    if v is None:
        return []
    return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]


def get_updater_data(user, token):
    payload = {'username': user, 'token': token, 'apiVersion': 2}
    r = requests.get('https://updater.factorio.com/get-available-versions', params=payload)
    if glob['verbose']:
        print(r.url.replace(token, '<secret>'))
    if r.status_code != 200:
        raise DownloadFailed('Could not download version list.', r.status_code)
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
        print(r.url.replace(token, '<secret>'))
    if r.status_code != 200:
        raise DownloadFailed('Could not obtain download link.', r.status_code, update)
    return r.json()[0]


def fetch_update(output_path, url):
    fname = posixpath.basename(url_parse.urlsplit(url).path)
    fpath = os.path.join(output_path, fname)
    r = requests.get(url, stream=True, verify=False)
    with open(fpath, 'wb') as fd:
        for chunk in r.iter_content(8192):
            fd.write(chunk)
    return fpath


def verbose_aware_exec(exec_args, verbose=False):
    try:
        captured = subprocess.check_output(exec_args, stderr=subprocess.STDOUT)
        if verbose:
            print(captured)
    except subprocess.CalledProcessError as ex:
        print(ex.output)
        raise


def get_username_token(factoriopath):
    with open(os.path.normpath(factoriopath + '/../../../player-data.json')) as data_file:  
        data = json.load(data_file)
    glob['user'] = data["service-username"]
    glob['token'] = data["service-token"]   

def main():
    args = parser.parse_args()
    glob['verbose'] = args.verbose

    if args.user and args.token:
        glob['user'] = args.user
        glob['token'] = args.token
    else:
        if args.apply_to:
            get_username_token(args.apply_to)
            print("No username or token provided, reading from player-data.json")
        else:
            print("Username/Token not available")
            exit()

    j = get_updater_data(glob['user'], glob['token'])
    if args.list_packages:
        print('Available packages:')
        for package in j.keys():
            print("\t", package)
        return 0

    for_version = args.for_version

    if for_version is None and args.apply_to is not None:
        version_output = subprocess.check_output([args.apply_to, "--version"], universal_newlines=True)
        source_version = re.match("Version: (\d+\.\d+\.\d+)", version_output)
        if source_version:
            for_version = source_version.group(1)
            print("Auto-detected starting version as %s from binary." % for_version)

    updates, latest = pick_updates(j, args.package, for_version, args.experimental)

    if not updates:
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
        return 1

    for u in updates:
        if args.dry_run:
            print('Dry run: would have fetched update from %s to %s.' % (u['from'], u['to']))
        else:
            url = get_update_link(glob['user'], glob['token'], args.package, u)
            if url is not None:
                fpath = fetch_update(args.output_path, url)
                if args.apply_to is not None:
                    update_args = [args.apply_to, "--apply-update", fpath]
                    print("Applying update with `%s`." % (" ".join(update_args)))

                    verbose_aware_exec(update_args, args.verbose)

                    if args.delete_after_apply:
                        print('Update applied, deleting temporary file %s.' % fpath)
                        os.unlink(fpath)
                else:
                    print('Wrote %(fpath)s, apply with `factorio --apply-update %(fpath)s`' % {'fpath': fpath})


if __name__ == '__main__':
    main()
