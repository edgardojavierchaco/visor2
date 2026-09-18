
"""
This module has been moved to :py:mod:`pyrocko.io.gcf`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gcf\n')
    sys.stderr.write('           -> should now use: pyrocko.io.gcf\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gcf\n')
    sys.stderr.write('              -> should now use: pyrocko.io.gcf\n\n')
    raise ImportError('Pyrocko module "pyrocko.gcf" has been renamed to "pyrocko.io.gcf".')

from pyrocko.io.gcf import *
