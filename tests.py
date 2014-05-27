#!/usr/bin/env python
from datetime import date
import os
import sys

argv = sys.argv
if '-w' not in argv and '--where' not in argv:
    argv[1:1] = ['-w', 'tests']
if '--logging-level' not in argv:
    argv[1:1] = ['--logging-level', 'INFO']

try:
    import nose
except ImportError:
    print('Could not find the nose test runner.')
    sys.exit(1)

print('Running nosetests %s' % ' '.join(argv[1:]))
nose.main(argv=argv)
