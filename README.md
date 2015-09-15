This is an aid for [Factorio](http://www.factorio.com/) headless server owners.
It fetches update packages from factorio.com for you, so that you can then apply
the update with minimal downtime.


## Usage ##

This is a Python 2 script using a single non-standard library,
[Requests](http://requests.readthedocs.org/en/latest/).

To install the required dependency, you should need do no more than run `pip
install requests` (or, in case of emergency, `easy_install requests`). If this
does not work, you are encouraged to read the linked documentation and try to
figure out what's gone wrong.

---

For the script to successfully connect to the Factorio updater API, you will
need two key pieces of information: your updater username and API token. Both
of these can be obtained from a working client copy of Factorio (like, say, the
one you're using to play on your headless server).

Look in your Factorio folder (e.g., `C:\Games\Factorio`), and find (and open)
the file named `player-data.json`. Near the end of the file there will be some
lines that look like this:

```JSON
    "updater-username": "Narc",
    "updater-token": "xyz123abc456def789ghijklmnopqr"
```

You will want to keep both of these for use with the update script.

---

From there, it's really simple: open a shell on the machine running your
headless server, fetch the updater script, and run it. Here's an example
session:

```
[narc@odin ~/src/factorio-updater]% python update_factorio.py --help
usage: update_factorio.py [-h] [-d] [-u USER] [-t TOKEN]
                          [-p {core-linux32,core-linux64,core-mac,core-win32,core-win64}]
                          [-f FOR_VERSION] [-O OUTPUT_PATH] [-x]

Fetches Factorio update packages (e.g., for headless servers)

optional arguments:
  -h, --help            show this help message and exit
  -d, --dry-run         Don't download files, just state which updates would
                        be downloaded.
  -u USER, --user USER  Your Factorio updater username, from player-data.json.
  -t TOKEN, --token TOKEN
                        Your Factorio updater token, also from player-
                        data.json.
  -p {core-linux32,core-linux64,core-mac,core-win32,core-win64}, --package {core-linux32,core-linux64,core-mac,core-win32,core-win64}
                        Which Factorio package to look for updates for, e.g.,
                        core-linux64 for a 64-bit Linux Factorio.
  -f FOR_VERSION, --for-version FOR_VERSION
                        Which Factorio version you currently have, e.g.,
                        0.12.2.
  -O OUTPUT_PATH, --output-path OUTPUT_PATH
                        Where to put downloaded files.
  -x, --experimental    Download experimental versions, too (otherwise only
                        stable updates are considered).
[narc@odin ~/src/factorio-updater]% python update_factorio.py -u Narc -t xyz123abc456def789ghijklmnopqr -p core-linux64 -f 0.12.2 -x
Wrote /tmp/core-linux64-0.12.2-0.12.3-update.zip, apply with `factorio --apply-update /tmp/core-linux64-0.12.2-0.12.3-update.zip`
[narc@odin ~/src/factorio-updater]% cd ~/srv/factorio/bin/x64
[narc@odin ~/srv/factorio/bin/x64]% ./factorio --apply-update /tmp/core-linux64-0.12.2-0.12.3-update.zip
[...stuff happens...]
[narc@odin ~/srv/factorio/bin/x64]% rm /tmp/core-linux64-0.12.2-0.12.3-update.zip
```



## License ##

The source of **Factorio Update Helper** is Copyright 2015 Octav "narc" Sandulescu. It
is licensed under the [MIT license][mit], available in this package in the file
[LICENSE.md](LICENSE.md).

[mit]: http://opensource.org/licenses/mit-license.html


## Statistics ##

1 API key was invalidated during the development of this script.
