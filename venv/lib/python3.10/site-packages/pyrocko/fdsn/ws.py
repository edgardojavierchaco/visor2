
"""
This module has been moved to :py:mod:`pyrocko.client.fdsn`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.fdsn.ws\n')
    sys.stderr.write('           -> should now use: pyrocko.client.fdsn\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.fdsn.ws\n')
    sys.stderr.write('              -> should now use: pyrocko.client.fdsn\n\n')
    raise ImportError('Pyrocko module "pyrocko.fdsn.ws" has been renamed to "pyrocko.client.fdsn".')

from pyrocko.client.fdsn import *
