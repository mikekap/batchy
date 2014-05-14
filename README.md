Batchy
========

A batching layer for python. For example, before

```python

def fetch_all_post_by_id(ids):
    post_data = get_post_data(ids)
    likes_data = get_likes_data_for_post_ids(ids)
    comment_data = get_comment_data_for_post_ids(ids)

    results = dict.fromkeys(ids)
    for id in ids:
        results[id] = {'post': post_data.get(id),
                       'likes': likes_data.get(id), 
                       'comments': comment_data.get(id)}
    return results
```

But with batchy:

```python

@runloop_coroutine()
def fetch_post_by_id(id):
    result = {}
    result['post'], result['likes'], result['comments'] = \
        yield get_post_data(id), get_likes_data_for_post_id(id), get_comment_data_for_post_ids(id)
    coro_return(result)

# If you really need the full batch version (you shouldn't)
@runloop_coroutine()
def fetch_posts_by_ids(ids):
    results = yield {id: fetch_post_by_id(id) for id in ids}
    coro_return(results)
```

Motivation
-------

Batching calls can be a major performance boost. When you are I/O bound, batching network calls can mean the difference
between 20ms and 400ms. Both memcached and redis support native batching (via get_multi & pipeline, respectively). SQL
does too (via IN queries).

However, writing batched code is hard. Even if you get it right, a slight change to your requirements
can have a huge impact on your factoring. This isn't 1990. It shouldn't be hard.
