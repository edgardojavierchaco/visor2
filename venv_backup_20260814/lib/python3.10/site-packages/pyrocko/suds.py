
"""
This module has been moved to :py:mod:`pyrocko.io.suds`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.suds\n')
    sys.stderr.write('           -> should now use: pyrocko.io.suds\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.suds\n')
    sys.stderr.write('              -> should now use: pyrocko.io.suds\n\n')
    raise ImportError('Pyrocko module "pyrocko.suds" has been renamed to "pyrocko.io.suds".')

from pyrocko.io.suds import *
