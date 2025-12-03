
"""
This module has been moved to :py:mod:`pyrocko.dataset.crust2x2`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.crust2x2\n')
    sys.stderr.write('           -> should now use: pyrocko.dataset.crust2x2\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.crust2x2\n')
    sys.stderr.write('              -> should now use: pyrocko.dataset.crust2x2\n\n')
    raise ImportError('Pyrocko module "pyrocko.crust2x2" has been renamed to "pyrocko.dataset.crust2x2".')

from pyrocko.dataset.crust2x2 import *
