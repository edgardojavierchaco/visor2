
"""
This module has been moved to :py:mod:`pyrocko.io.kan`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.kan\n')
    sys.stderr.write('           -> should now use: pyrocko.io.kan\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.kan\n')
    sys.stderr.write('              -> should now use: pyrocko.io.kan\n\n')
    raise ImportError('Pyrocko module "pyrocko.kan" has been renamed to "pyrocko.io.kan".')

from pyrocko.io.kan import *
