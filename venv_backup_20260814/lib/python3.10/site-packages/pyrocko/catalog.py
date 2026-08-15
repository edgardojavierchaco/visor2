
"""
This module has been moved to :py:mod:`pyrocko.client.catalog`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.catalog\n')
    sys.stderr.write('           -> should now use: pyrocko.client.catalog\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.catalog\n')
    sys.stderr.write('              -> should now use: pyrocko.client.catalog\n\n')
    raise ImportError('Pyrocko module "pyrocko.catalog" has been renamed to "pyrocko.client.catalog".')

from pyrocko.client.catalog import *
