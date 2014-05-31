import blinker
from collections import deque
from functools import wraps, partial
from threading import local
import inspect
import sys

from .compat import reraise, itervalues, iteritems, is_nextable

def noop(*_, **dummy):
    pass

class StopIterationWithValue(StopIteration):
    value = None

    def __init__(self, value):
        super(StopIterationWithValue, self).__init__()
        self.value = value

class _PendingRunnable(object):
    def __init__(self, it, parent=None, key=None, callback=None, callback_exc=None):
        self.iterable = it
        self.iteration = 0
        self.parent = parent
        self.key = key
        self.callback = callback
        self.callback_exc = callback_exc
        self.dependency_results = None
        self.dependencies_remaining = 0
        self.exception_to_raise = None
        self.result = None
        self.result_exception = None

    def step(self):
        assert self.iteration >= 0

        self.iteration += 1
        if self.iteration == 1:
            assert self.dependency_results is None and self.exception_to_raise is None
            run_fn = partial(next, self.iterable)
        elif self.exception_to_raise is not None:
            exc, self.exception_to_raise = self.exception_to_raise, None
            run_fn = partial(self.iterable.throw, *exc)
        else:
            run_fn = partial(self.iterable.send, self.dependency_results)

        try:
            requirements = run_fn()
        except StopIterationWithValue as e:
            self.result = e.value
            self.iteration = -1
            return None
        except StopIteration:
            self.iteration = -1
            return None
        except Exception:
            self.result_exception = sys.exc_info()
            self.iteration = -1
            return None

        if requirements is None:
            requirements = []

        dependencies = None
        if isinstance(requirements, dict):
            dependencies = requirements
            self.dependency_results = {}
            self.dependency_completed = partial(self._depencency_completed_list_or_dict, self.iteration)
        elif isinstance(requirements, (list, set, frozenset, tuple)):
            dependencies = dict(enumerate(requirements))
            self.dependency_results = [None] * len(dependencies)
            self.dependency_completed = partial(self._depencency_completed_list_or_dict, self.iteration)
        else:
            dependencies = {'': requirements}
            self.dependency_results = None
            self.dependency_completed = partial(self._dependency_completed_single, self.iteration)

        assert all(is_nextable(dep) for dep in itervalues(dependencies)), \
            inspect.getframeinfo(self.iterable.gi_frame)

        self.dependency_threw = partial(self._dependency_threw, self.iteration)
        self.dependencies_remaining = len(dependencies)
        return dependencies

    def _depencency_completed_list_or_dict(self, iteration, loop, k, v):
        if self.iteration != iteration:
            return

        self.dependency_results[k] = v
        self.dependencies_remaining -= 1
        if self.ready:
            loop.runnable(self)

    def _dependency_completed_single(self, iteration, loop, _, v):
        if self.iteration != iteration:
            return

        self.dependency_results = v
        self.dependencies_remaining -= 1
        if self.ready:
            loop.runnable(self)

    def _dependency_threw(self, iteration, loop, _, type_, value, traceback):
        if self.iteration != iteration:
            return

        self.exception_to_raise = (type_, value, traceback)
        self.iteration += 1
        self.dependencies_remaining = 0

        if self.ready:
            loop.runnable(self)

    dependency_completed = None  # dynamically changed.
    dependency_threw = None

    @property
    def ready(self):
        return self.dependencies_remaining == 0 and getattr(self.iterable, 'ready', True)

LOCAL_ID = 0
def new_local_id():
    global LOCAL_ID
    LOCAL_ID += 1
    return LOCAL_ID

class RunLoop(object):
    def __init__(self):
        self.locals = dict()

        self.run_queue = deque()
        self.total_pending = 0
        self.main_runnable = None

        self.on_queue_exhausted = blinker.Signal()
        self.on_runnable_added = blinker.Signal()
        self.on_iteration = blinker.Signal()

    def run(self, iterable):
        self.main_runnable = self.add(iterable)

        while self.total_pending:
            assert self.run_queue
            self.on_iteration.send()

            self._run_all_runnables()

            if self.total_pending:
                self.on_queue_exhausted.send()

        if self.main_runnable.result_exception:
            reraise(*self.main_runnable.result_exception)
        return self.main_runnable.result

    def add(self, iterable, callback_ok=None, callback_exc=None):
        callback_ok = callback_ok or noop
        callback_exc = callback_exc or noop
        obj = _PendingRunnable(iterable, callback=callback_ok, callback_exc=callback_exc)
        self.total_pending += 1
        if obj.ready:
            self.run_queue.append(obj)

        if hasattr(iterable, 'on_add_to_loop'):
            iterable.on_add_to_loop(self, obj)

        self.on_runnable_added.send(runnable=obj)
        return obj

    def runnable(self, runnable):
        """Notify the context that routine is runnable. This assumes that
        .add() was already called with this iterable."""
        assert isinstance(runnable, _PendingRunnable)
        self.run_queue.append(runnable)

    def _run_all_runnables(self):
        while self.run_queue:
            runnable = self.run_queue.popleft()
            deps = runnable.step()
            if deps is None:
                if runnable.result_exception:
                    runnable.callback_exc(*runnable.result_exception)
                elif runnable.callback is not None:
                    runnable.callback(runnable.result)                    
                    
                self.total_pending -= 1
                continue

            for k, v in iteritems(deps):
                self.add(v,
                         partial(runnable.dependency_completed, self, k),
                         partial(runnable.dependency_threw, self, k))

            if runnable.ready:
                self.run_queue.append(runnable)

class _LocalRunLoop(local):
    loop = None

_CURRENT_RUN_LOOP = _LocalRunLoop()

def current_run_loop():
    return _CURRENT_RUN_LOOP.loop

def runloop_coroutine():
    """Creates a coroutine that gets run in a run loop.

    The run loop will be created if necessary."""
    def wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if _CURRENT_RUN_LOOP.loop:
                return fn(*args, **kwargs)  # Returns the underlying iterable.
            else:
                _CURRENT_RUN_LOOP.loop = loop = RunLoop()
                try:
                    return loop.run(fn(*args, **kwargs))
                finally:
                    _CURRENT_RUN_LOOP.loop = None
        return wrapper
    return wrap

def coro_return(value):
    raise StopIterationWithValue(value)

class _DeferredIterable(object):
    def __init__(self):
        self.value = None
        self.exception = None
        self.ready = False
        self.batch_context = None
        self.runnable = None
        self.on_ready = blinker.Signal()

    def on_add_to_loop(self, context, runnable):
        assert self.batch_context is None

        self.batch_context = context
        self.runnable = runnable

    def set_value(self, value):
        assert not self.ready
        self.ready = True

        self.value = value
        if self.batch_context:
            self.batch_context.runnable(self.runnable)

        self.on_ready.send()

    def set_exception(self, type_, value=None, traceback=None):
        assert not self.ready
        self.ready = True

        self.exception = (type_, value, traceback)
        if self.batch_context:
            self.batch_context.runnable(self.runnable)

        self.on_ready.send()

    def __next__(self):
        coro_return(self.get())
    next = __next__

    def get(self):
        if __debug__:
            if not self.ready:
                raise ValueError(".get() on non-ready deferred.")
        if self.exception is not None:
            reraise(*self.exception)
        return self.value


def deferred():
    assert current_run_loop()
    coro_return(_DeferredIterable())
    yield  # pragma: no cover


def future(iterable):
    """Given an iterable, this returns an object that can be yielded again once
    you want to use it's value. This is useful to "front-load" some expensive
    calls that you don't need the results of immediately.

    Usage:
        thing_later = yield future(thing_resolver())
        ... Do things ...
        thing = yield thing_later


    In addition, this may be used to catch exceptions when doing several actions in parallel:
        a, b, c = yield future(get_a()), future(get_b()), future(get_c())
        try:
            a_thing = yield a
        except ValueError:
            a_thing = None  # it's ok we don't need it anyway

        b_thing, c_thing = yield b, c
    """

    result = yield deferred()
    current_run_loop().add(iterable, result.set_value, result.set_exception)
    coro_return(result)

def wait(deferreds, count=None):
    """iwait(deferreds_or_futures, count=None).

    Waits until up to `count` (or all, if count is None) deferreds to complete. Returns
    the objects that completed. Example:

    a, b, c = yield future(get_a()), future(get_b()), future(get_c())
    first, second = yield wait([a, b, c], count=2)
    # At this point 2/3 of the above futures are complete."""
    if count is None:
        count = len(deferreds)

    assert count <= len(deferreds), 'Waiting on too many deferreds: %s' % (count)

    ready_list = [d for d in deferreds if d.ready]
    # Check if any of the deferreds are ready.

    if len(ready_list) < count:
        wait_deferred = yield deferred()

        for d in deferreds:
            def on_ready(_):
                if wait_deferred.ready:
                    return  # This is mostly necessary for PyPy because weak refs
                            # aren't immediately removed there.

                ready_list.append(d)
                if len(ready_list) >= count:
                    wait_deferred.set_value(True)

            d.on_ready.connect(on_ready, weak=True)

        yield wait_deferred

    assert len(ready_list) == count
    coro_return(ready_list)
