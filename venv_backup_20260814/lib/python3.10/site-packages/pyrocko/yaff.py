
"""
This module has been moved to :py:mod:`pyrocko.io.yaff`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.yaff\n')
    sys.stderr.write('           -> should now use: pyrocko.io.yaff\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.yaff\n')
    sys.stderr.write('              -> should now use: pyrocko.io.yaff\n\n')
    raise ImportError('Pyrocko module "pyrocko.yaff" has been renamed to "pyrocko.io.yaff".')

from pyrocko.io.yaff import *
