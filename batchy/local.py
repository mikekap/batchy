from .runloop import new_local_id, current_run_loop

def _patch(self):
    loop = current_run_loop()
    if loop is None:
        raise RuntimeError('No run loop when accessing run-loop local')

    id_ = object.__getattribute__(self, '_id')
    try:
        object.__setattr__(self, '__dict__', loop.locals[id_])
    except KeyError:
        loop.locals[id_] = d = {'_id': id_}
        object.__setattr__(self, '__dict__', d)

        cls = type(self)
        cls.initialize(self)

class RunLoopLocal(object):
    def __init__(self):
        object.__setattr__(self, '_id', new_local_id())

    def initialize(self):
        pass

    def __getattribute__(self, name):
        _patch(self)
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only" % self.__class__.__name__)

        _patch(self)
        return object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only" % self.__class__.__name__)

        _patch(self)
        return object.__delattr__(self, name)
