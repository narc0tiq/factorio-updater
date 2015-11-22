import os, posixpath, requests, re, urlparse
import argparse


parser = argparse.ArgumentParser(description="Fetches Factorio update packages (e.g., for headless servers)")
parser.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                    help="Don't download files, just state which updates would be downloaded.")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help="Print URLs and stuff as they happen.")
parser.add_argument('-l', '--list-packages', action='store_true', dest='list_packages',
                    help="Print a list of valid packages (e.g., 'core-linux64', etc.).")
parser.add_argument('-u', '--user',
                    help="Your Factorio updater username, from player-data.json.")
parser.add_argument('-t', '--token',
                    help="Your Factorio updater token, also from player-data.json.")
parser.add_argument('-p', '--package', default='core-linux64',
                    help="Which Factorio package to look for updates for, "
                    "e.g., core-linux64 for a 64-bit Linux Factorio. Use --list-packages to "
                    "fetch an updated list.")
parser.add_argument('-f', '--for-version',
                    help="Which Factorio version you currently have, e.g., 0.12.2.")
parser.add_argument('-O', '--output-path', default='/tmp',
                    help="Where to put downloaded files.")
parser.add_argument('-x', '--experimental', action='store_true', dest='experimental',
                    help="Download experimental versions, too (otherwise only stable updates are considered).")


class DownloadFailed(Exception): pass


glob = { 'verbose': False }

def version_key(v):
    if v is None:
        return []
    return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]


def get_updater_data(user, token):
    payload = {'username': user, 'token': token, 'apiVersion': 2}
    r = requests.get('https://www.factorio.com/updater/get-available-versions', params=payload)
    if glob['verbose']:
        print r.url.replace(token, '<secret>')
    if r.status_code != 200:
        raise DownloadFailed('Could not download version list.', r.status_code)
    return r.json()


def pick_updates(updater_json, factorio_package, from_version, experimental=False):
    latest = [None, None]
    available_updates = {}
    for row in updater_json[factorio_package]:
        if 'from' not in row:
            latest[0] = row['stable']
            continue
        available_updates[row['from']] = row['to']

        latest[1] = max(latest[1], row['to'], key=version_key)

    updates = []

    current_version = from_version
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
    r = requests.get('https://www.factorio.com/updater/get-download-link', params=payload)
    if glob['verbose']:
        print r.url.replace(token, '<secret>')
    if r.status_code != 200:
        raise DownloadFailed('Could not obtain download link.', r.status_code, update)
    return r.json()[0]


def fetch_update(output_path, url):
    fname = posixpath.basename(urlparse.urlsplit(url).path)
    fpath = os.path.join(output_path, fname)
    r = requests.get(url, stream=True, verify=False)
    with open(fpath, 'wb') as fd:
        for chunk in r.iter_content(8192):
            fd.write(chunk)

    print 'Wrote %(fpath)s, apply with `factorio --apply-update %(fpath)s`' % {'fpath': fpath}


def main():
    args = parser.parse_args()
    glob['verbose'] = args.verbose

    j = get_updater_data(args.user, args.token)
    if args.list_packages:
        print 'Available packages:'
        for package in j.keys():
            print "\t", package
        return 0

    updates, latest = pick_updates(j, args.package, args.for_version, args.experimental)

    if not updates:
        message = 'No updates available for version %s' % args.for_version
        if not args.experimental:
            if latest[0]:
                message += ' (latest stable is %s).' % latest[0]
            else:
                message += '.'
            message += ' Did you want `--experimental`?'
        else:
            message += ' (latest experimental is %s).' % latest[1]
        print message
        return 1

    for u in updates:
        if args.dry_run:
            print 'Dry run: would have fetched update from %s to %s.' % (u['from'], u['to'])
        else:
            url = get_update_link(args.user, args.token, args.package, u)
            if url is not None:
                fetch_update(args.output_path, url)


if __name__ == '__main__':
    main()
