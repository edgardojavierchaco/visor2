
"""
This module has been moved to :py:mod:`pyrocko.plot.beachball`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.beachball\n')
    sys.stderr.write('           -> should now use: pyrocko.plot.beachball\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.beachball\n')
    sys.stderr.write('              -> should now use: pyrocko.plot.beachball\n\n')
    raise ImportError('Pyrocko module "pyrocko.beachball" has been renamed to "pyrocko.plot.beachball".')

from pyrocko.plot.beachball import *
