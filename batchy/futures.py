from __future__ import absolute_import

import sys
from functools import partial
from threading import Condition

from .hook import add_hook
from .local import RunLoopLocal
from .runloop import runloop_coroutine, deferred, current_run_loop, coro_return

FUTURES_HOOK_PRIORITY = 5

class FuturesManager(object):
    def __init__(self):
        self.pending_futures = set()
        self.finished_queue = []
        self.has_finished_queue = Condition()

    def _on_future_completed(self, d, future):
        with self.has_finished_queue:
            self.finished_queue.append((future, d))
            self.pending_futures.remove(future)
            self.has_finished_queue.notify()

    def add(self, future, d):
        self.pending_futures.add(future)
        future.add_done_callback(partial(self._on_future_completed, d))

        add_hook(FUTURES_HOOK_PRIORITY, self._on_queue_exhausted)

    def _on_queue_exhausted(self):
        current_run_loop().add(self.wait_next())

    @runloop_coroutine()
    def wait_next(self):
        with self.has_finished_queue:
            while not self.finished_queue:
                assert self.pending_futures
                self.has_finished_queue.wait()

            while self.finished_queue:
                future, d = self.finished_queue.pop()

                try:
                    d.set_value(future.result())
                except Exception:
                    d.set_exception(*sys.exc_info())

            if self.pending_futures:
                add_hook(FUTURES_HOOK_PRIORITY, self._on_queue_exhausted)

        coro_return(None)
        yield


class FuturesManagerLocal(RunLoopLocal):
    def initialize(self):
        self.futures_manager = FuturesManager()

FUTURES_MANAGER = FuturesManagerLocal()

@runloop_coroutine()
def future(future):
    d = yield deferred()

    FUTURES_MANAGER.futures_manager.add(future, d)
    coro_return(d)

@runloop_coroutine()
def future_result(f):
    coro_return((yield (yield future(f))))

@runloop_coroutine()
def submit(executor, *args, **kwargs):
    """Sample usage:

    rows = yield submit(thread_pool_executor, do_db_query, query, values)
    """
    coro_return((yield (yield future(executor.submit(*args, **kwargs)))))
