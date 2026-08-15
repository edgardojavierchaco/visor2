
"""
This module has been moved to :py:mod:`pyrocko.io.mseed`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.mseed\n')
    sys.stderr.write('           -> should now use: pyrocko.io.mseed\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.mseed\n')
    sys.stderr.write('              -> should now use: pyrocko.io.mseed\n\n')
    raise ImportError('Pyrocko module "pyrocko.mseed" has been renamed to "pyrocko.io.mseed".')

from pyrocko.io.mseed import *
