
"""
This module has been moved to :py:mod:`pyrocko.io.gse2`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gse2_io_wrap\n')
    sys.stderr.write('           -> should now use: pyrocko.io.gse2\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gse2_io_wrap\n')
    sys.stderr.write('              -> should now use: pyrocko.io.gse2\n\n')
    raise ImportError('Pyrocko module "pyrocko.gse2_io_wrap" has been renamed to "pyrocko.io.gse2".')

from pyrocko.io.gse2 import *
