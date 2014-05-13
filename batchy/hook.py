import heapq

from .runloop import runloop_coroutine, current_run_loop

class HookManager(object):
    def __init__(self):
        self.hook_queue = []  # (priority, id)
        self.pending_hooks = {}  # id -> function
        current_run_loop().on_queue_exhausted.connect(self._on_queue_exhausted)

    def add(self, id_, function, priority):
        if id_ not in self.pending_hooks:
            self.pending_hooks[id_] = function
            heapq.heappush(self.hook_queue, (-priority, id_))

    @runloop_coroutine()
    def run_next(self):
        _, id_ = heapq.heappop(self.hook_queue)
        function = self.pending_hooks.pop(id_)

        yield function()

    def _on_queue_exhausted(self, _):
        if not self.hook_queue:
            return

        current_run_loop().add(self.run_next())

def add_hook(priority, fn):
    mgr = getattr(current_run_loop(), '_hook_manager', None)
    if not mgr:
        current_run_loop()._hook_manager = mgr = HookManager()

    mgr.add(id(fn), fn, priority)
