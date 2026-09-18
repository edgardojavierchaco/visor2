
"""
This module has been moved to :py:mod:`pyrocko.io.datacube`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.datacube\n')
    sys.stderr.write('           -> should now use: pyrocko.io.datacube\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.datacube\n')
    sys.stderr.write('              -> should now use: pyrocko.io.datacube\n\n')
    raise ImportError('Pyrocko module "pyrocko.datacube" has been renamed to "pyrocko.io.datacube".')

from pyrocko.io.datacube import *
