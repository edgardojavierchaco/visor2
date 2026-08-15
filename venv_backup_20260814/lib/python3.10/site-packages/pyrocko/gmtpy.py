
"""
This module has been moved to :py:mod:`pyrocko.plot.gmtpy`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gmtpy\n')
    sys.stderr.write('           -> should now use: pyrocko.plot.gmtpy\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gmtpy\n')
    sys.stderr.write('              -> should now use: pyrocko.plot.gmtpy\n\n')
    raise ImportError('Pyrocko module "pyrocko.gmtpy" has been renamed to "pyrocko.plot.gmtpy".')

from pyrocko.plot.gmtpy import *
