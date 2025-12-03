
"""
This module has been moved to :py:mod:`pyrocko.io.stationxml`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.fdsn.station\n')
    sys.stderr.write('           -> should now use: pyrocko.io.stationxml\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.fdsn.station\n')
    sys.stderr.write('              -> should now use: pyrocko.io.stationxml\n\n')
    raise ImportError('Pyrocko module "pyrocko.fdsn.station" has been renamed to "pyrocko.io.stationxml".')

from pyrocko.io.stationxml import *
