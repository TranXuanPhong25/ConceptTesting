# Python bug concept catalog

Generated from `data/concepts.json`. Templates require a target contract; cards are hypotheses, not confirmed diagnoses.

## py.mutable-default — Mutable argument default leaks state across calls

Category: `state`

**Where:** Function parameters with list, dict, set or another mutable default.
**Preconditions:** The function mutates a default object and callers expect independent calls.

**Where template:** At {location} in {target}, inspect: Function parameters with list, dict, set or another mutable default.

**How:** A default object is created at function definition and reused when the argument is omitted.
**Trigger template:** Call {function} with {first_input}, then {second_input}, omitting {parameter} both times.

**What:** The second call contains state left by the first call.
**Oracle template:** Under {contract}, compare the second result and side effects with a call using a fresh explicit default.

**Applicability:** Shared defaults can be an intentional cache; establish the independence contract first.

**Sources:** [ruff:B006](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/mutable_argument_default.rs#L23-L84) (stable), [bugbear:B006](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L99-L102) (documented), [python:default-arguments](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L338-L391) (python-3.13)

## py.definition-time-call — Definition-time call freezes a supposedly fresh value

Category: `state`

**Where:** A function parameter default contains a function call.
**Preconditions:** The default is expected to change with time, randomness or request context.

**Where template:** At {location} in {target}, inspect: A function parameter default contains a function call.

**How:** The call runs once during definition, rather than once per invocation.
**Trigger template:** Invoke {function} before and after changing {external_state}, while omitting {parameter}.

**What:** Later invocations use an old timestamp, token or object.
**Oracle template:** Under {contract}, check that each invocation observes the required current state or a distinct object.

**Applicability:** Immutable constants and deliberately captured snapshots are valid uses.

**Sources:** [ruff:B008](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/function_call_in_argument_default.rs#L15-L67) (stable), [bugbear:B008](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L111-L115) (documented)

## py.mutable-class-attribute — Instances accidentally share a mutable class attribute

Category: `state`

**Where:** A class body defines a mutable attribute.
**Preconditions:** Instance methods mutate the class attribute without assigning an independent instance value.

**Where template:** At {location} in {target}, inspect: A class body defines a mutable attribute.

**How:** Attribute lookup reaches one class-owned object for several instances.
**Trigger template:** Create {first_instance} and {second_instance}; mutate {attribute} through the first.

**What:** The second instance observes changes intended only for the first.
**Oracle template:** Under {contract}, assert that instance-specific state of the second instance stays unchanged.

**Applicability:** ClassVar registries and explicitly shared caches intentionally share state.

**Sources:** [ruff:RUF012](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/mutable_class_default.rs#L16-L90) (stable)

## py.dataclass-shared-default — Dataclass field defaults share state or fail construction

Category: `state`

**Where:** Dataclass fields contain mutable literals or function-call defaults.
**Preconditions:** A field is intended to be fresh per instance.

**Where template:** At {location} in {target}, inspect: Dataclass fields contain mutable literals or function-call defaults.

**How:** An accepted default is shared; on supported Python versions some mutable defaults instead reject the class definition.
**Trigger template:** Define {dataclass}, then create two instances and mutate {field} on one if definition succeeds.

**What:** Class definition fails, or another instance observes unintended state changes.
**Oracle template:** Under {contract}, check class construction and per-instance field isolation using the documented factory semantics.

**Applicability:** Dataclass version and hashability affect rejection; a function call returning an immutable value can be intentional.

**Sources:** [ruff:RUF008](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/mutable_dataclass_default.rs#L13-L65) (stable), [ruff:RUF009](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/function_call_in_dataclass_default.rs#L19-L66) (stable)

## py.contextvar-shared-default — ContextVar mutable default crosses context boundaries

Category: `state`

**Where:** ContextVar is initialized with a mutable default.
**Preconditions:** Separate contexts read the default without first setting context-local objects.

**Where template:** At {location} in {target}, inspect: ContextVar is initialized with a mutable default.

**How:** Context-local bindings do not copy the one shared default object.
**Trigger template:** Read {context_variable} in two independent contexts; mutate the default in the first.

**What:** The second context sees state from the first context.
**Oracle template:** Under {contract}, assert context isolation after each context initializes its own value.

**Applicability:** A deliberately shared immutable default is safe; context propagation is distinct from object copying.

**Sources:** [ruff:B039](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/mutable_contextvar_default.rs#L13-L59) (stable), [bugbear:B039](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L297-L297) (documented)

## py.fromkeys-shared-value — dict.fromkeys shares one mutable value between keys

Category: `state`

**Where:** dict.fromkeys receives a mutable value.
**Preconditions:** Values for different keys are intended to be independent.

**Where template:** At {location} in {target}, inspect: dict.fromkeys receives a mutable value.

**How:** Every key references the same value object.
**Trigger template:** Build {mapping} for at least two keys and mutate the value at {first_key}.

**What:** The value at a different key also changes.
**Oracle template:** Under {contract}, assert per-key independence and the expected values after mutation.

**Applicability:** Aliasing is valid if the mapping is intentionally a collection of references to one object.

**Sources:** [ruff:RUF024](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/mutable_fromkeys_value.rs#L14-L54) (stable), [bugbear:B046](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L340-L342) (documented), [python:dict](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L5033-L5323) (python-3.13)

## py.repeated-matrix-row — Sequence repetition aliases nested matrix rows

Category: `state`

**Where:** A list of lists is built by multiplying a list containing one mutable row.
**Preconditions:** Rows must be independently mutable.

**Where template:** At {location} in {target}, inspect: A list of lists is built by multiplying a list containing one mutable row.

**How:** Sequence repetition copies references to the row rather than cloning the row.
**Trigger template:** Build {matrix} with at least two rows; change cell {row_index}, {column_index}.

**What:** The same column changes in other rows.
**Oracle template:** Under {contract}, assert exactly the selected cell changes and other rows retain their contents.

**Applicability:** Repeating immutable elements or intentionally shared row objects has different semantics.

**Sources:** [python:matrix-alias](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L1275-L1324) (python-3.13), [python:sequence-operations](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L929-L1132) (python-3.13)

## py.shallow-copy-nested-alias — Shallow copying leaves nested mutable objects shared

Category: `state`

**Where:** list.copy, dict.copy, slicing or copy.copy is used on nested containers.
**Preconditions:** The copy is expected to isolate nested mutations.

**Where template:** At {location} in {target}, inspect: list.copy, dict.copy, slicing or copy.copy is used on nested containers.

**How:** Only the outer container is copied; its nested objects are still referenced.
**Trigger template:** Copy {container}; mutate {nested_path} through the copy.

**What:** The original nested contents change too.
**Oracle template:** Under {contract}, compare the original before and after the nested mutation.

**Applicability:** Deep copying is not always the correct fix; shared nested objects may be part of the contract.

**Sources:** [python:shallow-copy](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L636-L649) (python-3.13), [python:assignment-alias](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L435-L507) (python-3.13)

## py.assignment-is-not-copy — Assignment creates an alias instead of an independent copy

Category: `state`

**Where:** A mutable object is assigned to a second variable.
**Preconditions:** Later code expects the second variable to hold an independent snapshot.

**Where template:** At {location} in {target}, inspect: A mutable object is assigned to a second variable.

**How:** Assignment binds another name to the same object.
**Trigger template:** Bind {alias} to {original}, mutate through either name, then inspect both.

**What:** A snapshot or original input changes unexpectedly.
**Oracle template:** Under {contract}, assert the original input remains equal to its saved contents when mutation is forbidden.

**Applicability:** Two names for one object are normal; a failure requires an independence or non-mutation contract.

**Sources:** [python:assignment-alias](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L435-L507) (python-3.13)

## py.augassign-partial-mutation — Augmented assignment can mutate before raising

Category: `state`

**Where:** An augmented assignment targets a mutable element inside an immutable container.
**Preconditions:** The in-place operation succeeds but storing its result back is prohibited.

**Where template:** At {location} in {target}, inspect: An augmented assignment targets a mutable element inside an immutable container.

**How:** __iadd__ can mutate the inner object before assignment to the outer tuple raises TypeError.
**Trigger template:** Execute {augmented_assignment} on a tuple containing a mutable list, then catch the assignment exception.

**What:** State has changed despite the operation raising an error.
**Oracle template:** Under {contract}, inspect the nested object after failure; do not assume exception implies rollback.

**Applicability:** Python does not promise automatic rollback; only flag an application that relies on it.

**Sources:** [python:augassign-partial-mutation](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L1349-L1433) (python-3.13)

## py.method-cache-retains-self — Caching a method retains instances through cache keys

Category: `state`

**Where:** lru_cache or cache decorates an instance method.
**Preconditions:** The cache outlives instance use and retains keys containing self.

**Where template:** At {location} in {target}, inspect: lru_cache or cache decorates an instance method.

**How:** Cached method entries keep strong references to their instances.
**Trigger template:** Create many {instances}, call {cached_method}, drop external references and inspect the cache or weak references.

**What:** Instances and their resources remain live longer than intended.
**Oracle template:** Under {lifetime_contract}, check bounded cache growth and whether instances become collectible after cache clearing.

**Applicability:** A bounded cache or intentional instance retention may be acceptable; garbage-collection timing alone is not a portable oracle.

**Sources:** [ruff:B019](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/cached_instance_method.rs#L12-L76) (stable), [bugbear:B019](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L194-L197) (documented)

## py.late-bound-closure — Loop closures read the final binding instead of each iteration value

Category: `iteration`

**Where:** A loop creates functions or lambdas that reference a loop variable.
**Preconditions:** The callback is invoked after the variable has been rebound.

**Where template:** At {location} in {target}, inspect: A loop creates functions or lambdas that reference a loop variable.

**How:** A closure reads a binding at call time instead of snapshotting its value at definition time.
**Trigger template:** Create callbacks for at least two distinct {loop_values}; invoke them after the loop.

**What:** Callbacks return the same final value or act on the wrong item.
**Oracle template:** Under {contract}, compare each callback result with the value from its own creation iteration.

**Applicability:** Immediate invocation and explicitly bound defaults or partial arguments can be correct.

**Sources:** [ruff:B023](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/function_uses_loop_variable.rs#L12-L47) (stable), [bugbear:B023](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L217-L219) (documented), [python:late-binding](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L208-L257) (python-3.13)

## py.mutate-while-iterating — Mutation of a live iterable skips elements or raises

Category: `iteration`

**Where:** A loop mutates the list, dictionary, set or live view it is traversing.
**Preconditions:** Mutation affects remaining positions or collection size.

**Where template:** At {location} in {target}, inspect: A loop mutates the list, dictionary, set or live view it is traversing.

**How:** List indices move as elements are removed; dict and set iteration may reject structural changes.
**Trigger template:** Iterate {container} with at least two adjacent removable items; mutate it during traversal.

**What:** Items are skipped, processed unexpectedly, or iteration raises RuntimeError.
**Oracle template:** Under {contract}, compare processed items and final contents against a traversal over a separate snapshot.

**Applicability:** Changing existing dict values without structural mutation can be valid; not every mutation invalidates an iterator.

**Sources:** [ruff:B909](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/loop_iterator_mutation.rs#L20-L42) (preview), [bugbear:B909](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L429-L429) (documented), [ruff:PLE4703](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/modified_iterating_set.rs#L12-L51) (preview), [python:dict-views](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L5326-L5429) (python-3.13), [python:sequence-operations](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L929-L1132) (python-3.13), [bugbear:B038](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L293-L293) (moved)

## py.loop-target-clobbers-name — Loop target overwrites a value still needed elsewhere

Category: `scope`

**Where:** A loop target reuses an iterable name, enclosing loop variable, imported binding or parameter still needed elsewhere.
**Preconditions:** Code later relies on the old binding.

**Where template:** At {location} in {target}, inspect: A loop target reuses an iterable name, enclosing loop variable, imported binding or parameter still needed elsewhere.

**How:** for binds its target in the surrounding scope and each assignment replaces the previous value.
**Trigger template:** Use at least two {outer_values} and {inner_values}; read {reused_name} after the inner loop.

**What:** Later operations see a scalar or the inner iteration value instead of the intended object.
**Oracle template:** Under {contract}, assert the preserved iterable or outer-loop value is used at the later operation.

**Applicability:** Rebinding does not itself change the active iterator and may be intentional.

**Sources:** [ruff:B020](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/loop_variable_overrides_iterator.rs#L13-L42) (stable), [bugbear:B020](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L201-L201) (documented), [bugbear:B045](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L331-L336) (documented), [python:local-binding](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L119-L189) (python-3.13), [ruff:F402](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/imports.rs#L10-L39) (stable)

## py.zip-truncates — zip silently truncates unequal length inputs

Category: `iteration`

**Where:** Parallel sequences are combined with zip without strict length checking.
**Preconditions:** The contract requires all inputs to be fully paired.

**Where template:** At {location} in {target}, inspect: Parallel sequences are combined with zip without strict length checking.

**How:** Default zip stops as soon as its shortest input is exhausted.
**Trigger template:** Pass {left_sequence} and {right_sequence} whose lengths differ by one.

**What:** An unmatched suffix is silently ignored.
**Oracle template:** Under {contract}, require explicit length-mismatch rejection or preservation of all expected items.

**Applicability:** Shortest-input pairing is often intended; strict=True requires Python 3.10 or later.

**Sources:** [bugbear:B905](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L405-L411) (documented), [bugbear:B913](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L448-L452) (documented)

## py.incomplete-batch — A final partial batch violates fixed-size processing assumptions

Category: `iteration`

**Where:** itertools.batched is used without an explicit final-batch policy.
**Preconditions:** Downstream processing requires exactly n elements per batch.

**Where template:** At {location} in {target}, inspect: itertools.batched is used without an explicit final-batch policy.

**How:** The default behavior emits the remaining shorter batch.
**Trigger template:** Supply {items} with a positive length not divisible by {batch_size}.

**What:** The last batch is incomplete or a downstream operation fails.
**Oracle template:** Under {contract}, assert the documented partial-batch behavior or explicit rejection of the incomplete batch.

**Applicability:** Partial batches are valid by default; strict support was added in Python 3.13.

**Sources:** [bugbear:B911](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L437-L439) (documented)

## py.map-truncates — Multi-iterable map truncates at the shortest input

Category: `iteration`

**Where:** map consumes multiple iterable arguments.
**Preconditions:** The operation requires matching lengths and complete processing.

**Where template:** At {location} in {target}, inspect: map consumes multiple iterable arguments.

**How:** Without strict checking, map stops at the first exhausted input.
**Trigger template:** Fully consume map over {left_sequence} and {right_sequence} of different lengths.

**What:** Some values are never processed.
**Oracle template:** Under {contract}, compare the processed count with the required count and check mismatch handling.

**Applicability:** Shortest-input semantics may be intended; map strict support depends on the Python version.

**Sources:** [bugbear:B912](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L443-L444) (documented)

## py.groupby-shared-iterator — groupby group iterators cannot be retained or consumed twice naively

Category: `iteration`

**Where:** An itertools.groupby group is reused or retained after advancing the outer iterator.
**Preconditions:** The caller expects each group to remain independently traversable.

**Where template:** At {location} in {target}, inspect: An itertools.groupby group is reused or retained after advancing the outer iterator.

**How:** Group iterators share the underlying input stream and are exhausted by consumption or outer advancement.
**Trigger template:** Consume {group} twice, or save it and advance {outer_group_iterator} before reading it.

**What:** A later read yields fewer items or an empty group.
**Oracle template:** Under {contract}, compare later group contents against materialized groups captured at creation time.

**Applicability:** Single-pass streaming is correct when explicitly intended; this card does not claim groupby sorts its input.

**Sources:** [ruff:B031](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/reuse_of_groupby_generator.rs#L11-L39) (stable), [bugbear:B031](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L264-L265) (documented)

## py.exhausted-iterator — Reusing a one-shot iterator loses data on the second pass

Category: `iteration`

**Where:** A generator, map, zip or iterator is traversed more than once.
**Preconditions:** The caller assumes it behaves like a reusable container.

**Where template:** At {location} in {target}, inspect: A generator, map, zip or iterator is traversed more than once.

**How:** An iterator advances its own state and stays exhausted after completion.
**Trigger template:** Traverse {iterator} to completion; traverse the same object again.

**What:** The second result is empty or incomplete.
**Oracle template:** Under {contract}, compare both passes with a materialized snapshot or separately created iterators.

**Applicability:** An empty second pass is correct for the iterator protocol; the bug is a caller assumption.

**Sources:** [python:iterators](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L842-L901) (python-3.13), [python:generator-expressions](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L388-L441) (python-3.13)

## py.unconsumed-lazy-expression — A lazy expression is created but its intended effects never run

Category: `iteration`

**Where:** A generator expression, map or filter is constructed and discarded.
**Preconditions:** Expected work occurs in the deferred body and nobody consumes the iterator.

**Where template:** At {location} in {target}, inspect: A generator expression, map or filter is constructed and discarded.

**How:** Lazy iteration postpones body execution until items are requested.
**Trigger template:** Run {statement} without consuming its result; inspect {expected_side_effect}.

**What:** Expected callbacks, writes or mutations do not occur.
**Oracle template:** Under {contract}, check the expected number and order of side effects.

**Applicability:** Generator construction can still evaluate its leftmost iterable expression immediately.

**Sources:** [ruff:B018](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/useless_expression.rs#L12-L56) (stable), [bugbear:B018](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L176-L190) (documented), [python:generator-expressions](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L388-L441) (python-3.13)

## py.generator-return-is-not-yield — A generator return value is not an emitted item

Category: `iteration`

**Where:** A function containing yield also returns a non-None value.
**Preconditions:** A consumer expects that return value among ordinary iterated items.

**Where template:** At {location} in {target}, inspect: A function containing yield also returns a non-None value.

**How:** return ends the generator; its value is carried by StopIteration rather than yielded.
**Trigger template:** Consume {generator} using list or a for loop, reaching its return path.

**What:** The expected terminal item is missing from the output sequence.
**Oracle template:** Under {contract}, compare emitted items with the required sequence; inspect StopIteration.value only if specified.

**Applicability:** Generator return values are valid for yield from and explicit StopIteration inspection.

**Sources:** [ruff:B901](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/return_in_generator.rs#L11-L84) (preview), [bugbear:B901](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L371-L376) (documented)

## py.stopiteration-in-generator — Raising StopIteration inside a generator becomes RuntimeError

Category: `iteration`

**Where:** A generator body explicitly raises StopIteration.
**Preconditions:** The raised exception escapes the generator body.

**Where template:** At {location} in {target}, inspect: A generator body explicitly raises StopIteration.

**How:** Modern Python converts escaping StopIteration into RuntimeError under PEP 479.
**Trigger template:** Consume {generator} until the explicit StopIteration branch executes.

**What:** Iteration fails with RuntimeError instead of ending normally.
**Oracle template:** Under {contract}, assert clean exhaustion and the expected emitted sequence.

**Applicability:** A direct call to next outside a generator follows ordinary StopIteration semantics.

**Sources:** [ruff:PLR1708](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/stop_iteration_return.rs#L13-L43) (stable)

## py.dict-iteration-unpacks-keys — Dictionary iteration unpacks keys instead of key-value pairs

Category: `mapping`

**Where:** A loop unpacks two targets while directly iterating a dict.
**Preconditions:** The intended data are key-value pairs.

**Where template:** At {location} in {target}, inspect: A loop unpacks two targets while directly iterating a dict.

**How:** Iterating a dict yields keys, so unpacking operates on each key.
**Trigger template:** Use {mapping} with a string key of length other than two and a distinguishable value.

**What:** Unpacking raises or binds characters or tuple components instead of the value.
**Oracle template:** Under {contract}, compare each bound pair with the mapping key and its stored value.

**Applicability:** Unpacking tuple-valued keys can be completely intentional.

**Sources:** [ruff:PLE1141](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/dict_iter_missing_items.rs#L12-L56) (preview)

## py.range-exclusive-stop — range excludes its stop boundary

Category: `iteration`

**Where:** A loop uses range to enumerate a contract-defined interval.
**Preconditions:** The required interval includes an endpoint omitted by the constructed range.

**Where template:** At {location} in {target}, inspect: A loop uses range to enumerate a contract-defined interval.

**How:** range includes start and excludes stop, with direction determined by step.
**Trigger template:** Choose {start} and {stop} that differ by one; also check an equal-endpoint interval.

**What:** A required endpoint is never visited or an interval is unexpectedly empty.
**Oracle template:** Under {interval_contract}, compare the exact visited sequence and count with the required inclusive or exclusive bounds.

**Applicability:** Python range is correct; this is a contract-dependent off-by-one hypothesis, not a general lint violation.

**Sources:** [python:range](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L1451-L1580) (python-3.13)

## py.slice-boundary-normalization — Slice clamping hides invalid bounds or drops an endpoint

Category: `iteration`

**Where:** Sequence slicing is used where index validation or inclusive endpoints are required.
**Preconditions:** The application assumes out-of-range slices raise or stop is inclusive.

**Where template:** At {location} in {target}, inspect: Sequence slicing is used where index validation or inclusive endpoints are required.

**How:** Slices clamp bounds, interpret negatives relative to length and exclude the stop position.
**Trigger template:** Slice {sequence} at length, beyond length, negative bounds, and an empty interval.

**What:** An invalid request silently yields an empty or truncated result.
**Oracle template:** Under {slice_contract}, compare the exact selected values and required rejection behavior.

**Applicability:** Clamping and half-open intervals are normal slice behavior; validate the application contract.

**Sources:** [python:sequence-operations](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L929-L1132) (python-3.13)

## py.negative-index-sentinel — A negative sentinel is accidentally used as a valid sequence index

Category: `iteration`

**Where:** A search result or computed index can be negative before indexing a sequence.
**Preconditions:** Negative results mean missing or invalid according to the application.

**Where template:** At {location} in {target}, inspect: A search result or computed index can be negative before indexing a sequence.

**How:** Negative indexing selects from the end instead of rejecting the sentinel.
**Trigger template:** Choose {input} that produces index -1 and apply the resulting index to a nonempty {sequence}.

**What:** The last element is returned for a missing item.
**Oracle template:** Under {contract}, require explicit missing-item handling rather than returning the final element.

**Applicability:** Negative indices are valid and useful when intentionally selecting from the end.

**Sources:** [python:negative-index](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L1179-L1189) (python-3.13), [python:sequence-operations](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L929-L1132) (python-3.13)

## py.finally-overrides-control-flow — finally return or jump overrides exceptions and return values

Category: `exceptions`

**Where:** A finally block contains return, break or continue.
**Preconditions:** An earlier return value or exception must remain observable.

**Where template:** At {location} in {target}, inspect: A finally block contains return, break or continue.

**How:** Control transfer in finally replaces pending control flow from try or except.
**Trigger template:** Make {try_body} raise {expected_exception} or return {expected_value}, then execute the finally jump.

**What:** The exception disappears or a different return value is observed.
**Oracle template:** Under {contract}, assert preservation of the required exception or return value after cleanup.

**Applicability:** Deliberate exception suppression must be explicit in the contract; inspect nested scopes separately.

**Sources:** [ruff:B012](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/jump_statement_in_finally.rs#L10-L46) (stable), [bugbear:B012](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L138-L142) (documented), [ruff:SIM107](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/return_in_try_except_finally.rs#L10-L46) (stable)

## py.catch-baseexception — An overly broad handler intercepts process control exceptions

Category: `exceptions`

**Where:** A bare except or except BaseException handler does not re-raise.
**Preconditions:** KeyboardInterrupt or SystemExit should propagate.

**Where template:** At {location} in {target}, inspect: A bare except or except BaseException handler does not re-raise.

**How:** BaseException includes process-control exceptions outside the usual Exception hierarchy.
**Trigger template:** Cause {protected_operation} to raise {control_exception} in an isolated test.

**What:** Cancellation or termination is swallowed and execution continues.
**Oracle template:** Under {contract}, assert that the required control exception propagates.

**Applicability:** Top-level cleanup and supervisor code may intentionally handle BaseException; do not send real interrupts to unrelated jobs.

**Sources:** [bugbear:B001](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L63-L66) (documented), [bugbear:B036](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L285-L285) (documented)

## py.empty-except-tuple — An empty exception tuple catches nothing

Category: `exceptions`

**Where:** An except handler uses an empty tuple.
**Preconditions:** The handler is intended to recover from a particular failure.

**Where template:** At {location} in {target}, inspect: An except handler uses an empty tuple.

**How:** No exception type can match the empty tuple.
**Trigger template:** Make {protected_operation} raise the exception the handler is expected to catch.

**What:** The exception escapes and the recovery branch never runs.
**Oracle template:** Under {contract}, assert the intended recovery result or a deliberately propagated exception.

**Applicability:** An empty dynamically configured set of handled exceptions may be intentional.

**Sources:** [ruff:B029](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/except_with_empty_tuple.rs#L11-L39) (stable), [bugbear:B029](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L256-L256) (documented)

## py.invalid-except-type — An except clause contains a non-exception class or value

Category: `exceptions`

**Where:** An except type expression is not a BaseException subclass or a tuple of such subclasses.
**Preconditions:** An exception reaches matching of that handler.

**Where template:** At {location} in {target}, inspect: An except type expression is not a BaseException subclass or a tuple of such subclasses.

**How:** Python rejects the invalid exception matcher with TypeError.
**Trigger template:** Raise {original_exception} inside the protected block and reach {handler}.

**What:** A matching-time TypeError obscures the original failure.
**Oracle template:** Under {contract}, assert the expected recovery or original exception rather than a matcher TypeError.

**Applicability:** Dynamic exception classes require runtime type knowledge; a name alone is not enough evidence.

**Sources:** [ruff:B030](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/except_with_non_exception_classes.rs#L12-L40) (stable), [bugbear:B030](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L260-L260) (documented)

## py.boolean-exception-matcher — Boolean operators in except select one class rather than several

Category: `exceptions`

**Where:** An except expression combines exception classes with and or or.
**Preconditions:** The handler is meant to catch either of two distinct exceptions.

**Where template:** At {location} in {target}, inspect: An except expression combines exception classes with and or or.

**How:** The boolean expression is evaluated first and yields one operand.
**Trigger template:** Make {protected_operation} raise each of {first_exception} and {second_exception} in separate calls.

**What:** One intended exception is not caught.
**Oracle template:** Under {contract}, assert the expected handling behavior for each specified exception type.

**Applicability:** Use tuple matching when both types are intended; computed match expressions can be deliberate.

**Sources:** [ruff:PLW0711](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/binary_op_exception.rs#L25-L52) (stable)

## py.unreachable-exception-handler — An earlier exception handler makes a later handler unreachable

Category: `exceptions`

**Where:** Ordered except clauses overlap or repeat exception types.
**Preconditions:** A later branch is expected to handle a more specific exception.

**Where template:** At {location} in {target}, inspect: Ordered except clauses overlap or repeat exception types.

**How:** Python selects the first matching handler, including a superclass handler.
**Trigger template:** Raise {specific_exception} that matches both {earlier_handler} and {later_handler}.

**What:** Specific recovery or reporting in the later handler never runs.
**Oracle template:** Under {contract}, assert which handler side effect and recovery value occur.

**Applicability:** Duplicate classes inside one tuple are mostly redundant; custom exception hierarchies need separate evidence.

**Sources:** [bugbear:B047](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L346-L349) (documented), [ruff:B025](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/duplicate_exceptions.rs#L16-L48) (stable), [bugbear:B025](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L229-L231) (documented)

## py.exception-constructed-not-raised — Constructing an exception does not raise it

Category: `exceptions`

**Where:** An exception instance is created or annotated but never raised or returned.
**Preconditions:** The branch is supposed to signal failure.

**Where template:** At {location} in {target}, inspect: An exception instance is created or annotated but never raised or returned.

**How:** Constructing Exception or calling add_note only changes an object; neither raises it.
**Trigger template:** Choose {invalid_input} that enters the error branch and observe subsequent execution.

**What:** Execution continues or returns a success-like result instead of signaling failure.
**Oracle template:** Under {contract}, assert the required exception type and message from the intended statement.

**Applicability:** Exception objects can legitimately be stored or returned as data.

**Sources:** [ruff:PLW0133](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/useless_exception_statement.rs#L13-L45) (stable), [bugbear:B040](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L301-L301) (documented)

## py.raise-invalid-object — Raising a literal or NotImplemented produces the wrong exception

Category: `exceptions`

**Where:** A raise statement uses a literal or the NotImplemented singleton.
**Preconditions:** The code expects an application exception or NotImplementedError.

**Where template:** At {location} in {target}, inspect: A raise statement uses a literal or the NotImplemented singleton.

**How:** raise accepts exception instances or classes; NotImplemented is a protocol sentinel.
**Trigger template:** Execute {error_branch} containing the raise expression.

**What:** A TypeError occurs instead of the intended exception.
**Oracle template:** Under {contract}, assert the exact required exception class.

**Applicability:** Returning NotImplemented from supported binary special methods is valid and distinct from raising it.

**Sources:** [ruff:B016](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/raise_literal.rs#L10-L32) (stable), [bugbear:B016](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L161-L162) (documented), [ruff:F901](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/raise_not_implemented.rs#L10-L40) (stable)

## py.empty-suppress — contextlib.suppress with no exception types suppresses nothing

Category: `exceptions`

**Where:** contextlib.suppress is called with no exception types.
**Preconditions:** The body may raise an exception the caller expects to suppress.

**Where template:** At {location} in {target}, inspect: contextlib.suppress is called with no exception types.

**How:** The empty matcher list cannot match any exception.
**Trigger template:** Raise {expected_suppressed_exception} inside {suppress_block}.

**What:** The supposedly suppressed error propagates.
**Oracle template:** Under {contract}, assert the intended suppression and subsequent continuation.

**Applicability:** An empty suppress can be an intentional no-op or placeholder.

**Sources:** [ruff:B022](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/useless_contextlib_suppress.rs#L10-L42) (stable), [bugbear:B022](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L210-L213) (documented)

## py.truthy-tuple-condition — A nonempty tuple makes an assertion or condition always true

Category: `logic`

**Where:** An assert or if condition is a tuple literal.
**Preconditions:** The tuple was intended as a condition and message, or several boolean checks.

**Where template:** At {location} in {target}, inspect: An assert or if condition is a tuple literal.

**How:** Truth testing a nonempty tuple ignores the truth values of its members.
**Trigger template:** Set {intended_condition} to false while leaving a nonempty tuple condition.

**What:** An assertion passes or an if branch runs despite the intended false condition.
**Oracle template:** Under {contract}, require the assertion or branch outcome to follow the intended boolean condition.

**Applicability:** A nonempty tuple may intentionally be tested for nonemptiness, although this literal form is suspicious.

**Sources:** [ruff:F631](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/assert_tuple.rs#L10-L33) (stable), [ruff:F634](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/if_tuple.rs#L11-L34) (stable)

## py.truthy-generator-assert — Asserting a generator object does not check its yielded values

Category: `testing`

**Where:** An assert statement directly tests a generator expression.
**Preconditions:** The test is intended to validate every generated condition.

**Where template:** At {location} in {target}, inspect: An assert statement directly tests a generator expression.

**How:** Generator objects are truthy and the assertion does not consume their values.
**Trigger template:** Provide {items} containing at least one item that violates {predicate}.

**What:** The test passes while the predicate is false for an item.
**Oracle template:** Under {contract}, verify actual predicate results through the specified all, any or exact-sequence semantics.

**Applicability:** all and any differ on empty input; select the quantifier required by the specification.

**Sources:** [bugbear:B044](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L323-L327) (documented), [python:generator-expressions](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L388-L441) (python-3.13)

## py.truthy-string-assert — Asserting a nonempty string validates no condition

Category: `testing`

**Where:** An assert condition is a nonempty string literal.
**Preconditions:** The string was intended as an error message rather than the condition.

**Where template:** At {location} in {target}, inspect: An assert condition is a nonempty string literal.

**How:** Every nonempty string is truthy.
**Trigger template:** Exercise {invalid_state} while executing the string-only assertion.

**What:** The test never fails for the intended invalid state.
**Oracle template:** Under {contract}, assert the actual boolean condition and reserve the string for the failure message.

**Applicability:** An empty string behaves differently; assertions may also be removed in optimized mode.

**Sources:** [ruff:PLW0129](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/assert_on_string_literal.rs#L17-L31) (stable)

## py.assert-side-effect — A required side effect disappears when assertions are optimized away

Category: `logic`

**Where:** An assert expression contains an assignment expression or required work.
**Preconditions:** The program relies on that work in optimized execution.

**Where template:** At {location} in {target}, inspect: An assert expression contains an assignment expression or required work.

**How:** Python optimized mode omits assertion evaluation entirely.
**Trigger template:** Execute {function} in ordinary and optimized interpreter modes with the same {input}.

**What:** A binding, side effect or required operation disappears in optimized mode.
**Oracle template:** Under {contract}, compare required outputs and effects across supported execution modes.

**Applicability:** Test-only assertions need not support optimized mode unless the application promises it.

**Sources:** [ruff:RUF018](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/assignment_in_assert.rs#L9-L53) (stable)

## py.identity-versus-equality — Identity comparison mistakes distinct equal values for unequal ones

Category: `logic`

**Where:** is or is not compares ordinary values such as strings or numbers.
**Preconditions:** The contract asks for value equality rather than object identity.

**Where template:** At {location} in {target}, inspect: is or is not compares ordinary values such as strings or numbers.

**How:** Identity compares object references; interning can hide errors in simple examples.
**Trigger template:** Construct {left_value} and {right_value} dynamically so they are equal but distinct objects.

**What:** Equal values take the unequal branch.
**Oracle template:** Under {contract}, compare the branch result with the required value-equality semantics.

**Applicability:** Identity checks for None and explicit singleton sentinels are valid.

**Sources:** [ruff:F632](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/invalid_literal_comparisons.rs#L13-L56) (stable), [python:identity](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L1861-L1947) (python-3.13)

## py.falsy-fallback — Boolean fallback replaces a valid falsy value

Category: `logic`

**Where:** x or default, or a and b or c, is used for defaulting or conditional selection.
**Preconditions:** Zero, False, an empty string or an empty container is valid data.

**Where template:** At {location} in {target}, inspect: x or default, or a and b or c, is used for defaulting or conditional selection.

**How:** Boolean operators select operands based on truthiness rather than missingness.
**Trigger template:** Supply {valid_falsy_value} where the alternate default is distinguishable.

**What:** The valid value is replaced by a default or the wrong branch result.
**Oracle template:** Under {contract}, distinguish missing values from valid falsy values in the expected output.

**Applicability:** Truthiness-based fallback is correct if the specification intentionally treats all falsy values as absent.

**Sources:** [python:truth](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L29-L73) (python-3.13), [python:boolean-operators](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L76-L115) (python-3.13)

## py.tautological-condition — A tautology or contradiction prevents an intended branch distinction

Category: `logic`

**Where:** A boolean expression combines the same pure condition and its negation, a constant, or identical operands.
**Preconditions:** The expression is expected to distinguish two reachable input cases.

**Where template:** At {location} in {target}, inspect: A boolean expression combines the same pure condition and its negation, a constant, or identical operands.

**How:** The expression can become constant or compare an expression with itself.
**Trigger template:** Provide {true_case} and {false_case} for the intended independent condition.

**What:** The branch outcome stays constant and one path is never selected.
**Oracle template:** Under {contract}, assert the expected branch-dependent outputs for both cases.

**Applicability:** NaN, overloaded comparisons and side effects invalidate simple boolean algebra assumptions; evaluate them explicitly.

**Sources:** [ruff:SIM220](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/ast_bool_op.rs#L124-L141) (stable), [ruff:SIM221](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/ast_bool_op.rs#L157-L174) (stable), [ruff:SIM222](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/ast_bool_op.rs#L197-L227) (stable), [ruff:SIM223](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/ast_bool_op.rs#L250-L280) (stable), [ruff:PLR0124](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/comparison_with_itself.rs#L10-L34) (stable)

## py.float-exact-equality — Exact floating point equality rejects a mathematically equal result

Category: `numeric`

**Where:** Computed floats are compared with == or !=.
**Preconditions:** The contract defines approximate numerical agreement.

**Where template:** At {location} in {target}, inspect: Computed floats are compared with == or !=.

**How:** Binary floating point rounding can produce nearby but unequal values.
**Trigger template:** Choose {operands} whose arithmetic result differs from {expected_value} by representational rounding.

**What:** An expected equal case fails or takes the wrong branch.
**Oracle template:** Under {numeric_contract}, use its specified absolute and relative tolerances, including a near-zero case.

**Applicability:** Exact comparison is valid for some algorithms and sentinels; tolerances must come from the problem requirements.

**Sources:** [ruff:RUF069](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/float_equality_comparison.rs#L14-L105) (preview)

## py.decimal-from-float — Constructing Decimal from a float preserves binary approximation

Category: `numeric`

**Where:** Decimal receives a floating point literal or float value.
**Preconditions:** Exact decimal digits are required.

**Where template:** At {location} in {target}, inspect: Decimal receives a floating point literal or float value.

**How:** Decimal converts the already rounded binary float rather than the decimal source text.
**Trigger template:** Construct {decimal_value} from a non-exact binary fraction such as the required monetary amount.

**What:** Unexpected trailing digits alter equality or downstream rounding.
**Oracle template:** Under {decimal_contract}, compare against an exact string-constructed Decimal and the required quantization.

**Applicability:** Converting an existing float exactly may be intentional.

**Sources:** [ruff:RUF032](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/decimal_from_float_literal.rs#L13-L38) (stable)

## py.nan-comparison — Ordinary equality cannot identify NaN

Category: `numeric`

**Where:** A computed value is compared directly with NaN.
**Preconditions:** The branch is intended to detect or exclude NaN.

**Where template:** At {location} in {target}, inspect: A computed value is compared directly with NaN.

**How:** NaN is not equal to itself, and ordinary ordering comparisons involving it are false.
**Trigger template:** Supply {nan_value} and a normal finite control value to {predicate}.

**What:** A NaN detector misses NaN or a filter behaves unexpectedly.
**Oracle template:** Under {contract}, assert explicit NaN classification and the required handling of finite and infinite values.

**Applicability:** Container identity shortcuts and custom numeric types require separate analysis.

**Sources:** [ruff:PLW0177](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/nan_comparison.rs#L12-L38) (stable), [python:comparisons](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L1494-L1699) (python-3.13)

## py.floor-division-negatives — Floor division differs from truncation for negative operands

Category: `numeric`

**Where:** Integer // is used in an algorithm expecting truncation toward zero.
**Preconditions:** Inputs may be negative and division is not exact.

**Where template:** At {location} in {target}, inspect: Integer // is used in an algorithm expecting truncation toward zero.

**How:** // rounds the quotient toward negative infinity.
**Trigger template:** Choose {negative_dividend} and {positive_divisor} with a nonzero remainder.

**What:** The quotient differs by one from the required truncating result.
**Oracle template:** Under {division_contract}, verify the specified quotient and remainder for all sign combinations.

**Applicability:** Floor division is correct for many algorithms; avoid floating conversion for large integer truncation.

**Sources:** [python:floor-division](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L829-L845) (python-3.13)

## py.operator-precedence — Operator precedence groups a condition differently from its intent

Category: `logic`

**Where:** Arithmetic, bitwise, boolean or chained comparison operators are mixed without explicit grouping.
**Preconditions:** The contract requires a grouping different from Python precedence.

**Where template:** At {location} in {target}, inspect: Arithmetic, bitwise, boolean or chained comparison operators are mixed without explicit grouping.

**How:** Python groups the expression according to its grammar; chained comparisons also have special evaluation rules.
**Trigger template:** Choose {operands} where {intended_grouping} and the parsed grouping produce different values.

**What:** A condition selects the wrong branch or arithmetic returns an incorrect value.
**Oracle template:** Under {contract}, compare against an explicitly parenthesized expression implementing the required grouping.

**Applicability:** Missing parentheses alone are not evidence of a bug; establish the intended expression.

**Sources:** [python:precedence](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L1984-L2097) (python-3.13), [python:comparisons](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L1494-L1699) (python-3.13)

## py.strip-character-set — strip treats its argument as a character set rather than a substring

Category: `strings`

**Where:** strip, lstrip or rstrip receives a multi-character argument.
**Preconditions:** The caller intends to remove an exact prefix or suffix.

**Where template:** At {location} in {target}, inspect: strip, lstrip or rstrip receives a multi-character argument.

**How:** Each boundary character in the supplied set is removed repeatedly.
**Trigger template:** Use {text} whose boundary shares characters with {affix} without containing that exact affix.

**What:** Valid characters are removed or an unintended part of the text disappears.
**Oracle template:** Under {contract}, compare with the required exact prefix or suffix removal.

**Applicability:** A character-set argument is correct when trimming a set of allowed boundary characters.

**Sources:** [ruff:B005](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/strip_with_multi_characters.rs#L13-L59) (stable), [ruff:PLE1310](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/bad_str_strip_call.rs#L16-L53) (stable), [bugbear:B005](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L90-L95) (documented)

## py.regex-positional-flags — Regex positional arguments bind flags as count or maxsplit

Category: `strings`

**Where:** re.sub, re.subn or re.split receives a positional argument intended as flags.
**Preconditions:** The flags value occupies a count or maxsplit position.

**Where template:** At {location} in {target}, inspect: re.sub, re.subn or re.split receives a positional argument intended as flags.

**How:** These APIs have different positional parameter orders from some other re functions.
**Trigger template:** Use {pattern} and {text} where case sensitivity and replacement or split count produce distinct outputs.

**What:** Case-insensitive matching is missing or the operation is unexpectedly limited.
**Oracle template:** Under {contract}, compare matching and count semantics with explicit flags and count or maxsplit keywords.

**Applicability:** Positional count can be intentional; API deprecations and supported Python versions should be checked.

**Sources:** [bugbear:B034](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L277-L277) (documented)

## py.missing-interpolation — A supposed template string remains uninterpolated

Category: `strings`

**Where:** A plain string contains placeholder-like braces without an f prefix.
**Preconditions:** The string is supposed to contain runtime values.

**Where template:** At {location} in {target}, inspect: A plain string contains placeholder-like braces without an f prefix.

**How:** Ordinary string literals do not evaluate brace expressions.
**Trigger template:** Set {variable} to a distinctive value and execute {formatting_path}.

**What:** Literal braces or names appear in the output.
**Oracle template:** Under {contract}, assert the required fully rendered string.

**Applicability:** Braces in JSON, logging templates, regular expressions or later formatting may be intentional.

**Sources:** [ruff:RUF027](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/missing_fstring_syntax.rs#L18-L71) (preview)

## py.string-format-contract — Formatting arguments do not match placeholders or conversion types

Category: `strings`

**Where:** Percent formatting, str.format or combined f-string/percent formatting consumes incompatible, missing or wrongly staged arguments.
**Preconditions:** The formatting path is reached with the problematic argument set.

**Where template:** At {location} in {target}, inspect: Percent formatting, str.format or combined f-string/percent formatting consumes incompatible, missing or wrongly staged arguments.

**How:** Each formatter validates placeholder syntax, count, names and conversions; f-string interpolation occurs before a following percent-formatting operation.
**Trigger template:** Run {format_expression} with distinct {arguments} that exercise each placeholder.

**What:** Formatting raises or produces an incorrectly mapped string.
**Oracle template:** Under {contract}, assert the complete required output and expected behavior for invalid argument types.

**Applicability:** Extra arguments may be harmless for some formatting APIs; do not treat all unused arguments as runtime failures. Intentional two-stage formatting is legal; evaluate the intermediate string and final argument bindings before flagging it.

**Sources:** [ruff:F501](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L24-L45) (stable), [ruff:F505](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L181-L203) (stable), [ruff:F507](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L253-L275) (stable), [ruff:F524](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L495-L516) (stable), [ruff:F525](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L529-L555) (stable), [ruff:PLE1307](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/bad_string_format_type.rs#L15-L33) (stable), [ruff:F502](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L57-L85) (stable), [ruff:F503](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L94-L122) (stable), [ruff:F506](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L216-L244) (stable), [ruff:F508](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L288-L314) (stable), [ruff:F509](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L323-L345) (stable), [ruff:F521](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L357-L377) (stable), [ruff:PLE1300](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/bad_string_format_character.rs#L13-L28) (stable), [ruff:RUF073](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/fstring_percent_format.rs#L9-L32) (preview)

## py.duplicate-dict-key — Repeated dictionary keys silently overwrite earlier values

Category: `mapping`

**Where:** A dict literal or construction contains equal keys.
**Preconditions:** All corresponding entries are expected to be preserved or a duplicate should be rejected.

**Where template:** At {location} in {target}, inspect: A dict literal or construction contains equal keys.

**How:** A dictionary keeps only one value per equal key, with later assignments replacing earlier ones.
**Trigger template:** Construct {mapping} with two equal {keys} and distinguishable values.

**What:** An earlier value disappears.
**Oracle template:** Under {contract}, assert the required duplicate policy and final mapping contents.

**Applicability:** Last-write-wins updates can be intentional; repeated identical pairs usually indicate redundancy rather than data loss.

**Sources:** [ruff:F601](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/repeated_keys.rs#L16-L54) (stable), [ruff:F602](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/repeated_keys.rs#L90-L127) (stable), [bugbear:B041](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L305-L305) (documented), [python:dict](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L5033-L5323) (python-3.13)

## py.constant-comprehension-key — A constant comprehension key collapses many entries into one

Category: `mapping`

**Where:** A dictionary comprehension uses a key independent of its iteration variable.
**Preconditions:** The output is expected to contain one distinct entry per input item.

**Where template:** At {location} in {target}, inspect: A dictionary comprehension uses a key independent of its iteration variable.

**How:** Each iteration writes the same key, replacing the previous value.
**Trigger template:** Run {comprehension} on at least two distinct {items}.

**What:** The mapping contains only the final value for the repeated key.
**Oracle template:** Under {contract}, assert expected key cardinality and each retained key-value association.

**Applicability:** Intentional reduction to one key is valid; the Ruff RUF011 predecessor is removed and retained only as source history.

**Sources:** [ruff:B035](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/static_key_dict_comprehension.rs#L14-L36) (stable), [bugbear:B035](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L281-L281) (documented), [ruff:RUF011](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/static_key_dict_comprehension.rs#L6-L33) (removed)

## py.defaultdict-keyword-factory — defaultdict keyword default_factory creates an entry instead of a factory

Category: `mapping`

**Where:** defaultdict is initialized with default_factory as a keyword argument.
**Preconditions:** Missing keys are expected to invoke that callable.

**Where template:** At {location} in {target}, inspect: defaultdict is initialized with default_factory as a keyword argument.

**How:** The factory is positional-only; keyword arguments populate initial dictionary entries.
**Trigger template:** Create {mapping}, then access a distinct missing {key}.

**What:** The lookup raises KeyError and an unintended default_factory key exists.
**Oracle template:** Under {contract}, assert the intended default value, factory attribute and initial key set.

**Applicability:** A mapping may intentionally store a key named default_factory.

**Sources:** [ruff:RUF026](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/default_factory_kwarg.rs#L17-L56) (stable)

## py.mutator-return-none — An in-place container method result is mistaken for the container

Category: `iteration`

**Where:** The result of list.sort, append, extend or another documented in-place mutator is assigned or returned.
**Preconditions:** The caller expects the modified sequence as the method result.

**Where template:** At {location} in {target}, inspect: The result of list.sort, append, extend or another documented in-place mutator is assigned or returned.

**How:** Many in-place container methods mutate their receiver and return None.
**Trigger template:** Run {mutator_call} on a nonempty sequence and inspect both its result and the original object.

**What:** A variable becomes None or a later operation on it fails.
**Oracle template:** Under {contract}, assert the required returned value separately from the required mutation.

**Applicability:** Not every mutator returns None; pop returns a removed item and custom methods can differ.

**Sources:** [python:mutable-sequences](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L1157-L1319) (python-3.13), [python:list-sort](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L1322-L1400) (python-3.13)

## py.undefined-local — A local assignment makes an earlier name access unbound

Category: `scope`

**Where:** A function reads a name that is also assigned in its body.
**Preconditions:** No local value has been assigned on the path before the read.

**Where template:** At {location} in {target}, inspect: A function reads a name that is also assigned in its body.

**How:** Python determines local bindings for the function scope, so an outer binding is not used automatically.
**Trigger template:** Choose {input} reaching {read_site} before the local assignment or through a skipped assignment branch.

**What:** Execution raises UnboundLocalError.
**Oracle template:** Under {contract}, check initialization on every required path or explicitly declared nonlocal or global access.

**Applicability:** Nested function and comprehension scopes differ; avoid inferring scope from text matching alone.

**Sources:** [ruff:F823](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/undefined_local.rs#L11-L38) (stable), [python:local-binding](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/faq/programming.rst#L119-L189) (python-3.13)

## py.undefined-name — A rarely executed branch reads an undefined name

Category: `scope`

**Where:** An expression loads a name with no reachable binding or import.
**Preconditions:** The branch using the name is executed.

**Where template:** At {location} in {target}, inspect: An expression loads a name with no reachable binding or import.

**How:** Name lookup fails after checking applicable scopes.
**Trigger template:** Choose {input} that reaches {undefined_reference}, including the least-used error branch.

**What:** The call raises NameError instead of the specified result or exception.
**Oracle template:** Under {contract}, assert the required output or specific application exception for that path.

**Applicability:** Dynamic namespace injection and optional imports need environment evidence. Specifically, interactive exit and quit helpers may be absent when Python starts without site initialization; program termination should use its documented API.

**Sources:** [ruff:F821](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/undefined_name.rs#L6-L32) (stable), [ruff:PLR1722](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/sys_exit_alias.rs#L10-L55) (stable)

## py.annotation-not-assignment — A colon introduces an annotation instead of assigning a value

Category: `scope`

**Where:** A variable, attribute or subscription uses an annotation-like statement where assignment was intended.
**Preconditions:** A later operation expects a value to have been stored.

**Where template:** At {location} in {target}, inspect: A variable, attribute or subscription uses an annotation-like statement where assignment was intended.

**How:** Annotations describe a target and generally do not assign the intended runtime value.
**Trigger template:** Execute {annotation_statement}, then read {target} or inspect the original object.

**What:** The target is absent or retains its old value.
**Oracle template:** Under {contract}, assert that the required runtime assignment actually occurred.

**Applicability:** Variable annotations and annotation-only class declarations are valid Python features.

**Sources:** [ruff:B032](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/unintentional_type_annotation.rs#L10-L28) (stable), [bugbear:B032](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L269-L269) (documented), [ruff:F842](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/unused_annotation.rs#L9-L32) (stable)

## py.blocking-call-in-async — A synchronous blocking call stalls an async event loop

Category: `async`

**Where:** An async function calls blocking sleep, I/O, HTTP, input or process APIs.
**Preconditions:** Other event-loop tasks must make progress during the operation.

**Where template:** At {location} in {target}, inspect: An async function calls blocking sleep, I/O, HTTP, input or process APIs.

**How:** A synchronous call occupies the event-loop thread until it returns.
**Trigger template:** Run {async_operation} alongside a controlled {progress_task} while the blocking operation waits.

**What:** The other task cannot progress and deadlines or responsiveness requirements are violated.
**Oracle template:** Under {concurrency_contract}, check progress with synchronization events and bounded waits rather than fragile timing alone.

**Applicability:** A call may return quickly on one input; explicit worker-thread offloading changes applicability.

**Sources:** [ruff:ASYNC210](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_http_call.rs#L11-L43) (stable), [ruff:ASYNC212](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_http_call_httpx.rs#L11-L42) (stable), [ruff:ASYNC230](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_open_call.rs#L10-L39) (stable), [ruff:ASYNC240](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_path_methods.rs#L9-L66) (stable), [ruff:ASYNC250](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_input.rs#L10-L38) (stable), [ruff:ASYNC251](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_sleep.rs#L11-L40) (stable), [ruff:ASYNC220](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_process_invocation.rs#L11-L42) (stable), [ruff:ASYNC221](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_process_invocation.rs#L51-L82) (stable), [ruff:ASYNC222](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/blocking_process_invocation.rs#L91-L127) (stable)

## py.async-call-not-awaited — Calling an async API without awaiting or scheduling leaves work undone

Category: `async`

**Where:** An async API such as Trio sleep or checkpoint is called as if it were synchronous.
**Preconditions:** The returned coroutine is neither awaited nor scheduled.

**Where template:** At {location} in {target}, inspect: An async API such as Trio sleep or checkpoint is called as if it were synchronous.

**How:** Calling an async function creates a coroutine object without executing its body.
**Trigger template:** Run {caller} through {async_call_site} and inspect {expected_effect}.

**What:** The effect does not happen and an unawaited-coroutine warning may appear.
**Oracle template:** Under {contract}, assert completion of the required effect and proper coroutine lifecycle.

**Applicability:** Returning a coroutine to an awaiting caller is valid; this concept generalizes the specific Trio source rule.

**Sources:** [ruff:ASYNC105](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/sync_call.rs#L12-L43) (stable)

## py.cancel-scope-no-checkpoint — A cancellation scope without a checkpoint cannot interrupt work

Category: `async`

**Where:** A Trio or AnyIO cancellation or timeout scope contains no checkpoint.
**Preconditions:** The timeout is expected to interrupt work in that scope.

**Where template:** At {location} in {target}, inspect: A Trio or AnyIO cancellation or timeout scope contains no checkpoint.

**How:** Cooperative cancellation is delivered at checkpoints; synchronous work does not yield.
**Trigger template:** Execute {scoped_operation} with an expired or very short {deadline} and a controlled workload.

**What:** The operation proceeds without observing the intended cancellation.
**Oracle template:** Under {cancellation_contract}, assert cancellation at a supported checkpoint and the required cleanup behavior.

**Applicability:** Timeout semantics are framework-specific; this is not a hard real-time deadline guarantee.

**Sources:** [ruff:ASYNC100](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_async/rules/cancel_scope_no_checkpoint.rs#L11-L50) (stable)

## py.fresh-lock-per-operation — Creating a fresh lock for each operation does not serialize shared state

Category: `resources`

**Where:** Each with statement or function call constructs its own lock.
**Preconditions:** Several workers update the same shared resource.

**Where template:** At {location} in {target}, inspect: Each with statement or function call constructs its own lock.

**How:** Different lock objects do not coordinate access with one another.
**Trigger template:** Run two {workers} against {shared_resource}, coordinating their overlap with synchronization barriers.

**What:** Updates interleave or a shared invariant is violated.
**Oracle template:** Under {concurrency_contract}, assert shared-lock identity and the required invariant during overlapping operations.

**Applicability:** A local lock can be valid if it is actually shared with all relevant workers; a single sequential run cannot demonstrate a race.

**Sources:** [ruff:PLW2101](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/useless_with_lock.rs#L9-L53) (stable)

## py.contextmanager-cleanup-on-error — Generator context manager cleanup is skipped on exceptional exit

Category: `resources`

**Where:** A contextmanager generator has cleanup after yield outside a protecting finally.
**Preconditions:** The with body can raise and cleanup must still happen.

**Where template:** At {location} in {target}, inspect: A contextmanager generator has cleanup after yield outside a protecting finally.

**How:** The body exception is thrown at yield, bypassing unprotected code that follows it.
**Trigger template:** Enter {context_manager}, raise {body_exception} inside the with body and inspect {resource}.

**What:** The resource remains acquired or a required cleanup effect is missing.
**Oracle template:** Under {resource_contract}, assert cleanup on both normal and exceptional exit while preserving required exception behavior.

**Applicability:** Cleanup may intentionally be conditional; establish ownership and exception semantics before applying.

**Sources:** [ruff:RUF075](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/fallible_context_manager.rs#L11-L54) (preview)

## py.file-not-closed — Manual file handling misses cleanup on an early exit

Category: `resources`

**Where:** A file is opened without a context manager or another proven cleanup path.
**Preconditions:** Exceptions or early returns can bypass close and the function owns the handle.

**Where template:** At {location} in {target}, inspect: A file is opened without a context manager or another proven cleanup path.

**How:** Cleanup placed only on the normal path is not guaranteed to run.
**Trigger template:** Cause {operation_after_open} to fail after {file_handle} is created.

**What:** A file descriptor, buffered write or lock remains outstanding beyond its intended lifetime.
**Oracle template:** Under {ownership_contract}, assert closure and required flush behavior on all exits.

**Applicability:** Returned or externally owned handles may deliberately outlive the function; absence of with alone does not prove a leak.

**Sources:** [ruff:SIM115](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/open_file_with_context_handler.rs#L11-L39) (stable)

## py.subprocess-nonzero-ignored — A subprocess failure is mistaken for a successful operation

Category: `resources`

**Where:** subprocess.run is called without checking a nonzero return code.
**Preconditions:** The enclosing operation requires the subprocess to succeed.

**Where template:** At {location} in {target}, inspect: subprocess.run is called without checking a nonzero return code.

**How:** By default run returns a CompletedProcess even when the command exits unsuccessfully.
**Trigger template:** Run {command} with a controlled nonzero exit status and inspect the enclosing result.

**What:** The application reports success or consumes missing or invalid output.
**Oracle template:** Under {contract}, assert the specified failure signal or explicit returncode handling.

**Applicability:** check=False is valid when code inspects the returncode or intentionally accepts failure.

**Sources:** [ruff:PLW1510](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/subprocess_run_without_check.rs#L11-L54) (stable)

## py.environ-rebinding — Rebinding os.environ breaks intended child environment propagation

Category: `resources`

**Where:** Code assigns a new object to os.environ.
**Preconditions:** The goal is to change the actual process environment inherited by subprocesses.

**Where template:** At {location} in {target}, inspect: Code assigns a new object to os.environ.

**How:** Replacing the Python mapping does not perform the underlying environment updates made through its original proxy.
**Trigger template:** Rebind {environment_mapping}, then start a controlled child process to inspect {test_variable}.

**What:** The child sees different environment values from the replacement mapping.
**Oracle template:** Under {environment_contract}, assert the child environment via an explicit env mapping or supported environment mutation.

**Applicability:** Do not expose existing environment secrets; use dedicated synthetic variable names and an isolated process.

**Sources:** [ruff:B003](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/assignment_to_os_environ.rs#L10-L45) (stable), [bugbear:B003](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L76-L79) (documented)

## py.naive-utc-datetime — A naive datetime is mistaken for an aware UTC instant

Category: `datetime`

**Where:** datetime.today, utcnow or utcfromtimestamp creates a naive datetime.
**Preconditions:** Downstream code interprets the result as a timezone-aware instant.

**Where template:** At {location} in {target}, inspect: datetime.today, utcnow or utcfromtimestamp creates a naive datetime.

**How:** The object lacks timezone information; conversions can treat it as local time and aware comparisons may fail.
**Trigger template:** Exercise {datetime_operation} in a controlled non-UTC timezone or combine its result with {aware_datetime}.

**What:** An instant is shifted or comparison raises a naive-versus-aware TypeError.
**Oracle template:** Under {time_contract}, compare normalized aware instants and required timezone metadata.

**Applicability:** Naive local or wall-clock values can be valid; runtime version and deprecations affect API availability.

**Sources:** [ruff:DTZ002](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_datetimez/rules/call_datetime_today.rs#L13-L55) (stable), [ruff:DTZ003](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_datetimez/rules/call_datetime_utcnow.rs#L13-L51) (stable), [ruff:DTZ004](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_datetimez/rules/call_datetime_utcfromtimestamp.rs#L13-L52) (stable)

## py.invalid-special-method-return — A special method returns a value forbidden by its protocol

Category: `object-model`

**Where:** __bool__, __bytes__, __hash__, __index__, __len__ or __str__ returns an invalid type or length.
**Preconditions:** The corresponding built-in operation invokes the special method.

**Where template:** At {location} in {target}, inspect: __bool__, __bytes__, __hash__, __index__, __len__ or __str__ returns an invalid type or length.

**How:** Python enforces the return contract of each special method.
**Trigger template:** Call {builtin_operation} on {instance} whose special method returns {invalid_result}.

**What:** The built-in raises TypeError or ValueError rather than producing the required result.
**Oracle template:** Under {protocol_contract}, check the exact required return type and value domain for that method.

**Applicability:** Protocols differ: bool is not accepted as a substitute everywhere and length must be nonnegative.

**Sources:** [ruff:PLE0304](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_bool_return.rs#L15-L40) (stable), [ruff:PLE0308](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_bytes_return.rs#L15-L40) (stable), [ruff:PLE0309](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_hash_return.rs#L15-L44) (stable), [ruff:PLE0305](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_index_return.rs#L15-L46) (stable), [ruff:PLE0303](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_length_return.rs#L15-L45) (stable), [ruff:PLE0307](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_str_return.rs#L15-L40) (stable)

## py.init-return-or-yield — __init__ returns or yields a value instead of returning None

Category: `object-model`

**Where:** A class initializer returns a non-None value or contains yield.
**Preconditions:** Normal class instantiation invokes that initializer.

**Where template:** At {location} in {target}, inspect: A class initializer returns a non-None value or contains yield.

**How:** __init__ must return None; a yield turns it into a generator function that returns a generator object on call.
**Trigger template:** Instantiate {class_name} on the path with the return or yield.

**What:** Object construction raises TypeError.
**Oracle template:** Under {construction_contract}, assert successful initialization and the required instance state.

**Applicability:** A bare return is allowed; object creation customizations belong to different protocols such as __new__.

**Sources:** [ruff:PLE0101](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/return_in_init.rs#L12-L40) (stable), [ruff:PLE0100](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/yield_in_init.rs#L11-L34) (stable), [bugbear:B037](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L289-L289) (documented)

## py.property-missing-return — A property getter falls through and returns None

Category: `object-model`

**Where:** A property getter has a path without a returned value.
**Preconditions:** The property contract requires a value on that path.

**Where template:** At {location} in {target}, inspect: A property getter has a path without a returned value.

**How:** Python implicitly returns None when a function falls through.
**Trigger template:** Construct {instance} that reaches the getter fallthrough path and read {property}.

**What:** The property is None instead of the required computed value.
**Oracle template:** Under {property_contract}, check every specified state including the branch without an explicit return.

**Applicability:** A property returning None can be intentional and must not automatically be labeled a bug.

**Sources:** [ruff:RUF066](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/property_without_return.rs#L11-L41) (preview)

## py.abstract-decorator-order — Decorator order breaks abstract property or method construction

Category: `object-model`

**Where:** abstractmethod is combined with property, classmethod or staticmethod in the wrong order.
**Preconditions:** The descriptor requires abstractmethod to act on the underlying function first.

**Where template:** At {location} in {target}, inspect: abstractmethod is combined with property, classmethod or staticmethod in the wrong order.

**How:** Decorators apply bottom-up; setting abstract flags on an incompatible descriptor can fail at class definition.
**Trigger template:** Define {class_name} with {decorator_stack}, then inspect construction and abstract status.

**What:** Class definition raises AttributeError or abstractness differs from the required behavior.
**Oracle template:** Under {class_contract}, assert abstract status and valid construction of a concrete subclass.

**Applicability:** Different descriptors such as cached_property have different rules; do not reorder arbitrary decorators mechanically.

**Sources:** [ruff:RUF074](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/incorrect_decorator_order.rs#L13-L49) (preview), [bugbear:B049](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L353-L358) (documented)

## py.missing-super-call — Referring to super without calling it skips base initialization

Category: `object-model`

**Where:** Code uses super as if it were a proxy object without calling it.
**Preconditions:** The method should invoke an implementation from the method resolution order.

**Where template:** At {location} in {target}, inspect: Code uses super as if it were a proxy object without calling it.

**How:** The super built-in must create a proxy before normal base-method access.
**Trigger template:** Instantiate or call {subclass_method} on a class whose base method sets a distinctive {state}.

**What:** Base behavior is missing or attribute access fails.
**Oracle template:** Under {inheritance_contract}, assert required base initialization and final state.

**Applicability:** Explicit two-argument super is also valid; cooperative inheritance needs the actual MRO.

**Sources:** [ruff:PLW0245](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/super_without_brackets.rs#L11-L60) (stable)

## py.broad-raises-oracle — A broad exception assertion accepts the wrong failure

Category: `testing`

**Where:** A test expects Exception or another overly broad class.
**Preconditions:** The test should identify one specific failure from the intended operation.

**Where template:** At {location} in {target}, inspect: A test expects Exception or another overly broad class.

**How:** An unrelated TypeError, NameError or setup error satisfies the broad assertion.
**Trigger template:** Introduce {unrelated_failure} before or within {intended_operation} and observe the exception assertion.

**What:** The test passes without establishing the intended behavior.
**Oracle template:** Under {exception_contract}, assert the required exception class, message or attributes and the exact raising operation.

**Applicability:** Broad handlers can be appropriate for application recovery; this concept concerns oracle specificity.

**Sources:** [ruff:B017](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/assert_raises_exception.rs#L11-L34) (stable), [bugbear:B017](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L166-L172) (documented)

## py.multi-statement-raises-oracle — An exception assertion can pass on an earlier unintended statement

Category: `testing`

**Where:** An exception assertion context contains several top-level operations.
**Preconditions:** Only the final operation is intended to raise.

**Where template:** At {location} in {target}, inspect: An exception assertion context contains several top-level operations.

**How:** Any matching earlier exception exits the context before the intended operation runs.
**Trigger template:** Make {setup_statement} raise the expected exception before {target_statement}.

**What:** The test passes even though the target statement was never executed.
**Oracle template:** Under {exception_contract}, separate setup from the assertion context and assert the exception at the intended call.

**Applicability:** Several statements can be intentional, but the raising site must still match the test claim.

**Sources:** [bugbear:B908](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L425-L425) (documented)

## py.assert-removal — Assertions used for runtime validation vanish in optimized mode

Category: `testing`

**Where:** An application uses assert to enforce required runtime input validation or unconditional failure.
**Preconditions:** Optimized Python execution is supported by the application.

**Where template:** At {location} in {target}, inspect: An application uses assert to enforce required runtime input validation or unconditional failure.

**How:** The interpreter can omit assert statements when optimization is enabled.
**Trigger template:** Pass {invalid_input} to {function} in ordinary and optimized interpreter modes.

**What:** Invalid input is accepted or a required failure disappears in optimized mode.
**Oracle template:** Under {validation_contract}, assert explicit required rejection in every supported mode.

**Applicability:** Debug-only assertions are valid; do not demand optimized-mode validation without a contract.

**Sources:** [bugbear:B011](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L133-L134) (documented)

## py.dictionary-view-is-live — A saved dictionary view changes with the dictionary

Category: `mapping`

**Where:** dict.keys, values or items is saved as though it were a historical snapshot.
**Preconditions:** The underlying dictionary is mutated before the saved result is used.

**Where template:** At {location} in {target}, inspect: dict.keys, values or items is saved as though it were a historical snapshot.

**How:** Dictionary views reflect the current dictionary rather than copying its contents.
**Trigger template:** Save {view}, mutate {mapping}, then inspect or iterate the saved view.

**What:** A supposed snapshot contains added or changed entries, or iteration fails after a size change.
**Oracle template:** Under {snapshot_contract}, compare the historical contents with the values observed after mutation.

**Applicability:** Live views are intentional and efficient; mutation of an existing value differs from changing dictionary size.

**Sources:** [python:dict-views](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L5326-L5429) (python-3.13)

## py.eager-default-expression — A default argument expression runs even when its value is unused

Category: `logic`

**Where:** A fallback expression is passed as a function argument such as dict.get default.
**Preconditions:** The caller expects that fallback to be evaluated only for a missing key.

**Where template:** At {location} in {target}, inspect: A fallback expression is passed as a function argument such as dict.get default.

**How:** Arguments are evaluated before a function call, regardless of which arguments the callee uses.
**Trigger template:** Use an existing {key} and a {fallback_expression} with a controlled visible side effect or exception.

**What:** An unnecessary side effect occurs or the lookup raises despite the key being present.
**Oracle template:** Under {evaluation_contract}, assert whether fallback evaluation is permitted for an existing key.

**Applicability:** Eager evaluation is Python semantics and may be intended; this is an application assumption to verify.

**Sources:** [python:evaluation-order](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L1963-L1981) (python-3.13), [python:dict](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L5033-L5323) (python-3.13)

## py.unary-increment-noop — Prefix increment or decrement does not update a Python number

Category: `numeric`

**Where:** Code writes ++x or --x expecting an increment or decrement.
**Preconditions:** x is a built-in numeric value and the result is not assigned.

**Where template:** At {location} in {target}, inspect: Code writes ++x or --x expecting an increment or decrement.

**How:** These expressions apply unary plus or minus twice; Python has no prefix increment operator.
**Trigger template:** Initialize {counter} to a distinctive integer and execute {expression}.

**What:** The counter stays unchanged and loop progress or counts are wrong.
**Oracle template:** Under {counter_contract}, assert the required change in the stored counter value.

**Applicability:** Custom overloaded unary operators can have other behavior; do not generalize to arbitrary objects.

**Sources:** [ruff:B002](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/unary_prefix_increment_decrement.rs#L10-L36) (stable), [bugbear:B002](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L70-L72) (documented)

## py.unreliable-callable-check — Attribute presence is mistaken for callability

Category: `object-model`

**Where:** A callable guard uses hasattr(obj, "__call__").
**Preconditions:** Objects can supply dynamic attributes or non-callable __call__ values.

**Where template:** At {location} in {target}, inspect: A callable guard uses hasattr(obj, "__call__").

**How:** Attribute presence and the callable protocol are different checks; a synthesized attribute can mislead hasattr.
**Trigger template:** Pass {object} with a controlled dynamic __getattr__ or non-callable __call__ to {guard}.

**What:** The guard makes a callability decision inconsistent with the supported object protocol.
**Oracle template:** Under {contract}, compare guard outcomes with the supported callable protocol and required invocation behavior.

**Applicability:** callable() itself does not guarantee that an arbitrary argument list will be accepted.

**Sources:** [ruff:B004](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/unreliable_callable_check.rs#L10-L72) (stable), [bugbear:B004](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L83-L86) (documented)

## py.discarded-comparison — A standalone comparison fails to enforce an intended condition

Category: `logic`

**Where:** A comparison appears as an expression statement with its result unused.
**Preconditions:** The application expects validation, assignment or a state change.

**Where template:** At {location} in {target}, inspect: A comparison appears as an expression statement with its result unused.

**How:** For ordinary operands, evaluating a comparison returns a boolean and does not enforce it or assign either operand.
**Trigger template:** Reach {comparison_statement} with {operands} that make the required condition false.

**What:** Execution continues without the expected rejection or update.
**Oracle template:** Under {contract}, assert the required rejection or state transition independently of evaluating the comparison.

**Applicability:** Overloaded comparisons can have side effects; inspect operand types before treating the statement as inert.

**Sources:** [ruff:B015](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/useless_comparison.rs#L12-L39) (stable), [bugbear:B015](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L156-L157) (documented)

## py.fstring-docstring — An f-string in docstring position leaves __doc__ unset

Category: `object-model`

**Where:** The first statement of a function, class or module is an f-string.
**Preconditions:** A docstring is required by introspection or documentation consumers.

**Where template:** At {location} in {target}, inspect: The first statement of a function, class or module is an f-string.

**How:** A joined string expression is not recognized as a literal Python docstring.
**Trigger template:** Define {object} using the f-string as its first statement and inspect its own __doc__.

**What:** The expected documentation is absent from __doc__ or automated tooling.
**Oracle template:** Under {documentation_contract}, assert the required literal docstring is available through introspection.

**Applicability:** A runtime expression at that position is legal; the failure requires a documented introspection contract.

**Sources:** [ruff:B021](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/f_string_docstring.rs#L10-L36) (stable), [bugbear:B021](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L205-L206) (documented)

## py.missing-abstract-contract — Missing abstract decorators permit an incomplete implementation

Category: `object-model`

**Where:** An ABC or an empty interface method lacks the intended abstractmethod decorator.
**Preconditions:** The interface contract requires subclasses to implement that method before instantiation.

**Where template:** At {location} in {target}, inspect: An ABC or an empty interface method lacks the intended abstractmethod decorator.

**How:** ABC inheritance alone does not make ordinary methods abstract or prohibit an otherwise concrete class from instantiating.
**Trigger template:** Instantiate {incomplete_subclass} without implementing {required_method}, then call that method if construction succeeds.

**What:** An incomplete object is accepted and may run an empty stub instead of required behavior.
**Oracle template:** Under {interface_contract}, assert abstract status and rejection of incomplete implementations.

**Applicability:** ABCs can intentionally provide concrete mixin methods; absence of a decorator alone does not prove a bug.

**Sources:** [ruff:B024](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/abstract_base_class.rs#L14-L59) (stable), [ruff:B027](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/abstract_base_class.rs#L71-L105) (stable), [bugbear:B024](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L223-L225) (documented), [bugbear:B027](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L244-L244) (documented)

## py.argument-binding-collision — Explicit and unpacked call arguments bind the same parameter

Category: `scope`

**Where:** A call combines explicit keywords with positional star arguments or keyword unpacking.
**Preconditions:** Two supplied values target the same formal parameter or keyword.

**Where template:** At {location} in {target}, inspect: A call combines explicit keywords with positional star arguments or keyword unpacking.

**How:** Star arguments still fill positional slots; ** mappings cannot duplicate an explicitly provided keyword.
**Trigger template:** Call {function} with {explicit_arguments} and {expanded_arguments} that overlap at {parameter}.

**What:** Argument binding raises TypeError; repeated explicit keyword syntax can instead fail compilation.
**Oracle template:** Under {call_contract}, assert successful unique binding or the required explicit collision rejection.

**Applicability:** A star argument after a keyword is legal when bindings do not overlap; do not reject the syntax categorically.

**Sources:** [ruff:B026](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/star_arg_unpacking_after_keyword_arg.rs#L10-L51) (stable), [bugbear:B026](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L235-L240) (documented), [ruff:PLE1132](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/repeated_keyword_argument.rs#L11-L28) (stable)

## py.warning-stacklevel — Warning location points to the wrapper instead of the caller

Category: `exceptions`

**Where:** A library wrapper calls warnings.warn without a suitable stacklevel or skip policy.
**Preconditions:** The warning contract requires identifying the external caller site.

**Where template:** At {location} in {target}, inspect: A library wrapper calls warnings.warn without a suitable stacklevel or skip policy.

**How:** The default warning stacklevel attributes the warning to the warn call itself.
**Trigger template:** Invoke {wrapper} from a known {caller_location} while capturing warning records.

**What:** The warning filename or line identifies the library internals rather than the relevant caller.
**Oracle template:** Under {warning_contract}, assert captured warning filename, line and category at the intended origin.

**Applicability:** A wrapper may intentionally report its own location; skip_file_prefixes availability depends on Python version.

**Sources:** [bugbear:B028](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L248-L252) (documented)

## py.set-loses-multiplicity — A set collapses repeated values that the application needed to retain

Category: `iteration`

**Where:** A set literal includes duplicate values or is used as though it preserves input multiplicity.
**Preconditions:** The application requires distinct entries, counts or a missing distinct literal was intended.

**Where template:** At {location} in {target}, inspect: A set literal includes duplicate values or is used as though it preserves input multiplicity.

**How:** A set retains one entry per equal value; repeated literals do not create additional elements.
**Trigger template:** Construct {set_expression} with equal values and compare it with {required_entries}.

**What:** Required cardinality or multiplicity is lost, or a copy-paste typo hides a missing distinct entry.
**Oracle template:** Under {collection_contract}, check the expected distinct members and whether multiplicity must be preserved.

**Applicability:** Deduplication is the normal set contract; duplicate spelling alone can be harmless redundancy.

**Sources:** [ruff:B033](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_bugbear/rules/duplicate_value.rs#L15-L48) (stable), [bugbear:B033](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L273-L273) (documented)

## py.exception-roundtrip — Custom exception initialization breaks copying or pickling

Category: `exceptions`

**Where:** An exception subclass defines a custom __init__ whose argument state is incompatible with reconstruction.
**Preconditions:** The exception must support copy, pickle or stable text reconstruction.

**Where template:** At {location} in {target}, inspect: An exception subclass defines a custom __init__ whose argument state is incompatible with reconstruction.

**How:** Base exception protocols use args to reconstruct or stringify the object; inconsistent args and constructor signatures can break that protocol.
**Trigger template:** Create {exception_instance} with {constructor_arguments}; round-trip it through the required copy or serialization operation.

**What:** Reconstruction raises or loses required exception state or message.
**Oracle template:** Under {exception_contract}, assert type, required attributes, args and message after the round-trip.

**Applicability:** Custom __reduce__ or __str__ can legitimately supply alternative protocols; untrusted pickle data must never be loaded.

**Sources:** [bugbear:B042](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L309-L314) (documented)

## py.exception-chaining-contract — Exception translation loses the intended explicit cause

Category: `exceptions`

**Where:** An except block raises a replacement exception without explicit chaining policy.
**Preconditions:** The error API specifies a cause or deliberate suppression of underlying context.

**Where template:** At {location} in {target}, inspect: An except block raises a replacement exception without explicit chaining policy.

**How:** Implicit context differs from an explicit __cause__ and from raise ... from None suppression.
**Trigger template:** Make {underlying_operation} fail with {cause_exception}, then capture the translated {public_exception}.

**What:** The exception cause, context display or diagnostic chain differs from the error contract.
**Oracle template:** Under {error_contract}, inspect __cause__, __context__ and __suppress_context__ as appropriate.

**Applicability:** Implicit chaining preserves context automatically; lack of from does not itself mean all cause information is lost.

**Sources:** [bugbear:B904](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L398-L401) (documented)

## py.ast-visitor-no-recursion — An AST visitor override silently skips child nodes

Category: `object-model`

**Where:** A NodeVisitor visit_* override does not visit relevant child nodes.
**Preconditions:** The analysis must traverse descendants beneath that node.

**Where template:** At {location} in {target}, inspect: A NodeVisitor visit_* override does not visit relevant child nodes.

**How:** Custom visit methods replace the default generic traversal unless they explicitly recurse.
**Trigger template:** Run {visitor} on {nested_source} containing a target node below the overridden parent.

**What:** Nested findings or transformations are missing.
**Oracle template:** Under {traversal_contract}, assert the required visited node set and nested findings.

**Applicability:** Some visitors intentionally prune subtrees; verify traversal policy before adding generic_visit.

**Sources:** [bugbear:B906](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L415-L417) (documented)

## py.manual-repr-escaping — Manually quoting a value fails to escape embedded quotes or control characters

Category: `strings`

**Where:** A representation is produced by surrounding an interpolated value with literal quote characters.
**Preconditions:** The output must be an unambiguous escaped representation.

**Where template:** At {location} in {target}, inspect: A representation is produced by surrounding an interpolated value with literal quote characters.

**How:** Manual surrounding quotes do not apply repr escaping to the value itself.
**Trigger template:** Render {value} containing a quote, backslash or newline using {representation_expression}.

**What:** The output is ambiguous or spans unintended lines.
**Oracle template:** Under {representation_contract}, compare with the required escaped representation for the supported value type.

**Applicability:** Human-facing literal text may intentionally use plain quoting; repr is not a universal serialization format.

**Sources:** [bugbear:B907](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L421-L421) (documented)

## py.defaultdict-read-inserts — Reading a missing defaultdict key unexpectedly changes the mapping

Category: `mapping`

**Where:** A defaultdict is used for counter-like read-only missing-key lookups.
**Preconditions:** Missing reads should not create persistent entries.

**Where template:** At {location} in {target}, inspect: A defaultdict is used for counter-like read-only missing-key lookups.

**How:** Subscription of a missing defaultdict key invokes the factory and inserts the result.
**Trigger template:** Read many distinct {missing_keys} from {mapping} without intending to add entries.

**What:** The mapping grows or later iteration includes keys that were only probed.
**Oracle template:** Under {mapping_contract}, compare the key set and size before and after missing-key reads.

**Applicability:** Insertion on missing subscription is intentional defaultdict behavior; get and Counter have different missing-key semantics.

**Sources:** [bugbear:B910](https://github.com/PyCQA/flake8-bugbear/blob/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb/README.rst#L433-L433) (documented)

## py.ignored-format-arguments — Extra formatting arguments hide an omitted output field

Category: `strings`

**Where:** Percent mapping formatting or str.format supplies values unused by any placeholder.
**Preconditions:** The output contract requires those values to appear.

**Where template:** At {location} in {target}, inspect: Percent mapping formatting or str.format supplies values unused by any placeholder.

**How:** These formatting APIs can accept extra supplied values without including them in the rendered text.
**Trigger template:** Render {format_expression} with distinct {supplied_values} and vary only the unused argument.

**What:** The required field is absent and changing its value does not affect output.
**Oracle template:** Under {output_contract}, compare the complete rendered text with the required field set and values.

**Applicability:** Supplying an intentionally broad reusable mapping is valid; unused arguments alone need not be bugs.

**Sources:** [ruff:F504](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L131-L162) (stable), [ruff:F522](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L389-L420) (stable), [ruff:F523](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/strings.rs#L441-L472) (stable)

## py.starred-unpacking-syntax — Invalid starred assignment prevents compilation

Category: `syntax`

**Where:** A destructuring assignment contains multiple starred targets or exceeds interpreter target-count limits.
**Preconditions:** The source is compiled by an interpreter enforcing these assignment constraints.

**Where template:** At {location} in {target}, inspect: A destructuring assignment contains multiple starred targets or exceeds interpreter target-count limits.

**How:** The compiler rejects ambiguous or oversized starred target layouts.
**Trigger template:** Compile {source_fragment} with {target_interpreter} using the required language version.

**What:** Compilation raises SyntaxError before the module can run.
**Oracle template:** Under {language_contract}, assert that required source compiles or invalid source is rejected at the specified stage.

**Applicability:** A single starred target is valid; exact target-count limits are interpreter-specific.

**Sources:** [ruff:F621](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/starred_expressions.rs#L9-L23) (stable), [ruff:F622](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/starred_expressions.rs#L32-L50) (stable)

## py.future-import-contract — A misplaced or unsupported __future__ import prevents compilation

Category: `syntax`

**Where:** A future import follows executable statements or requests an unsupported feature.
**Preconditions:** Compilation occurs on the target Python version.

**Where template:** At {location} in {target}, inspect: A future import follows executable statements or requests an unsupported feature.

**How:** __future__ imports are compile-time directives with placement and recognized-feature constraints.
**Trigger template:** Compile {module_source} on {target_interpreter} with the future import in its actual position.

**What:** The module fails with SyntaxError before import-time code executes.
**Oracle template:** Under {compatibility_contract}, assert successful compilation for every supported interpreter version.

**Applicability:** A module docstring and permitted leading statements have special placement rules; feature support varies by version.

**Sources:** [ruff:F404](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/imports.rs#L135-L162) (stable), [ruff:F407](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/future_feature_not_defined.rs#L6-L18) (stable)

## py.local-wildcard-import — A wildcard import in a non-module scope is rejected

Category: `syntax`

**Where:** from module import * appears inside a function or another disallowed scope.
**Preconditions:** Ordinary Python module compilation rules apply.

**Where template:** At {location} in {target}, inspect: from module import * appears inside a function or another disallowed scope.

**How:** Wildcard imports are restricted to module scope.
**Trigger template:** Compile {source_fragment} with the wildcard import inside its actual enclosing scope.

**What:** Compilation fails before the containing function can run.
**Oracle template:** Under {language_contract}, assert valid import placement or the required SyntaxError for invalid input.

**Applicability:** A wildcard import at module scope is legal, though it can still introduce name collisions.

**Sources:** [ruff:F406](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/imports.rs#L219-L249) (stable)

## py.legacy-print-redirection — Python 2 print redirection is interpreted as an unsupported operator in Python 3

Category: `resources`

**Where:** Migrated code contains a print >> stream expression.
**Preconditions:** The program executes under Python 3 and intends file-directed printing.

**Where template:** At {location} in {target}, inspect: Migrated code contains a print >> stream expression.

**How:** print is a function object; the old statement-like spelling is no longer redirection and can be parsed as a shift operation.
**Trigger template:** Execute {legacy_print_expression} with a controlled {output_stream} under the supported Python 3 version.

**What:** Execution fails or no required text reaches the intended stream.
**Oracle template:** Under {output_contract}, assert the exact bytes or text written to the required stream.

**Applicability:** Do not assume this spelling always fails parsing; ordinary Python 3 can parse it and fail at runtime.

**Sources:** [ruff:F633](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/invalid_print_syntax.rs#L9-L52) (stable)

## py.control-flow-placement — A control-flow statement is illegal in its enclosing scope or Python version

Category: `syntax`

**Where:** break, continue, return, yield or await occurs in a scope or version that forbids it.
**Preconditions:** The fragment is compiled with the actual target scope and interpreter flags.

**Where template:** At {location} in {target}, inspect: break, continue, return, yield or await occurs in a scope or version that forbids it.

**How:** The compiler enforces loop, function, async-function and version-specific control-flow restrictions.
**Trigger template:** Compile {source_fragment} inside {enclosing_scope} with {target_interpreter} and the required flags.

**What:** Compilation rejects the statement before runtime paths can be tested.
**Oracle template:** Under {language_contract}, assert compilation and diagnostics appropriate to the supported scope and version.

**Applicability:** Top-level await can be permitted by special compilation modes; continue in finally is supported from Python 3.8.

**Sources:** [ruff:F701](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/break_outside_loop.rs#L6-L23) (stable), [ruff:F702](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/continue_outside_loop.rs#L6-L23) (stable), [ruff:F704](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/yield_outside_function.rs#L36-L59) (stable), [ruff:F706](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/return_outside_function.rs#L6-L23) (stable), [ruff:PLE1142](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/await_outside_async.rs#L6-L41) (stable), [ruff:PLE1700](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/yield_from_in_async_function.rs#L6-L29) (stable), [ruff:PLE0116](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/continue_in_finally.rs#L10-L42) (stable)

## py.bare-except-order — A bare except before another handler makes the try statement invalid

Category: `syntax`

**Where:** A try statement places a bare except before another except clause.
**Preconditions:** Normal Python compilation rules apply.

**Where template:** At {location} in {target}, inspect: A try statement places a bare except before another except clause.

**How:** A catch-all bare handler must be last because subsequent exception matching would be unreachable.
**Trigger template:** Compile {try_statement} with its actual handler order.

**What:** Compilation raises SyntaxError.
**Oracle template:** Under {language_contract}, assert valid handler ordering or the required rejection for invalid source.

**Applicability:** except Exception is not syntactically catch-all and can compile before specific handlers; its runtime shadowing is a separate concept.

**Sources:** [ruff:F707](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/default_except_not_last.rs#L10-L50) (stable)

## py.binding-overwrite — Rebinding a parameter, receiver or assignment target destroys a still-needed value

Category: `scope`

**Where:** A parameter, receiver, definition or repeated destructuring target is rebound before a required use.
**Preconditions:** Later behavior needs the earlier binding rather than the replacement.

**Where template:** At {location} in {target}, inspect: A parameter, receiver, definition or repeated destructuring target is rebound before a required use.

**How:** Assignment and def statements replace the binding; repeated assignment targets retain the last stored value.
**Trigger template:** Use distinct {original_value} and {replacement_value}; execute {rebinding_site} and observe {later_use}.

**What:** A later call, attribute access or result uses the wrong object or value.
**Oracle template:** Under {binding_contract}, assert the expected original or replacement value at each required use.

**Applicability:** Intentional reuse and overwritten unused temporaries are valid; receiver names have no magic beyond binding conventions.

**Sources:** [ruff:PLR1704](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/redefined_argument_from_local.rs#L9-L38) (stable), [ruff:PLW0642](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/self_or_cls_assignment.rs#L11-L56) (stable), [ruff:PLW0128](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/redeclared_assigned_name.rs#L11-L39) (stable), [ruff:F811](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/redefined_while_unused.rs#L20-L75) (stable)

## py.invalid-module-exports — Invalid __all__ entries break the advertised module export interface

Category: `object-model`

**Where:** A module defines __all__ with invalid entries, an invalid container or missing names.
**Preconditions:** Consumers use the advertised wildcard export interface.

**Where template:** At {location} in {target}, inspect: A module defines __all__ with invalid entries, an invalid container or missing names.

**How:** Wildcard import resolves exported string names from the module; malformed entries or absent attributes cannot supply that interface.
**Trigger template:** Import {module} through its declared wildcard interface in an isolated namespace.

**What:** Export resolution fails or required public names are missing.
**Oracle template:** Under {module_contract}, assert successful exports and the exact required public name bindings.

**Applicability:** Module __getattr__ and supported lazy exports can provide names dynamically; verify runtime resolution.

**Sources:** [ruff:F822](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pyflakes/rules/undefined_export.rs#L6-L45) (stable), [ruff:PLE0604](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_all_object.rs#L8-L32) (stable), [ruff:PLE0605](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_all_format.rs#L8-L32) (stable)

## py.typevar-conflicting-variance — A type parameter requests incompatible variance modes

Category: `object-model`

**Where:** A TypeVar or related supported type-parameter constructor requests both covariance and contravariance.
**Preconditions:** The chosen type system or runtime constructor rejects the contradictory definition.

**Where template:** At {location} in {target}, inspect: A TypeVar or related supported type-parameter constructor requests both covariance and contravariance.

**How:** The definition gives one parameter mutually incompatible variance modes.
**Trigger template:** Construct or type-check {type_parameter_definition} under {target_typing_environment}.

**What:** Definition fails or the typing tool reports an invalid variance declaration.
**Oracle template:** Under {typing_contract}, assert the permitted variance definition and its diagnostic or construction behavior.

**Applicability:** Static and runtime enforcement differ by constructor and version; record the actual validation layer.

**Sources:** [ruff:PLC0131](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/type_bivariance.rs#L13-L59) (stable)

## py.slots-string-metadata — A single-string __slots__ value is misread as a sequence of slot names

Category: `object-model`

**Where:** __slots__ is one string and tooling iterates that metadata directly.
**Preconditions:** The consumer expects each iteration item to be a complete attribute name.

**Where template:** At {location} in {target}, inspect: __slots__ is one string and tooling iterates that metadata directly.

**How:** Class construction accepts a single slot-name string, but ordinary string iteration yields characters.
**Trigger template:** Use a multi-character {slot_name}, then run {slot_consumer} over the declared __slots__ value.

**What:** The consumer treats characters as slot names and misses or misreads attributes.
**Oracle template:** Under {metadata_contract}, assert full slot names are obtained and the corresponding attributes are processed.

**Applicability:** A single string is legal __slots__ syntax; normal attribute access can remain entirely correct.

**Sources:** [ruff:PLC0205](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/single_string_slots.rs#L10-L53) (stable)

## py.scope-declaration-conflict — Invalid global or nonlocal declarations prevent compilation

Category: `syntax`

**Where:** A name is both global and nonlocal, nonlocal lacks an enclosing binding, or a global declaration follows a forbidden use.
**Preconditions:** The fragment is compiled in its actual nested scopes.

**Where template:** At {location} in {target}, inspect: A name is both global and nonlocal, nonlocal lacks an enclosing binding, or a global declaration follows a forbidden use.

**How:** Scope declarations must be consistent with each other and with enclosing bindings and prior name use.
**Trigger template:** Compile {function_source} in {enclosing_source} on {target_interpreter}.

**What:** Compilation raises SyntaxError rather than reaching a runtime name lookup.
**Oracle template:** Under {scope_contract}, assert valid declarations and the required scope of each binding.

**Applicability:** This differs from UnboundLocalError, which arises when otherwise valid code reads an unassigned local at runtime.

**Sources:** [ruff:PLE0115](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/nonlocal_and_global.rs#L8-L46) (stable), [ruff:PLE0117](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/nonlocal_without_binding.rs#L6-L36) (stable), [ruff:PLE0118](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/load_before_global_declaration.rs#L7-L42) (stable)

## py.duplicate-base-class — Duplicate base or Generic inheritance rejects a class definition

Category: `object-model`

**Where:** A class repeats a base or combines PEP 695 type parameters with incompatible explicit Generic inheritance.
**Preconditions:** The target Python supports the source syntax and reaches class construction.

**Where template:** At {location} in {target}, inspect: A class repeats a base or combines PEP 695 type parameters with incompatible explicit Generic inheritance.

**How:** Class creation rejects duplicate base or Generic inheritance specifications.
**Trigger template:** Define {class_source} on {target_interpreter} using the actual resolved bases.

**What:** Class construction raises TypeError before instances can be created.
**Oracle template:** Under {inheritance_contract}, assert successful class definition and the intended base relationships.

**Applicability:** Aliases can resolve to the same base; PEP 695 syntax itself requires a sufficiently recent interpreter.

**Sources:** [ruff:PLE0241](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/duplicate_bases.rs#L13-L60) (stable), [ruff:RUF053](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/class_with_mixed_type_vars.rs#L19-L67) (stable)

## py.index-out-of-bounds — Sequence indexing crosses the valid positive or negative boundary

Category: `iteration`

**Where:** A sequence is indexed with a computed or hard-coded integer.
**Preconditions:** The index is outside the sequence valid index range on that path.

**Where template:** At {location} in {target}, inspect: A sequence is indexed with a computed or hard-coded integer.

**How:** Direct indexing rejects indices at or above length and below negative length instead of clamping like a slice.
**Trigger template:** Use {sequence} of length n and exercise {index_expression} at n, -n-1 and on an empty sequence.

**What:** IndexError replaces the required value or documented invalid-input handling.
**Oracle template:** Under {index_contract}, assert correct boundary values and the required rejection policy.

**Applicability:** An expected IndexError is valid API behavior; custom __getitem__ implementations can have other domains.

**Sources:** [ruff:PLE0643](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/potential_index_error.rs#L9-L24) (stable), [python:sequence-operations](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/builtins/stdtypes.rst#L929-L1132) (python-3.13)

## py.bare-raise-without-exception — A bare raise executes without an active exception

Category: `exceptions`

**Where:** A bare raise is reached on a path with no active exception to re-raise.
**Preconditions:** The error branch expects to re-raise or signal a particular application exception.

**Where template:** At {location} in {target}, inspect: A bare raise is reached on a path with no active exception to re-raise.

**How:** Bare raise uses the active handled exception; none is available on that path.
**Trigger template:** Execute {raise_site} from both the normal path and any active exception path.

**What:** A RuntimeError replaces the intended error or propagation.
**Oracle template:** Under {error_contract}, assert the required exception class and cause on each supported path.

**Applicability:** A helper called during active exception handling can legally use bare raise; lexical position alone is insufficient.

**Sources:** [ruff:PLE0704](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/misplaced_bare_raise.rs#L10-L46) (stable)

## py.logging-format-arguments — Deferred logging formatting receives the wrong number of arguments

Category: `strings`

**Where:** A logging call supplies positional formatting arguments that do not match its message placeholders.
**Preconditions:** The log record reaches a handler that formats it.

**Where template:** At {location} in {target}, inspect: A logging call supplies positional formatting arguments that do not match its message placeholders.

**How:** Logging applies percent-style formatting lazily; argument-count mismatch fails during record formatting.
**Trigger template:** Emit {logging_call} with a controlled handler and capture formatting or handler errors.

**What:** The intended log entry is lost or diagnostics are emitted; handler policy determines whether an exception escapes.
**Oracle template:** Under {logging_contract}, assert the final formatted record and required error handling at the handler boundary.

**Applicability:** Disabled logging levels may hide the issue; do not assume every handler raises TypeError directly to the caller.

**Sources:** [ruff:PLE1205](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/logging.rs#L55-L88) (stable), [ruff:PLE1206](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/logging.rs#L13-L46) (stable)

## py.getenv-type-contract — Environment lookups violate key or fallback type assumptions

Category: `resources`

**Where:** os.getenv receives a non-string key or a fallback incompatible with downstream string handling.
**Preconditions:** The selected key and present/missing environment cases reach the affected path.

**Where template:** At {location} in {target}, inspect: os.getenv receives a non-string key or a fallback incompatible with downstream string handling.

**How:** Keys must be strings; a missing lookup can return its supplied default unchanged instead of an environment string.
**Trigger template:** Test {lookup_expression} with an invalid key and with a dedicated key both present and missing.

**What:** Lookup raises TypeError or downstream code receives an unexpected value type.
**Oracle template:** Under {environment_contract}, assert the key domain and the required present/missing return types.

**Applicability:** A non-string fallback can be deliberate if callers handle it; use synthetic keys in isolated tests.

**Sources:** [ruff:PLE1507](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_envvar_value.rs#L11-L35) (stable), [ruff:PLW1508](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/invalid_envvar_default.rs#L11-L38) (stable)

## py.singledispatch-binding — A dispatch decorator uses the receiver instead of the intended argument

Category: `object-model`

**Where:** singledispatch decorates a bound method or singledispatchmethod decorates a standalone function.
**Preconditions:** Dispatch must follow the intended non-receiver argument and descriptor context.

**Where template:** At {location} in {target}, inspect: singledispatch decorates a bound method or singledispatchmethod decorates a standalone function.

**How:** Function and method dispatch decorators implement different argument and binding protocols.
**Trigger template:** Call {dispatcher} with two distinct supported {argument_types} through its public binding form.

**What:** The wrong implementation runs or the decorated object is unusable in that context.
**Oracle template:** Under {dispatch_contract}, assert the selected implementation and result for every supported type.

**Applicability:** Static methods and explicitly designed descriptor combinations need separate binding analysis.

**Sources:** [ruff:PLE1519](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/singledispatch_method.rs#L12-L56) (stable), [ruff:PLE1520](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/singledispatchmethod_function.rs#L12-L46) (stable)

## py.bidi-source-obfuscation — Bidirectional formatting makes displayed source diverge from token order

Category: `source-integrity`

**Where:** Source text contains bidirectional formatting controls.
**Preconditions:** Review or source-processing logic assumes displayed order accurately conveys executable token order.

**Where template:** At {location} in {target}, inspect: Source text contains bidirectional formatting controls.

**How:** Bidirectional display reordering can make comments, strings or neighboring source appear in a misleading order.
**Trigger template:** Inspect {source_fragment} in escaped-codepoint form and compare its tokens or AST with the displayed rendering.

**What:** A reviewer or source consumer attributes behavior to the wrong apparent code region.
**Oracle template:** Under {source_contract}, compare parsed behavior with the intended logic and enforce the required source-display policy.

**Applicability:** Legitimate right-to-left text is common; presence of a control character does not by itself prove a vulnerability.

**Sources:** [ruff:PLE2502](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/bidirectional_unicode.rs#L28-L55) (stable)

## py.property-requires-arguments — A property getter requires arguments that attribute access cannot supply

Category: `object-model`

**Where:** A property getter requires positional or keyword arguments beyond its receiver.
**Preconditions:** The property is read through normal attribute access.

**Where template:** At {location} in {target}, inspect: A property getter requires positional or keyword arguments beyond its receiver.

**How:** The descriptor calls its getter with the instance and does not receive application-supplied method arguments.
**Trigger template:** Construct {instance} and read {property_name} through attribute access.

**What:** The getter raises a missing-argument TypeError.
**Oracle template:** Under {property_contract}, assert attribute access returns the required value without extra call arguments.

**Applicability:** Optional getter parameters can be satisfied by defaults; a method intended to take arguments may be a better API.

**Sources:** [ruff:PLR0206](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/property_with_parameters.rs#L9-L44) (stable)

## py.loop-else-without-break — A loop else executes after a successful search because no break occurs

Category: `iteration`

**Where:** A search loop has an else clause but no relevant break.
**Preconditions:** The else branch is intended only for a failed search.

**Where template:** At {location} in {target}, inspect: A search loop has an else clause but no relevant break.

**How:** Loop else runs on normal exhaustion regardless of whether a match was encountered unless the loop exits with break.
**Trigger template:** Supply {items} containing a match for {predicate} and then allow normal exhaustion.

**What:** The not-found branch runs after successful processing.
**Oracle template:** Under {search_contract}, assert found and not-found effects are mutually correct for matching, missing and empty inputs.

**Applicability:** A loop else can intentionally run on normal exhaustion; return and exceptions also affect control flow.

**Sources:** [ruff:PLW0120](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/useless_else_on_loop.rs#L19-L57) (stable)

## py.self-assignment — A mistaken self-assignment leaves required state unchanged

Category: `scope`

**Where:** A variable is assigned to itself where an update or different source value was intended.
**Preconditions:** The required state transition changes that binding.

**Where template:** At {location} in {target}, inspect: A variable is assigned to itself where an update or different source value was intended.

**How:** Ordinary name self-assignment stores the same object reference without performing the intended computation.
**Trigger template:** Execute {assignment_site} with distinct {current_value} and {required_value}.

**What:** The stored value stays unchanged.
**Oracle template:** Under {state_contract}, assert the required post-assignment value and downstream effect.

**Applicability:** Attribute assignment can invoke descriptors and is not necessarily inert; this card concerns ordinary name bindings.

**Sources:** [ruff:PLW0127](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/self_assigning_variable.rs#L11-L29) (stable)

## py.invalid-open-mode — An invalid file mode rejects opening before the intended I/O

Category: `resources`

**Where:** open receives an invalid mode character or incompatible combination of modes.
**Preconditions:** The target interpreter and file API enforce that mode grammar.

**Where template:** At {location} in {target}, inspect: open receives an invalid mode character or incompatible combination of modes.

**How:** File-opening mode parsing rejects unsupported or contradictory flags.
**Trigger template:** Call {open_expression} with a temporary file and the exact {mode_value} on {target_interpreter}.

**What:** Opening raises before the required read, write or create operation.
**Oracle template:** Under {file_contract}, assert supported mode behavior and required invalid-mode rejection.

**Applicability:** Historical modes such as U have version-specific support; use the actual supported Python versions.

**Sources:** [ruff:PLW1501](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/bad_open_mode.rs#L11-L42) (stable)

## py.shallow-environ-proxy — A shallow copy of os.environ still changes process environment state

Category: `resources`

**Where:** copy.copy is used on the os.environ proxy as though it produced an independent environment snapshot.
**Preconditions:** The caller intends mutations of the copy not to affect process environment state.

**Where template:** At {location} in {target}, inspect: copy.copy is used on the os.environ proxy as though it produced an independent environment snapshot.

**How:** The shallow proxy copy retains shared backing state and environment mutation behavior.
**Trigger template:** In an isolated process, shallow-copy os.environ and mutate a dedicated {test_key} through {copied_proxy}.

**What:** The original environment or child-process environment changes unexpectedly.
**Oracle template:** Under {environment_contract}, assert isolation of the original mapping and required child environment.

**Applicability:** os.environ.copy() or an explicit dict snapshot has different semantics; never test with existing secret-bearing keys.

**Sources:** [ruff:PLW1507](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/shallow_copy_environ.rs#L10-L48) (stable)

## py.preexec-thread-deadlock — preexec_fn can deadlock a child forked from a multithreaded process

Category: `resources`

**Where:** subprocess.Popen uses preexec_fn while the parent has multiple threads.
**Preconditions:** The child callback can encounter a lock inherited from a thread absent in the child.

**Where template:** At {location} in {target}, inspect: subprocess.Popen uses preexec_fn while the parent has multiple threads.

**How:** After fork, locks can remain held without their owning thread, blocking child setup before exec.
**Trigger template:** Review {preexec_callback} and reproduce {controlled_lock_schedule} only in a bounded isolated subprocess harness.

**What:** Child creation or pre-exec setup hangs before the intended command runs.
**Oracle template:** Under {process_contract}, assert bounded child startup and required process setup using documented subprocess options.

**Applicability:** Scheduling is nondeterministic; a passing run cannot prove safety, and every reproduction needs timeout and cleanup.

**Sources:** [ruff:PLW1509](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/subprocess_popen_preexec_fn.rs#L11-L45) (stable)

## py.assert-print-message — An assertion prints its message but stores None in the exception

Category: `testing`

**Where:** An assert message expression is print(message).
**Preconditions:** Consumers require the diagnostic in AssertionError rather than only stdout.

**Where template:** At {location} in {target}, inspect: An assert message expression is print(message).

**How:** print returns None, so the failing assertion stores None as its message after producing a stdout side effect.
**Trigger template:** Make {asserted_condition} false and capture both AssertionError.args and stdout.

**What:** The exception lacks the required message and output appears on an unexpected channel.
**Oracle template:** Under {diagnostic_contract}, assert the exception arguments and output channels independently.

**Applicability:** This changes diagnostics rather than whether the assertion condition fails; explicit print side effects can be intentional.

**Sources:** [ruff:RUF030](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/assert_with_print_message.rs#L10-L43) (stable)

## py.post-init-default-not-constructor-default — A __post_init__ default does not make an InitVar constructor argument optional

Category: `object-model`

**Where:** A dataclass __post_init__ parameter has a default while its corresponding InitVar field does not.
**Preconditions:** The generated constructor is expected to allow omitting that init-only argument.

**Where template:** At {location} in {target}, inspect: A dataclass __post_init__ parameter has a default while its corresponding InitVar field does not.

**How:** The generated __init__ signature comes from dataclass field declarations, not defaults on __post_init__.
**Trigger template:** Instantiate {dataclass} while omitting {initvar_parameter}, then inspect the generated constructor signature.

**What:** Instantiation raises a missing-argument error despite the __post_init__ default.
**Oracle template:** Under {construction_contract}, assert the generated signature and required omitted-argument behavior.

**Applicability:** Defaults in __post_init__ can affect direct calls to it; they do not define generated constructor defaults.

**Sources:** [ruff:RUF033](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/post_init_default.rs#L18-L80) (stable)

## py.identical-branches — Copied identical branches erase a required distinction between cases

Category: `logic`

**Where:** Conditional branches or if-expression arms contain identical outcomes.
**Preconditions:** The specification requires at least two cases to produce different results or effects.

**Where template:** At {location} in {target}, inspect: Conditional branches or if-expression arms contain identical outcomes.

**How:** Both branches perform the same computation despite the intended distinction.
**Trigger template:** Supply {first_case} and {second_case} that the contract requires to behave differently.

**What:** The required output or side-effect distinction is absent.
**Oracle template:** Under {branch_contract}, compare outcomes for each distinct specified case.

**Applicability:** Identical branches are often a valid simplification opportunity; only a differing contract establishes a bug.

**Sources:** [ruff:RUF034](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/useless_if_else.rs#L9-L27) (stable), [ruff:SIM114](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/flake8_simplify/rules/if_with_same_arms.rs#L19-L41) (stable)

## py.assert-message-instead-of-comparison — An assertion message is mistaken for an expected comparison value

Category: `testing`

**Where:** An assertion uses a computed value as its condition and the expected literal as its message.
**Preconditions:** The test intends exact equality rather than a truthiness test.

**Where template:** At {location} in {target}, inspect: An assertion uses a computed value as its condition and the expected literal as its message.

**How:** assert actual, expected checks only actual truthiness and reserves expected for failure diagnostics.
**Trigger template:** Choose {actual_value} that is truthy but unequal to {expected_value}, then execute {assertion}.

**What:** The assertion passes despite a wrong value.
**Oracle template:** Under {value_contract}, assert the required equality or other comparison directly.

**Applicability:** Non-string assertion messages are legal; the failure requires evidence that an exact comparison was intended.

**Sources:** [ruff:RUF040](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/invalid_assert_message_literal_argument.rs#L9-L31) (stable)

## py.implicit-dataclass-classvar — An unannotated dataclass attribute is not an instance constructor field

Category: `object-model`

**Where:** A dataclass body assigns an unannotated attribute intended as a field.
**Preconditions:** The caller expects that attribute to appear in generated __init__ or per-instance field metadata.

**Where template:** At {location} in {target}, inspect: A dataclass body assigns an unannotated attribute intended as a field.

**How:** An unannotated assignment remains a class attribute instead of a dataclass field.
**Trigger template:** Construct {dataclass} with {attribute} as a keyword and inspect dataclass field metadata.

**What:** The constructor rejects the keyword or the required field is missing.
**Oracle template:** Under {field_contract}, assert the constructor signature, field list and intended per-instance state.

**Applicability:** Class constants are intentionally not fields; a mutable class attribute has an additional sharing risk covered separately.

**Sources:** [ruff:RUF045](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/implicit_classvar_in_dataclass.rs#L11-L57) (preview)

## py.version-integer-parsing — Splitting a version into integers rejects legitimate release suffixes

Category: `strings`

**Where:** A version string is split on dots and every component is passed to int.
**Preconditions:** Supported versions may include prerelease, postrelease, development or local suffixes.

**Where template:** At {location} in {target}, inspect: A version string is split on dots and every component is passed to int.

**How:** A package version need not consist only of dot-separated integer components.
**Trigger template:** Parse {version_string} containing a supported nonnumeric suffix alongside a plain release control case.

**What:** Parsing raises ValueError or version handling rejects a supported release.
**Oracle template:** Under {version_contract}, assert acceptance and ordering for the exact supported version scheme.

**Applicability:** Use a parser for the required scheme; not every arbitrary application version claims packaging-version compliance.

**Sources:** [ruff:RUF048](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/map_int_version_parsing.rs#L10-L40) (stable)

## py.dataclass-enum-equality — Decorating an Enum as a dataclass collapses required member distinctions

Category: `object-model`

**Where:** An Enum class is directly decorated with dataclass.
**Preconditions:** Distinct enum members must compare as distinct in the application.

**Where template:** At {location} in {target}, inspect: An Enum class is directly decorated with dataclass.

**How:** Dataclass-generated comparison behavior can interfere with normal enum member equality.
**Trigger template:** Define {enum_class} and compare two distinct {members} under {target_interpreter}.

**What:** Distinct members compare equal or other generated dataclass behavior violates the enum contract.
**Oracle template:** Under {enum_contract}, assert identity and required equality relationships for distinct members.

**Applicability:** An enum with a dataclass mixin is a different design; supported combinations and behavior vary by Python version.

**Sources:** [ruff:RUF049](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/dataclass_enum.rs#L10-L50) (stable)

## py.formfeed-indentation — A form-feed inside indentation changes or obscures block structure

Category: `source-integrity`

**Where:** Leading whitespace contains a form-feed after a space or tab.
**Preconditions:** The displayed indentation is assumed to match the intended parsed block structure.

**Where template:** At {location} in {target}, inspect: Leading whitespace contains a form-feed after a space or tab.

**How:** Form-feed within indentation has interpreter-dependent or undefined indentation effects beyond the documented leading case.
**Trigger template:** Inspect escaped whitespace in {source_fragment} and parse or compile it with {target_interpreter}.

**What:** Compilation fails or the parsed block grouping differs from the required source structure.
**Oracle template:** Under {source_contract}, compare parsed nesting with intended nesting and enforce the chosen whitespace policy.

**Applicability:** Do not assume a portable exact indentation effect; a form-feed at the beginning of a line has separately documented handling.

**Sources:** [ruff:RUF054](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/indented_form_feed.rs#L10-L36) (preview)

## py.annotations-in-class-dict — Direct class-dictionary annotation access misses version-dependent annotations

Category: `object-model`

**Where:** Annotation introspection reads cls.__dict__["__annotations__"] or .get directly.
**Preconditions:** The code supports annotation storage or evaluation behavior not represented by that raw dictionary entry.

**Where template:** At {location} in {target}, inspect: Annotation introspection reads cls.__dict__["__annotations__"] or .get directly.

**How:** The class dictionary is not a stable public abstraction for every supported Python annotation implementation.
**Trigger template:** Inspect {class_with_annotations} under each supported {annotation_mode} and Python version.

**What:** Required annotations are missing, a KeyError occurs or the consumer receives incomplete metadata.
**Oracle template:** Under {annotation_contract}, compare required annotation names and evaluation policy using the version-appropriate public introspection API.

**Applicability:** Deferred annotation APIs can evaluate expressions; preserve the specified evaluation policy and do not treat all introspection functions as identical.

**Sources:** [ruff:RUF063](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/access_annotations_from_class_dict.rs#L8-L78) (stable)

## py.permission-radix — A decimal permission literal sets different bits than intended octal permissions

Category: `resources`

**Where:** chmod or another mode-taking API receives a decimal-looking permission literal.
**Preconditions:** The intended value was expressed as familiar octal permission digits.

**Where template:** At {location} in {target}, inspect: chmod or another mode-taking API receives a decimal-looking permission literal.

**How:** The numeric literal is interpreted in its written radix, so decimal digits and octal digits represent different bitmasks.
**Trigger template:** Apply {mode_literal} to a temporary resource and inspect its permission bits on {target_platform}.

**What:** The resulting access bits differ from the intended permission policy.
**Oracle template:** Under {permission_contract}, compare the masked actual permissions with the required octal bitmask.

**Applicability:** A decimal bitmask may be intentional; umask and platform semantics must be accounted for separately.

**Sources:** [ruff:RUF064](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/non_octal_permissions.rs#L12-L77) (stable)

## py.path-character-prefix — A textual path prefix is mistaken for a common path component

Category: `resources`

**Where:** os.path.commonprefix is used for path ancestry or a shared-directory decision.
**Preconditions:** The contract requires component boundaries or containment rather than character overlap.

**Where template:** At {location} in {target}, inspect: os.path.commonprefix is used for path ancestry or a shared-directory decision.

**How:** commonprefix compares characters and can return a partial component shared by unrelated paths.
**Trigger template:** Use {paths} with a common spelling but different directory components, such as a directory name and a longer sibling name.

**What:** The computed ancestor is invalid or an unrelated sibling is classified as inside the required directory.
**Oracle template:** Under {path_contract}, assert component-aware ancestry under the required normalization and filesystem semantics.

**Applicability:** commonpath alone does not resolve symlinks or establish a complete filesystem containment policy; textual prefix is valid for purely textual tasks.

**Sources:** [ruff:RUF071](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/os_path_commonprefix.rs#L10-L72) (stable)

## py.method-receiver-default — A receiver default allows an unintended unbound method call

Category: `object-model`

**Where:** An instance receiver parameter has a default such as self=None.
**Preconditions:** The method must operate on an explicitly bound instance and direct class calls should not silently use a fallback receiver.

**Where template:** At {location} in {target}, inspect: An instance receiver parameter has a default such as self=None.

**How:** Calling an instance method through the class does not supply self; the parameter default can mask the missing receiver.
**Trigger template:** Invoke {method} through both {bound_instance} and its class without an explicit receiver.

**What:** The unbound call uses the fallback receiver or fails later with a misleading attribute error.
**Oracle template:** Under {method_contract}, assert required binding behavior and explicit rejection or documented handling of unbound calls.

**Applicability:** Ordinary bound classmethods already receive cls; a receiver default may be intentional for explicit class-level invocation.

**Sources:** [ruff:RUF077](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/method_receiver_default.rs#L12-L57) (preview)

## py.membership-wrong-domain — Membership checks the container protocol rather than the intended application domain

Category: `logic`

**Where:** in or not in is used on mappings, strings or other containers with different membership semantics.
**Preconditions:** The application expects value membership, exact tokens or another domain not supplied by that container protocol.

**Where template:** At {location} in {target}, inspect: in or not in is used on mappings, strings or other containers with different membership semantics.

**How:** dict membership tests keys; string membership tests substrings, and an empty string is a substring of every string.
**Trigger template:** Use {container} where {candidate} is present only as a value, partial substring or empty string, rather than as an intended member.

**What:** The membership decision disagrees with the required domain.
**Oracle template:** Under {membership_contract}, assert membership over the explicit required key, value, token or substring domain.

**Applicability:** These are normal Python semantics; select the intended domain from the specification before judging the result.

**Sources:** [python:membership](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L1702-L1750) (python-3.13)

## py.empty-membership — Membership against an always-empty collection cannot distinguish candidates

Category: `logic`

**Where:** A membership condition uses a collection that is empty on every relevant path.
**Preconditions:** The condition is intended to accept at least one candidate.

**Where template:** At {location} in {target}, inspect: A membership condition uses a collection that is empty on every relevant path.

**How:** Membership in an empty built-in collection is false for every candidate; not in is true.
**Trigger template:** Evaluate {membership_condition} for both {accepted_candidate} and {rejected_candidate}.

**What:** A required acceptance or rejection branch cannot be reached.
**Oracle template:** Under {membership_contract}, assert different required outcomes and verify collection initialization.

**Applicability:** Constant membership tests can be intentional; custom __contains__ methods may not follow built-in empty-container semantics.

**Sources:** [ruff:RUF060](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/in_empty_collection.rs#L10-L30) (stable), [python:membership](https://github.com/python/cpython/blob/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc/reference/expressions.rst#L1702-L1750) (python-3.13)

## py.slot-redefinition — A subclass slot shadows distinct storage owned by its base class

Category: `object-model`

**Where:** A subclass declares a slot with the same name as an inherited slot.
**Preconditions:** Base-class and subclass behavior assume one consistent attribute storage location.

**Where template:** At {location} in {target}, inspect: A subclass declares a slot with the same name as an inherited slot.

**How:** The subclass descriptor hides the base descriptor under ordinary attribute lookup, while the base slot can still be accessed through its own descriptor.
**Trigger template:** Create {instance}, store distinguishable values through {base_slot_descriptor} and ordinary {attribute} access, then run the affected base operation.

**What:** The base operation or serializer observes different storage from ordinary attribute access or cannot retrieve required state.
**Oracle template:** Under {attribute_contract}, assert consistent required state across normal access and the supported base-class operations.

**Applicability:** Slot redefinition is discouraged and behavior can be implementation-sensitive; do not assume an exact storage layout across interpreters.

**Sources:** [ruff:PLW0244](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/redefined_slots_in_subclass.rs#L14-L43) (preview)

## py.self-import-partial-initialization — A self-import accesses a module before its required names are initialized

Category: `scope`

**Where:** A module imports itself or accesses itself through an import during initialization.
**Preconditions:** The import path requests a name that has not yet been defined.

**Where template:** At {location} in {target}, inspect: A module imports itself or accesses itself through an import during initialization.

**How:** Import cycles can expose the partially initialized module object before the required definitions exist.
**Trigger template:** Import {module} in a fresh isolated interpreter and reach {premature_name_access}.

**What:** Import resolution or attribute access fails before module initialization completes.
**Oracle template:** Under {module_contract}, assert successful initialization and availability of the required names at their actual use sites.

**Applicability:** A self-import can succeed by returning the cached partial module; it does not unconditionally raise ImportError.

**Sources:** [ruff:PLW0406](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/pylint/rules/import_self.rs#L10-L28) (stable)

## py.invalid-sequence-index-type — A sequence index lacks the required integer or slice protocol

Category: `iteration`

**Where:** A built-in sequence is indexed with an unsupported index value.
**Preconditions:** The value is neither a slice nor an object accepted by the integer-index protocol.

**Where template:** At {location} in {target}, inspect: A built-in sequence is indexed with an unsupported index value.

**How:** Sequence subscription validates its index protocol rather than interpreting arbitrary strings or floats as indices.
**Trigger template:** Apply {index_value} to {sequence}, including an invalid-type case and a valid integer-index control.

**What:** Subscription raises TypeError instead of the required element or invalid-input handling.
**Oracle template:** Under {index_contract}, assert the supported index domain and the required rejection policy.

**Applicability:** Objects implementing __index__ can be valid without being int instances; mapping keys and custom __getitem__ have different rules.

**Sources:** [ruff:RUF016](https://github.com/astral-sh/ruff/blob/bfa2407e98ee1343caeefd02b4b69043509baa8c/crates/ruff_linter/src/rules/ruff/rules/invalid_index_type.rs#L11-L31) (stable)
