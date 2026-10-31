# Source → concept → template → partition

These examples come from frozen predictions. A concept describes an operation;
it does not assert that the operation is buggy or generate an expected output.

## Task51: remove_vowels (exposed development example)

Relevant source:

```python
vowels = 'aeiouAEIOU'
text = text.replace(' ', '')
return ''.join([char for char in text if char not in vowels])
```

1. Extract `selective_filter` with `source=text`, `element=char`,
   `predicate=char not in vowels`, `result=[char for char in text if char not in vowels]`.
   Every role has a source span; the filter is on line21. Its assignment chain records
   `text = text.replace(' ', '')` on line20.
2. Query uses neutral properties and role names, not the function/variable names:

   ```text
   selective filter
   identity selection
   predicate true retained false removed
   iteration order and occurrence positions retained locally
   source iterable
   element element
   predicate condition
   result sequence
   ```

3. BM25 returns selective filtering, element mapping, frequency aggregation.
   The shared binder accepts only selective filtering; it does not backfill the
   two unbindable candidates.
4. The bound template produces four planned partitions: all predicate true, all
   predicate false, mixed outcomes, repeated elements. Every partition carries
   the concrete role expressions above; `realized=null`, no expected output.
5. `text.replace(...)` is **unknown** because the source lacks a recognized string
   annotation/literal at that receiver. The source chain alone does not justify
   a `sequence_transform → selective_filter` semantic edge. Public prose says the
   function takes a string, but the narrow requirement parser does not interpret
   that sentence; requirement status remains `unknown`.

Consequently this version does not automatically derive preservation of spaces
from the public contract, select a space-bearing input, or expose task51's bug.
Local preservation at the filter does not prove preservation from the original
function argument: a preceding transformation can already remove information.
[Full packet](WALKTHROUGH_51.json).

## Authored example: search result consumed as an index

```python
def f(s: str, q):
    i = s.find(q)
    alias = i
    return s[alias]
```

The extractor produces `position_lookup` and `search_position_indexing`:

```text
position_lookup(source=s, needle=q, position=s.find(q))
    --position_flows_to_index-->
search_position_indexing(search_source=s, needle=q,
                         position=alias, indexed_source=s, result=s[alias])
```

Relation evidence includes the search call, index use and subscript, with alias
assignments retained as source-chain evidence. The relation query includes the
producer kind, relation name and consumer kind before candidate selection.
The template partitions are needle absent with nonempty source, first position,
last position and repeated matches. They are conditional on receiver semantics
and the public contract; no runtime type or reaching input is proven.

A guarded search has the same structural relationship but may make the absent
partition unreachable at the subscript. This is why the output is a plan, not a
coverage claim or defect label. [Full packet](WALKTHROUGH_search_consumed.json).

The typed preprocessing fixture also demonstrates a transformation/filter edge:
[full packet](WALKTHROUGH_filter_preprocess.json). It is an authored engineering
case, not evidence that the same extraction succeeds on task51 or the 113 census.
