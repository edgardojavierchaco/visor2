
"""
This module has been moved to :py:mod:`pyrocko.plot.hudson`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.hudson\n')
    sys.stderr.write('           -> should now use: pyrocko.plot.hudson\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.hudson\n')
    sys.stderr.write('              -> should now use: pyrocko.plot.hudson\n\n')
    raise ImportError('Pyrocko module "pyrocko.hudson" has been renamed to "pyrocko.plot.hudson".')

from pyrocko.plot.hudson import *
