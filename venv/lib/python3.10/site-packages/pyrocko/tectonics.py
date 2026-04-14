
"""
This module has been moved to :py:mod:`pyrocko.dataset.tectonics`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.tectonics\n')
    sys.stderr.write('           -> should now use: pyrocko.dataset.tectonics\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.tectonics\n')
    sys.stderr.write('              -> should now use: pyrocko.dataset.tectonics\n\n')
    raise ImportError('Pyrocko module "pyrocko.tectonics" has been renamed to "pyrocko.dataset.tectonics".')

from pyrocko.dataset.tectonics import *
