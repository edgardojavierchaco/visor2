
"""
This module has been moved to :py:mod:`pyrocko.dataset.crustdb`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.crustdb\n')
    sys.stderr.write('           -> should now use: pyrocko.dataset.crustdb\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.crustdb\n')
    sys.stderr.write('              -> should now use: pyrocko.dataset.crustdb\n\n')
    raise ImportError('Pyrocko module "pyrocko.crustdb" has been renamed to "pyrocko.dataset.crustdb".')

from pyrocko.dataset.crustdb import *
