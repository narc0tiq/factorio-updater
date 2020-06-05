This is an aid for [Factorio](http://www.factorio.com/) headless server owners.
It fetches update packages from factorio.com for you, so that you can then apply
the update with minimal downtime.


## Usage ##

This is a Python 2/3 script using a single non-standard library,
[Requests](http://requests.readthedocs.org/en/latest/).

To install the required dependency, you should need do no more than run `pip
install requests` (or, in case of emergency, `easy_install requests`). If this
does not work, you are encouraged to read the linked documentation and try to
figure out what's gone wrong.

---

From there, it's really simple: open a shell on the machine running your
headless server, fetch the updater script, and run it (try it with `--help`
first!). Here's an example session:

```
[narc@odin ~/src/factorio-updater]% python update_factorio.py --help
usage: update_factorio.py [-h] [-d] [-v] [-l] [-u USER] [-t TOKEN]
                          [-p PACKAGE] [-f FOR_VERSION] [-O OUTPUT_PATH]
                          [-a APPLY_TO] [-D] [-x]

Fetches Factorio update packages (e.g., for headless servers)

optional arguments:
  -h, --help            show this help message and exit
  -d, --dry-run         Don't download files, just state which updates would
                        be downloaded.
  -v, --verbose         Print URLs and stuff as they happen.
  -l, --list-packages   Print a list of valid packages (e.g., 'core-
                        linux_headless64', etc.).
  -u USER, --user USER  Your Factorio service username, from player-data.json.
  -t TOKEN, --token TOKEN
                        Your Factorio service token, also from player-
                        data.json.
  -p PACKAGE, --package PACKAGE
                        Which Factorio package to look for updates for, e.g.,
                        'core-linux_headless64' for a 64-bit Linux headless
                        Factorio. Use '--list-packages' to fetch an updated
                        list.
  -f FOR_VERSION, --for-version FOR_VERSION
                        Which Factorio version you currently have, e.g.,
                        '0.12.2'. If empty, query the Factorio binary given in
                        '--apply-to' for its version.
  -O OUTPUT_PATH, --output-path OUTPUT_PATH
                        Where to put downloaded files.
  -a APPLY_TO, --apply-to APPLY_TO
                        Apply the updates using the chosen binary.
  -D, --delete-after-applying
                        Delete update archives after successfully applying
                        their contents. Ignored if '--apply-to' was not
                        provided.
  -x, --experimental    Download experimental versions, too (otherwise only
                        stable updates are considered).
[narc@odin ~/src/factorio-updater]% python3 update_factorio.py -xDa ~/srv/factorio/bin/x64/factorio
Auto-detected starting version as 0.15.10 from binary.
Applying update with `/home/narc/srv/factorio/bin/x64/factorio --apply-update /tmp/core-linux_headless64-0.15.10-0.15.11-update.zip`.
Update applied, deleting temporary file /tmp/core-linux_headless64-0.15.10-0.15.11-update.zip.
Applying update with `/home/narc/srv/factorio/bin/x64/factorio --apply-update /tmp/core-linux_headless64-0.15.11-0.15.12-update.zip`.
Update applied, deleting temporary file /tmp/core-linux_headless64-0.15.11-0.15.12-update.zip.
Applying update with `/home/narc/srv/factorio/bin/x64/factorio --apply-update /tmp/core-linux_headless64-0.15.12-0.15.13-update.zip`.
Update applied, deleting temporary file /tmp/core-linux_headless64-0.15.12-0.15.13-update.zip.
[narc@odin ~/src/factorio-updater]% ls /tmp/core-linux_headless64*
zsh: no matches found: /tmp/core-linux_headless64*
```


## Service username and token ##

The keen-eyed will have noticed the options for `--user` and `--token`. These
allow you to supply a username and token normally used by the Factorio services
(like the in-game updater and authenticated multiplayer). Having them will
allow you to download (and potentially apply) more updates than unauthenticated
checks.

First, how to get them:
* You must have a working (non-headless) Factorio client that you've used for
multiplayer (like, say, the one you're using to play on your headless server).
* You will need to find your
[Factorio user data directory](https://wiki.factorio.com/Application_directory#User_Data_directory).
There are two options for this (unless you've made changes explicitly):
    * If you have the **standalone** download, the working directory is the
    same as your Factorio data. It might be something like `C:\Games\Factorio`, or
    maybe `~/Desktop/Factorio`.
    * If you have the version with an **installer**, or **the Steam version**,
    the working directory will be in your user profile's application data area:
        * On Windows, `%APPDATA%\Factorio`
        * On Linux, `~/.factorio`
        * On OSX, `~/Library/Application Support/factorio`
* From your user data directory, you will need the file named
`player-data.json`. Open it with any editor capable of showing plain text files
(e.g., Notepad).

You are looking for lines like these:

```JSON
    "service-username": "Narc",
    "service-token": "xyz123abc456def789ghijklmnopqr"
```

These are the username and token you can provide.


### Why provide username and token? ###

If you happen to have some desire to download updates for a non-headless
version (not normally recommended, but sometimes needs must), you must
authenticate to be able to see these updates. Here's an example session:

```
[narc@odin ~/src/factorio-updater]% python update_factorio.py -u Narc -t xyz123abc456def789ghijklmnopqr --list-packages
Available packages:
         core-win64
         core-mac
         core-linux_headless64
         core-win32
         core-linux32
         core-linux64
[narc@odin ~/src/factorio-updater]% mkdir update-packages
[narc@odin ~/src/factorio-updater]% python update_factorio.py -u Narc -t xyz123abc456def789ghijklmnopqr -O update-packages -p core-win64 -f 0.14.23 -x
Wrote update-packages/core-win64-0.14.23-0.15.1-update.zip, apply with `factorio --apply-update update-packages/core-win64-0.14.23-0.15.1-update.zip`
Wrote update-packages/core-win64-0.15.1-0.15.2-update.zip, apply with `factorio --apply-update update-packages/core-win64-0.15.1-0.15.2-update.zip`
[...]
Wrote update-packages/core-win64-0.15.12-0.15.13-update.zip, apply with `factorio --apply-update update-packages/core-win64-0.15.12-0.15.13-update.zip`
```

You can now take any Factorio Windows 64-bit, version 0.14.23 and up, and apply the updates from the `update-packages` directory just like the in-game updater would.


## License ##

The source of **Factorio Update Helper** is Copyright 2015-2017 Octav "narc"
Sandulescu. It is licensed under the [MIT license][mit], available in this
package in the file [LICENSE.md](LICENSE.md).

[mit]: http://opensource.org/licenses/mit-license.html


## Statistics ##

1 API key was invalidated during the development of this script.
