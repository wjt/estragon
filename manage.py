#!/usr/bin/env python
# vim: sts=4 sw=4 et
import os
os.environ.setdefault('ESTRAGON_SETTINGS', os.path.join(os.getcwd(), 'settings.py'))
import sys

from flask.ext.script import Manager, Server
from estragon import app

manager = Manager(app)
manager.add_command('runserver', Server(host='::1'))

if __name__ == "__main__":
    if '--threaded' not in sys.argv and '--processes' not in sys.argv:
        sys.argv.append('--threaded')

    manager.run()

