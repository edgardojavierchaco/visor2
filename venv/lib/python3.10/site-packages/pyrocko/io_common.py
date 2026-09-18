
"""
This module has been moved to :py:mod:`pyrocko.io.io_common`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.io_common\n')
    sys.stderr.write('           -> should now use: pyrocko.io.io_common\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.io_common\n')
    sys.stderr.write('              -> should now use: pyrocko.io.io_common\n\n')
    raise ImportError('Pyrocko module "pyrocko.io_common" has been renamed to "pyrocko.io.io_common".')

from pyrocko.io.io_common import *
