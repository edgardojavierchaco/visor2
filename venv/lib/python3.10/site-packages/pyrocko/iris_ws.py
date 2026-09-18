
"""
This module has been moved to :py:mod:`pyrocko.client.iris`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.iris_ws\n')
    sys.stderr.write('           -> should now use: pyrocko.client.iris\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.iris_ws\n')
    sys.stderr.write('              -> should now use: pyrocko.client.iris\n\n')
    raise ImportError('Pyrocko module "pyrocko.iris_ws" has been renamed to "pyrocko.client.iris".')

from pyrocko.client.iris import *
