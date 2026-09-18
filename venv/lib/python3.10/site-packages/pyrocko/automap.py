
"""
This module has been moved to :py:mod:`pyrocko.plot.automap`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.automap\n')
    sys.stderr.write('           -> should now use: pyrocko.plot.automap\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.automap\n')
    sys.stderr.write('              -> should now use: pyrocko.plot.automap\n\n')
    raise ImportError('Pyrocko module "pyrocko.automap" has been renamed to "pyrocko.plot.automap".')

from pyrocko.plot.automap import *
