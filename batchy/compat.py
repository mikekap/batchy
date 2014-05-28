import sys
PY3 = sys.version_info[0] == 3

if PY3:
    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    def itervalues(d, *args, **kwargs):
        return iter(d.values(*args, **kwargs))
    def iteritems(d, *args, **kwargs):
        return iter(d.items(*args, **kwargs))

    def is_nextable(o):
        return hasattr(o, '__next__')
else:
    exec("""
def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

    def itervalues(d, *args, **kwargs):
        return d.itervalues(*args, **kwargs)
    def iteritems(d, *args, **kwargs):
        return d.iteritems(*args, **kwargs)

    def is_nextable(o):
        return hasattr(o, 'next')
