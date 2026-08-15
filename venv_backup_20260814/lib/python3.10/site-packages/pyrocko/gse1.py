
"""
This module has been moved to :py:mod:`pyrocko.io.gse1`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gse1\n')
    sys.stderr.write('           -> should now use: pyrocko.io.gse1\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gse1\n')
    sys.stderr.write('              -> should now use: pyrocko.io.gse1\n\n')
    raise ImportError('Pyrocko module "pyrocko.gse1" has been renamed to "pyrocko.io.gse1".')

from pyrocko.io.gse1 import *
