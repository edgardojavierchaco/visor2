
"""
This module has been moved to :py:mod:`pyrocko.io.ims`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.ims\n')
    sys.stderr.write('           -> should now use: pyrocko.io.ims\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.ims\n')
    sys.stderr.write('              -> should now use: pyrocko.io.ims\n\n')
    raise ImportError('Pyrocko module "pyrocko.ims" has been renamed to "pyrocko.io.ims".')

from pyrocko.io.ims import *
