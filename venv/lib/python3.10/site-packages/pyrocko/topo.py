
"""
This module has been moved to :py:mod:`pyrocko.dataset.topo`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.topo\n')
    sys.stderr.write('           -> should now use: pyrocko.dataset.topo\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.topo\n')
    sys.stderr.write('              -> should now use: pyrocko.dataset.topo\n\n')
    raise ImportError('Pyrocko module "pyrocko.topo" has been renamed to "pyrocko.dataset.topo".')

from pyrocko.dataset.topo import *
