from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

from .batch_coroutine import batch_coroutine, class_batch_coroutine
from .local import RunLoopLocal
from .runloop import runloop_coroutine, coro_return, deferred, future, current_run_loop
from .context import runloop_coroutine_with_context

# This is what you should be using, unless you are really performance sensitive.
coro = runloop_coroutine_with_context
