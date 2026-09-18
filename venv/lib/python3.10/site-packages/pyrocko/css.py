
"""
This module has been moved to :py:mod:`pyrocko.io.css`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.css\n')
    sys.stderr.write('           -> should now use: pyrocko.io.css\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.css\n')
    sys.stderr.write('              -> should now use: pyrocko.io.css\n\n')
    raise ImportError('Pyrocko module "pyrocko.css" has been renamed to "pyrocko.io.css".')

from pyrocko.io.css import *
