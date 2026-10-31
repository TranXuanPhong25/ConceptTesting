# Task51: what VR15 adds

Source and results below are from the sealed development census. No new execution,
test input or expected output was generated for this walkthrough.

```python
def remove_vowels(text):
    """remove_vowels is a function that takes string and returns string without vowels."""
    vowels = 'aeiouAEIOU'
    text = text.replace(' ', '')
    return ''.join([char for char in text if char not in vowels])
```

1. The single-parameter public type grammar quotes the first docstring sentence.
   It conditionally assigns builtin-string semantics to the initial `text`. It
   does not infer runtime type from seeing `.replace` or from expected examples.
2. RHS resolution preserves pre-assignment `text`. Builtin string replacement
   returns a string; the assignment chain connects that result to the later filter.
3. Three instances become bindable:

   ```text
   sequence_transform(source=text_before, pattern=' ', replacement='')
      → selective_filter(source=text_after, predicate=char not in vowels)
      → composite: transform_then_filter
   ```

   `text_before/text_after` above are explanatory names. Actual slots both say
   `text` but carry distinct source spans and an assignment-chain receipt.
4. The composite query includes transformation-before-selection properties,
   role names and `transform_flows_to_filter`. BM25 returns the composite,
   selective-filter and sequence-transform templates; all three bind. Direct
   kind lookup returns the same three applicable templates.
5. Composite partitions consider both operations jointly:
   pattern absent with mixed selection; pattern present alongside retained
   content; repeated pattern with repeated retained content; pattern present
   with all remaining elements removed.

The composite's input source is the **receiver of the bound transformation**;
it is not generally guaranteed to be the original function argument. Here the
source chain establishes their relationship. Local filtering can preserve the
selected occurrences while preprocessing has already removed other content.

All partitions remain `planned_not_executed` with `realized=null`. Whether they
are allowed by the task contract, reachable from a valid original input, and
what the expected output should be are separate checks. Vr15 does not require
the vowel table to be incorrect before a partition can be proposed.

Independent source review supports both edges conditional on builtin-string
semantics; it does not validate the whole function or claim bug detection.
[Full packet, including source receipts](WALKTHROUGH_51.json).
