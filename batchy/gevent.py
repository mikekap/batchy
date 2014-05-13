from __future__ import absolute_import

from functools import partial
import gevent

from .runloop import runloop_coroutine, deferred, current_run_loop, coro_return
from .hook import add_hook

GEVENT_HOOK_PRIORITY = 5

class GreenletManager(object):
    def __init__(self):
        self.pending_greenlets = []
        self.finished_queue = []

    def _on_greenlet_completed(self, d, greenlet):
        self.finished_queue.append((greenlet, d))
        self.pending_greenlets.remove(greenlet)

    def add(self, greenlet, d):
        self.pending_greenlets.append(greenlet)
        greenlet.rawlink(partial(self._on_greenlet_completed, d))

        add_hook(GEVENT_HOOK_PRIORITY, self._on_queue_exhausted)

    def _on_queue_exhausted(self):
        current_run_loop().add(self.wait_next())

    @runloop_coroutine()
    def wait_next(self):
        while not self.finished_queue:
            assert self.pending_greenlets
            gevent.wait(objects=self.pending_greenlets, count=1)
            # At this point one of the greenlets should have finished and set
            # a value with the callback above. This sort of depends on an
            # implementation detail of rawlink - the notifications are done in
            # FIFO order and we should have registered the _on_greenlet_completed
            # link before getting here. If this ever changes, we can always add
            # a gevent.sleep(0) to make the gevent loop delay exiting this function

        while self.finished_queue:
            greenlet, d = self.finished_queue.pop()

            if greenlet.successful:
                d.set_value(greenlet.get())
            else:
                d.set_exception(greenlet.exception)

        if self.pending_greenlets:
            add_hook(GEVENT_HOOK_PRIORITY, self._on_queue_exhausted)

        yield

@runloop_coroutine()
def _add_greenlet(greenlet):
    d = yield deferred()

    mgr = getattr(current_run_loop(), '_greenlet_manager', None)
    if not mgr:
        current_run_loop()._greenlet_manager = mgr = GreenletManager()

    mgr.add((greenlet, d))
    coro_return(d)

@runloop_coroutine()
def spawn(*args, **kwargs):
    d = yield _add_greenlet(gevent.spawn(*args, **kwargs))
    value = yield d
    coro_return(value)
