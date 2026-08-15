
"""
This module has been moved to :py:mod:`pyrocko.io.rdseed`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.rdseed\n')
    sys.stderr.write('           -> should now use: pyrocko.io.rdseed\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.rdseed\n')
    sys.stderr.write('              -> should now use: pyrocko.io.rdseed\n\n')
    raise ImportError('Pyrocko module "pyrocko.rdseed" has been renamed to "pyrocko.io.rdseed".')

from pyrocko.io.rdseed import *
