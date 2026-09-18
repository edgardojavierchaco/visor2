
"""
This module has been moved to :py:mod:`pyrocko.io.sac`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.sacio\n')
    sys.stderr.write('           -> should now use: pyrocko.io.sac\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.sacio\n')
    sys.stderr.write('              -> should now use: pyrocko.io.sac\n\n')
    raise ImportError('Pyrocko module "pyrocko.sacio" has been renamed to "pyrocko.io.sac".')

from pyrocko.io.sac import *
