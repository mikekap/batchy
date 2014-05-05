import blinker
from collections import deque
from functools import wraps, partial
from threading import local

class StopIterationWithValue(StopIteration):
    value = None

    def __init__(self, value):
        super(StopIterationWithValue, self).__init__()
        self.value = value

class _PendingRunnable(object):
    def __init__(self, it, parent=None, key=None, callback=None):
        self.iterable = it
        self.parent = parent
        self.key = key
        self.callback = callback
        self.dependency_results = None
        self.dependencies_remaining = 0
        self.result = None
        self.first = True

    def step(self):
        try:
            if self.first:
                assert self.dependency_results is None
                requirements = self.iterable.next()
                self.first = False
            else:
                requirements = self.iterable.send(self.dependency_results)
        except StopIterationWithValue as e:
            self.result = e.value
            return None
        except StopIteration:
            return None

        if requirements is None:
            requirements = []

        dependencies = None
        if isinstance(requirements, dict):
            dependencies = requirements
            self.dependency_results = {}
            self.dependency_completed = self._depencency_completed_list_or_dict
        elif isinstance(requirements, (list, set, frozenset, tuple)):
            dependencies = dict(enumerate(requirements))
            self.dependency_results = [None] * len(dependencies)
            self.dependency_completed = self._depencency_completed_list_or_dict
        else:
            dependencies = {'': requirements}
            self.dependency_results = None
            self.dependency_completed = self._dependency_completed_single

        self.dependencies_remaining = len(dependencies)
        return dependencies

    def _depencency_completed_list_or_dict(self, loop, k, v):
        self.dependency_results[k] = v
        self.dependencies_remaining -= 1
        if self.ready:
            loop.runnable(self)

    def _dependency_completed_single(self, loop, _, v):
        self.dependency_results = v
        self.dependencies_remaining -= 1
        if self.ready:
            loop.runnable(self)

    dependency_completed = None  # dynamically changed.

    @property
    def ready(self):
        return self.dependencies_remaining == 0 and getattr(self.iterable, 'ready', True)

class RunLoop(object):
    def __init__(self):
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

        return self.main_runnable.result

    def add(self, iterable, callback=None):
        obj = _PendingRunnable(iterable, callback=callback)
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
            runnable = self.run_queue.pop()
            deps = runnable.step()
            if deps is None:
                if runnable.callback is not None:
                    runnable.callback(runnable.result)                    

                self.total_pending -= 1
                continue

            for k, v in deps.iteritems():
                self.add(v, partial(runnable.dependency_completed, self, k))

            if runnable.ready:
                self.run_queue.append(runnable)

class _RunLoopLocal(local):
    loop = None

_CURRENT_RUN_LOOP = _RunLoopLocal()

def current_run_loop():
    return _CURRENT_RUN_LOOP.loop

def runloop_coroutine():
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
        self.ready = False
        self.batch_context = None
        self.runnable = None

    def on_add_to_loop(self, context, runnable):
        self.batch_context = context
        self.runnable = runnable

    def set_value(self, value):
        self.value = value
        self.ready = True
        if self.batch_context:
            self.batch_context.runnable(self.runnable)

    def next(self):
        coro_return(self.value)


def deferred():
    assert current_run_loop()
    coro_return(_DeferredIterable())
    yield  # Ignore pylint warnings; this is needed to make the function a generator.

def future(iterable):
    """Given an iterable, this returns an object that can be yielded again once
    you want to use it's value. This is useful to "front-load" some expensive
    calls that you don't need the results of immediately.

    Usage:
        thing_later = yield future(thing_resolver())
        ... Do things ...
        thing = yield thing_later"""

    result = yield deferred()
    current_run_loop().add(iterable, result.set_value)
    coro_return(result)
