
"""
This module has been moved to :py:mod:`pyrocko.io.segy`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.segy\n')
    sys.stderr.write('           -> should now use: pyrocko.io.segy\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.segy\n')
    sys.stderr.write('              -> should now use: pyrocko.io.segy\n\n')
    raise ImportError('Pyrocko module "pyrocko.segy" has been renamed to "pyrocko.io.segy".')

from pyrocko.io.segy import *
