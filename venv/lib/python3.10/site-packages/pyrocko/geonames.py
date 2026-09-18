
"""
This module has been moved to :py:mod:`pyrocko.dataset.geonames`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.geonames\n')
    sys.stderr.write('           -> should now use: pyrocko.dataset.geonames\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.geonames\n')
    sys.stderr.write('              -> should now use: pyrocko.dataset.geonames\n\n')
    raise ImportError('Pyrocko module "pyrocko.geonames" has been renamed to "pyrocko.dataset.geonames".')

from pyrocko.dataset.geonames import *
