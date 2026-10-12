# Execution-function index

Generated from Python AST; source files are read without importing or executing them. Includes nested helpers and class methods. Function bodies and call order are explained in [PIPELINES.md](PIPELINES.md).

## eval_v3m.py

| Symbol | Source location | Kind |
|---|---|---|
| `worker` | [eval_v3m.py:20](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:20) | function |
| `worker.accepts` | [eval_v3m.py:42](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:42) | function |
| `worker.candidate` | [eval_v3m.py:63](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:63) | function |
| `agreement` | [eval_v3m.py:75](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:75) | function |
| `evaluate` | [eval_v3m.py:82](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:82) | function |
| `evaluate.task` | [eval_v3m.py:111](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:111) | function |
| `evaluate.fmt` | [eval_v3m.py:166](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:166) | function |
| `main` | [eval_v3m.py:196](/home/phong/dev/ConceptTester/trickcatcher_linefacts/eval_v3m.py:196) | function |

## evaluate.py

| Symbol | Source location | Kind |
|---|---|---|
| `extract_asserts` | [evaluate.py:27](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:27) | function |
| `worker` | [evaluate.py:47](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:47) | function |
| `worker.run_assert` | [evaluate.py:71](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:71) | function |
| `worker.run_assert.wrapped` | [evaluate.py:74](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:74) | function |
| `evaluate` | [evaluate.py:120](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:120) | function |
| `sign_p` | [evaluate.py:167](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:167) | function |
| `report` | [evaluate.py:172](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:172) | function |
| `main` | [evaluate.py:207](/home/phong/dev/ConceptTester/trickcatcher_linefacts/evaluate.py:207) | function |

## facts.py

| Symbol | Source location | Kind |
|---|---|---|
| `scalar_variants` | [facts.py:43](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:43) | function |
| `variants` | [facts.py:58](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:58) | function |
| `literal_ok` | [facts.py:88](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:88) | function |
| `fuzz_inputs` | [facts.py:95](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:95) | function |
| `fuzz_inputs.add` | [facts.py:98](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:98) | function |
| `valid_fuzz` | [facts.py:150](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:150) | function |
| `valid_fuzz.add` | [facts.py:156](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:156) | function |
| `call_src` | [facts.py:199](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:199) | function |
| `statements` | [facts.py:206](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:206) | function |
| `statements.walk` | [facts.py:212](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:212) | function |
| `mutation_points` | [facts.py:240](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:240) | function |
| `make_mutant` | [facts.py:287](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:287) | function |
| `make_mutant.frag` | [facts.py:297](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:297) | function |
| `t_outcome` | [facts.py:374](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:374) | function |
| `t_outcome_placebo` | [facts.py:381](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:381) | function |
| `t_stmt` | [facts.py:387](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:387) | function |
| `t_stmt_placebo` | [facts.py:392](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:392) | function |
| `t_mutant` | [facts.py:396](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:396) | function |
| `say` | [facts.py:416](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:416) | function |
| `describe` | [facts.py:425](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:425) | function |
| `call_plausible` | [facts.py:460](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:460) | function |
| `call_plausible.types` | [facts.py:463](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:463) | function |
| `output_text` | [facts.py:483](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:483) | function |
| `new_facts` | [facts.py:505](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:505) | function |
| `new_facts.emit` | [facts.py:509](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:509) | function |
| `new_facts.ancestors` | [facts.py:557](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:557) | function |
| `slot` | [facts.py:583](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:583) | function |
| `display_slot` | [facts.py:587](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:587) | function |
| `set_blocks` | [facts.py:592](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:592) | function |
| `tier` | [facts.py:601](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:601) | function |
| `du_key` | [facts.py:605](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:605) | function |
| `pick` | [facts.py:609](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:609) | function |
| `make_forced` | [facts.py:636](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:636) | function |
| `make_forced.Force` | [facts.py:639](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:639) | class |
| `make_forced.Force.visit` | [facts.py:640](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:640) | function |
| `make_forced.force` | [facts.py:650](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:650) | function |
| `guard_features` | [facts.py:658](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:658) | function |
| `parse_examples` | [facts.py:716](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:716) | function |
| `doc_fail` | [facts.py:767](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:767) | function |
| `main` | [facts.py:781](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:781) | function |
| `main.first_hit` | [facts.py:826](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:826) | function |
| `main.dedupe` | [facts.py:940](/home/phong/dev/ConceptTester/trickcatcher_linefacts/facts.py:940) | function |

## fuzz_validity.py

| Symbol | Source location | Kind |
|---|---|---|
| `EvalPlus` | [fuzz_validity.py:10](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:10) | class |
| `EvalPlus.__init__` | [fuzz_validity.py:12](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:12) | function |
| `EvalPlus.read` | [fuzz_validity.py:22](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:22) | function |
| `EvalPlus.__call__` | [fuzz_validity.py:32](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:32) | function |
| `EvalPlus.close` | [fuzz_validity.py:39](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:39) | function |
| `Mined` | [fuzz_validity.py:51](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:51) | class |
| `validator` | [fuzz_validity.py:60](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:60) | function |
| `worker` | [fuzz_validity.py:71](/home/phong/dev/ConceptTester/trickcatcher_linefacts/fuzz_validity.py:71) | function |

## gen_evaluation.py

| Symbol | Source location | Kind |
|---|---|---|
| `input_metrics` | [gen_evaluation.py:16](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_evaluation.py:16) | function |
| `report` | [gen_evaluation.py:59](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_evaluation.py:59) | function |

## gen_inputs.py

| Symbol | Source location | Kind |
|---|---|---|
| `load_contracts` | [gen_inputs.py:23](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:23) | function |
| `arity` | [gen_inputs.py:34](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:34) | function |
| `extract_generator` | [gen_inputs.py:41](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:41) | function |
| `sandbox` | [gen_inputs.py:50](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:50) | function |
| `generate_candidates` | [gen_inputs.py:67](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:67) | function |
| `witness_candidates` | [gen_inputs.py:80](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:80) | function |
| `classify` | [gen_inputs.py:97](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:97) | function |
| `classify_worker` | [gen_inputs.py:119](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:119) | function |
| `feedback` | [gen_inputs.py:189](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:189) | function |
| `select` | [gen_inputs.py:202](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_inputs.py:202) | function |

## gen_prompts.py

| Symbol | Source location | Kind |
|---|---|---|
| `read_original_templates` | [gen_prompts.py:23](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_prompts.py:23) | function |
| `messages` | [gen_prompts.py:34](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_prompts.py:34) | function |
| `generator_messages` | [gen_prompts.py:38](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_prompts.py:38) | function |
| `oracle_messages` | [gen_prompts.py:49](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_prompts.py:49) | function |
| `concept_toolinput_messages` | [gen_prompts.py:53](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_prompts.py:53) | function |
| `seed` | [gen_prompts.py:65](/home/phong/dev/ConceptTester/trickcatcher_linefacts/gen_prompts.py:65) | function |

## generate.py

| Symbol | Source location | Kind |
|---|---|---|
| `bundle` | [generate.py:40](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:40) | function |
| `select` | [generate.py:49](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:49) | function |
| `rebuild` | [generate.py:60](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:60) | function |
| `prompts` | [generate.py:75](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:75) | function |
| `export` | [generate.py:89](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:89) | function |
| `run` | [generate.py:102](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:102) | function |
| `run.work` | [generate.py:120](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:120) | function |
| `main` | [generate.py:138](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generate.py:138) | function |

## generator_worker.py

| Symbol | Source location | Kind |
|---|---|---|
| `CallTimeout` | [generator_worker.py:13](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generator_worker.py:13) | class |
| `timed_out` | [generator_worker.py:17](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generator_worker.py:17) | function |
| `main` | [generator_worker.py:21](/home/phong/dev/ConceptTester/trickcatcher_linefacts/generator_worker.py:21) | function |

## llm_client.py

| Symbol | Source location | Kind |
|---|---|---|
| `NoRedirect` | [llm_client.py:17](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:17) | class |
| `NoRedirect.redirect_request` | [llm_client.py:18](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:18) | function |
| `atomic_json` | [llm_client.py:22](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:22) | function |
| `Client` | [llm_client.py:30](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:30) | class |
| `Client.__init__` | [llm_client.py:31](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:31) | function |
| `Client._log` | [llm_client.py:51](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:51) | function |
| `Client.chat` | [llm_client.py:55](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:55) | function |
| `Client._chat` | [llm_client.py:59](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:59) | function |
| `Client.chat_many` | [llm_client.py:106](/home/phong/dev/ConceptTester/trickcatcher_linefacts/llm_client.py:106) | function |

## offline.py

| Symbol | Source location | Kind |
|---|---|---|
| `excluded` | [offline.py:26](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:26) | function |
| `skip_pilot` | [offline.py:30](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:30) | function |
| `plus_check_src` | [offline.py:34](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:34) | function |
| `worker` | [offline.py:46](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:46) | function |
| `worker.cand` | [offline.py:62](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:62) | function |
| `worker.hit` | [offline.py:93](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:93) | function |
| `run_all` | [offline.py:103](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:103) | function |
| `sign_p` | [offline.py:126](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:126) | function |
| `report` | [offline.py:131](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:131) | function |
| `report.pf` | [offline.py:149](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:149) | function |
| `report.sets` | [offline.py:153](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline.py:153) | function |

## offline_metrics_v3m.py

| Symbol | Source location | Kind |
|---|---|---|
| `pf` | [offline_metrics_v3m.py:11](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:11) | function |
| `sign_p` | [offline_metrics_v3m.py:15](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:15) | function |
| `metrics` | [offline_metrics_v3m.py:19](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:19) | function |
| `selected` | [offline_metrics_v3m.py:43](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:43) | function |
| `pool` | [offline_metrics_v3m.py:45](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:45) | function |
| `enriched_metrics` | [offline_metrics_v3m.py:47](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:47) | function |
| `kind_metrics` | [offline_metrics_v3m.py:56](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:56) | function |
| `analyze` | [offline_metrics_v3m.py:64](/home/phong/dev/ConceptTester/trickcatcher_linefacts/offline_metrics_v3m.py:64) | function |

## oracle_b01.py

| Symbol | Source location | Kind |
|---|---|---|
| `dpp_templates` | [oracle_b01.py:75](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:75) | function |
| `load_run` | [oracle_b01.py:86](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:86) | function |
| `call_of` | [oracle_b01.py:93](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:93) | function |
| `expected_of` | [oracle_b01.py:104](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:104) | function |
| `code_block` | [oracle_b01.py:114](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:114) | function |
| `collect` | [oracle_b01.py:119](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:119) | function |
| `chunks` | [oracle_b01.py:132](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:132) | function |
| `msgs` | [oracle_b01.py:143](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:143) | function |
| `llm` | [oracle_b01.py:147](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:147) | function |
| `llm.run_job` | [oracle_b01.py:169](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:169) | function |
| `b1_expected` | [oracle_b01.py:180](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:180) | function |
| `by_task` | [oracle_b01.py:198](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:198) | function |
| `post_of` | [oracle_b01.py:209](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:209) | function |
| `variants` | [oracle_b01.py:221](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:221) | function |
| `mutant_source` | [oracle_b01.py:226](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:226) | function |
| `mutants` | [oracle_b01.py:236](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:236) | function |
| `worker` | [oracle_b01.py:246](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:246) | function |
| `worker.TO` | [oracle_b01.py:249](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:249) | class |
| `worker.alarm` | [oracle_b01.py:252](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:252) | function |
| `worker.timed` | [oracle_b01.py:259](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:259) | function |
| `worker.load` | [oracle_b01.py:270](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:270) | function |
| `worker.passes_base` | [oracle_b01.py:276](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:276) | function |
| `worker.same` | [oracle_b01.py:281](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:281) | function |
| `worker.holds` | [oracle_b01.py:304](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:304) | function |
| `worker.judge` | [oracle_b01.py:329](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:329) | function |
| `worker.unanimous` | [oracle_b01.py:333](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:333) | function |
| `sign_p` | [oracle_b01.py:375](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:375) | function |
| `execute` | [oracle_b01.py:380](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:380) | function |
| `execute.run_task` | [oracle_b01.py:396](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:396) | function |
| `judges` | [oracle_b01.py:415](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:415) | function |
| `judges.run_job` | [oracle_b01.py:434](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:434) | function |
| `decide` | [oracle_b01.py:450](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:450) | function |
| `score` | [oracle_b01.py:468](/home/phong/dev/ConceptTester/trickcatcher_linefacts/oracle_b01.py:468) | function |

## precond_concepts.py

| Symbol | Source location | Kind |
|---|---|---|
| `main` | [precond_concepts.py:49](/home/phong/dev/ConceptTester/trickcatcher_linefacts/precond_concepts.py:49) | function |

## precond_prompts.py

| Symbol | Source location | Kind |
|---|---|---|
| `messages` | [precond_prompts.py:10](/home/phong/dev/ConceptTester/trickcatcher_linefacts/precond_prompts.py:10) | function |

## preconditions.py

| Symbol | Source location | Kind |
|---|---|---|
| `sha` | [preconditions.py:28](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:28) | function |
| `specification` | [preconditions.py:32](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:32) | function |
| `json_list` | [preconditions.py:41](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:41) | function |
| `norm` | [preconditions.py:49](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:49) | function |
| `predicates` | [preconditions.py:53](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:53) | function |
| `predicate` | [preconditions.py:74](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:74) | function |
| `doc_inputs` | [preconditions.py:119](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:119) | function |
| `isolated` | [preconditions.py:142](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:142) | function |
| `mine` | [preconditions.py:149](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:149) | function |
| `mine.query` | [preconditions.py:174](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:174) | function |
| `mine.confirm` | [preconditions.py:181](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:181) | function |
| `load_predicate` | [preconditions.py:231](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:231) | function |
| `worker` | [preconditions.py:239](/home/phong/dev/ConceptTester/trickcatcher_linefacts/preconditions.py:239) | function |

## prompts.py

| Symbol | Source location | Kind |
|---|---|---|
| `section` | [prompts.py:42](/home/phong/dev/ConceptTester/trickcatcher_linefacts/prompts.py:42) | function |
| `build` | [prompts.py:70](/home/phong/dev/ConceptTester/trickcatcher_linefacts/prompts.py:70) | function |

## property_oracle.py

| Symbol | Source location | Kind |
|---|---|---|
| `worker` | [property_oracle.py:19](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:19) | function |
| `worker.TO` | [property_oracle.py:22](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:22) | class |
| `worker.alarm` | [property_oracle.py:25](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:25) | function |
| `worker.timed` | [property_oracle.py:31](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:31) | function |
| `worker.load` | [property_oracle.py:45](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:45) | function |
| `worker.holds` | [property_oracle.py:63](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:63) | function |
| `main` | [property_oracle.py:85](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:85) | function |
| `main.one` | [property_oracle.py:92](/home/phong/dev/ConceptTester/trickcatcher_linefacts/property_oracle.py:92) | function |

## rbc_ablation.py

| Symbol | Source location | Kind |
|---|---|---|
| `final` | [rbc_ablation.py:25](/home/phong/dev/ConceptTester/trickcatcher_linefacts/rbc_ablation.py:25) | function |
| `one` | [rbc_ablation.py:30](/home/phong/dev/ConceptTester/trickcatcher_linefacts/rbc_ablation.py:30) | function |
| `main` | [rbc_ablation.py:62](/home/phong/dev/ConceptTester/trickcatcher_linefacts/rbc_ablation.py:62) | function |

## run_gen.py

| Symbol | Source location | Kind |
|---|---|---|
| `bundle_all` | [run_gen.py:26](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:26) | function |
| `_digest` | [run_gen.py:42](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:42) | function |
| `run` | [run_gen.py:46](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:46) | function |
| `run.work` | [run_gen.py:99](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:99) | function |
| `run.work.query` | [run_gen.py:105](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:105) | function |
| `run.bounded_work` | [run_gen.py:160](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:160) | function |
| `prepare_task` | [run_gen.py:183](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:183) | function |
| `run_mined` | [run_gen.py:215](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:215) | function |
| `run_mined.work` | [run_gen.py:245](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:245) | function |
| `main` | [run_gen.py:281](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_gen.py:281) | function |

## run_v4.py

| Symbol | Source location | Kind |
|---|---|---|
| `task_sources` | [run_v4.py:18](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:18) | function |
| `safe_path` | [run_v4.py:30](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:30) | function |
| `mined_task` | [run_v4.py:42](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:42) | function |
| `mine` | [run_v4.py:55](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:55) | function |
| `mine.work` | [run_v4.py:56](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:56) | function |
| `facts` | [run_v4.py:66](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:66) | function |
| `facts.work` | [run_v4.py:69](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:69) | function |
| `classify` | [run_v4.py:93](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:93) | function |
| `assertions` | [run_v4.py:109](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:109) | function |
| `merge` | [run_v4.py:114](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:114) | function |
| `run` | [run_v4.py:118](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:118) | function |
| `run.work` | [run_v4.py:138](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:138) | function |
| `run.work.one` | [run_v4.py:142](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:142) | function |
| `run.work.one.query` | [run_v4.py:151](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:151) | function |
| `main` | [run_v4.py:256](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v4.py:256) | function |

## run_v5.py

| Symbol | Source location | Kind |
|---|---|---|
| `digest` | [run_v5.py:18](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:18) | function |
| `sources` | [run_v5.py:22](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:22) | function |
| `writable` | [run_v5.py:29](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:29) | function |
| `manifest` | [run_v5.py:40](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:40) | function |
| `isolated` | [run_v5.py:48](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:48) | function |
| `inputs` | [run_v5.py:57](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:57) | function |
| `provenance` | [run_v5.py:77](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:77) | function |
| `build_one` | [run_v5.py:84](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:84) | function |
| `bundle_facts` | [run_v5.py:101](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:101) | function |
| `messages` | [run_v5.py:115](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:115) | function |
| `mine_gap` | [run_v5.py:125](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:125) | function |
| `mine_tasks` | [run_v5.py:158](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:158) | function |
| `mine_tasks.work` | [run_v5.py:164](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:164) | function |
| `mine_tasks.work.raw_fact` | [run_v5.py:169](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:169) | function |
| `main` | [run_v5.py:189](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:189) | function |
| `main.work` | [run_v5.py:229](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v5.py:229) | function |

## run_v6.py

| Symbol | Source location | Kind |
|---|---|---|
| `facts` | [run_v6.py:23](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v6.py:23) | function |
| `facts.one` | [run_v6.py:27](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v6.py:27) | function |
| `bundle` | [run_v6.py:44](/home/phong/dev/ConceptTester/trickcatcher_linefacts/run_v6.py:44) | function |

## spec_facts.py

| Symbol | Source location | Kind |
|---|---|---|
| `in_class` | [spec_facts.py:26](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:26) | function |
| `applies` | [spec_facts.py:50](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:50) | function |
| `transforms` | [spec_facts.py:66](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:66) | function |
| `text` | [spec_facts.py:85](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:85) | function |
| `worker` | [spec_facts.py:96](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:96) | function |
| `worker.TO` | [spec_facts.py:100](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:100) | class |
| `worker.alarm` | [spec_facts.py:103](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:103) | function |
| `worker.ok` | [spec_facts.py:111](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:111) | function |
| `base_args` | [spec_facts.py:154](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:154) | function |
| `build` | [spec_facts.py:165](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:165) | function |
| `offline` | [spec_facts.py:193](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:193) | function |
| `offline_worker` | [spec_facts.py:221](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:221) | function |
| `offline_worker.TO` | [spec_facts.py:225](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:225) | class |
| `offline_worker.alarm` | [spec_facts.py:228](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:228) | function |
| `offline_worker.load` | [spec_facts.py:233](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:233) | function |
| `offline_worker.run` | [spec_facts.py:238](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:238) | function |
| `offline_worker.same` | [spec_facts.py:249](/home/phong/dev/ConceptTester/trickcatcher_linefacts/spec_facts.py:249) | function |

## tc_full.py

| Symbol | Source location | Kind |
|---|---|---|
| `sha` | [tc_full.py:33](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:33) | function |
| `templates` | [tc_full.py:37](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:37) | function |
| `seed` | [tc_full.py:48](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:48) | function |
| `messages` | [tc_full.py:53](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:53) | function |
| `source` | [tc_full.py:59](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:59) | function |
| `read_hep` | [tc_full.py:64](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:64) | function |
| `load_tasks` | [tc_full.py:68](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:68) | function |
| `put_json` | [tc_full.py:88](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:88) | function |
| `put_lines` | [tc_full.py:92](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:92) | function |
| `generation_manifest` | [tc_full.py:104](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:104) | function |
| `generate` | [tc_full.py:111](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:111) | function |
| `generate.task_job` | [tc_full.py:127](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:127) | function |
| `isolated` | [tc_full.py:144](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:144) | function |
| `subset_scores` | [tc_full.py:155](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:155) | function |
| `row_metrics` | [tc_full.py:178](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:178) | function |
| `execute_task` | [tc_full.py:185](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:185) | function |
| `aggregate` | [tc_full.py:240](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:240) | function |
| `run` | [tc_full.py:282](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:282) | function |
| `run.one` | [tc_full.py:302](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:302) | function |
| `main` | [tc_full.py:332](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full.py:332) | function |

## tc_full_worker.py

| Symbol | Source location | Kind |
|---|---|---|
| `CallTimeout` | [tc_full_worker.py:14](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:14) | class |
| `expired` | [tc_full_worker.py:18](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:18) | function |
| `to_hashable` | [tc_full_worker.py:23](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:23) | function |
| `same` | [tc_full_worker.py:31](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:31) | function |
| `timed` | [tc_full_worker.py:35](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:35) | function |
| `load` | [tc_full_worker.py:46](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:46) | function |
| `base_filter` | [tc_full_worker.py:53](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:53) | function |
| `base_filter.check` | [tc_full_worker.py:58](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:58) | function |
| `assertion` | [tc_full_worker.py:80](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:80) | function |
| `execute` | [tc_full_worker.py:92](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:92) | function |
| `main` | [tc_full_worker.py:147](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tc_full_worker.py:147) | function |

## tracer.py

| Symbol | Source location | Kind |
|---|---|---|
| `Timeout` | [tracer.py:20](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:20) | class |
| `_alarm` | [tracer.py:24](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:24) | function |
| `alarm` | [tracer.py:32](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:32) | function |
| `dcopy` | [tracer.py:40](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:40) | function |
| `numcls` | [tracer.py:48](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:48) | function |
| `absval` | [tracer.py:66](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:66) | function |
| `_num` | [tracer.py:93](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:93) | function |
| `__v` | [tracer.py:97](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:97) | function |
| `__c` | [tracer.py:106](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:106) | function |
| `shape_preds` | [tracer.py:130](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:130) | function |
| `rel_preds` | [tracer.py:162](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:162) | function |
| `__p` | [tracer.py:186](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:186) | function |
| `output_preds` | [tracer.py:195](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:195) | function |
| `__d` | [tracer.py:201](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:201) | function |
| `__u` | [tracer.py:210](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:210) | function |
| `__named` | [tracer.py:217](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:217) | function |
| `__del` | [tracer.py:222](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:222) | function |
| `__loop` | [tracer.py:229](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:229) | function |
| `__tick` | [tracer.py:237](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:237) | function |
| `__it` | [tracer.py:241](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:241) | function |
| `Inst` | [tracer.py:257](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:257) | class |
| `Inst.__init__` | [tracer.py:258](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:258) | function |
| `Inst.site` | [tracer.py:266](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:266) | function |
| `Inst.wrap` | [tracer.py:270](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:270) | function |
| `Inst.vsite` | [tracer.py:273](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:273) | function |
| `Inst.visit_Name` | [tracer.py:279](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:279) | function |
| `Inst.visit_Call` | [tracer.py:291](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:291) | function |
| `Inst._members` | [tracer.py:299](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:299) | function |
| `Inst._probes` | [tracer.py:305](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:305) | function |
| `Inst._cond` | [tracer.py:320](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:320) | function |
| `Inst._condition` | [tracer.py:328](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:328) | function |
| `Inst.stmts` | [tracer.py:356](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:356) | function |
| `Inst.visit_If` | [tracer.py:363](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:363) | function |
| `Inst.loop_wrap` | [tracer.py:369](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:369) | function |
| `Inst.visit_While` | [tracer.py:378](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:378) | function |
| `Inst.visit_IfExp` | [tracer.py:383](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:383) | function |
| `Inst.visit_comprehension` | [tracer.py:389](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:389) | function |
| `Inst.visit_For` | [tracer.py:397](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:397) | function |
| `Inst.target_names` | [tracer.py:406](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:406) | function |
| `Inst.def_stmts` | [tracer.py:410](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:410) | function |
| `Inst.visit_Delete` | [tracer.py:419](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:419) | function |
| `Inst.visit_NamedExpr` | [tracer.py:427](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:427) | function |
| `Inst.visit_With` | [tracer.py:434](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:434) | function |
| `Inst.visit_ExceptHandler` | [tracer.py:443](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:443) | function |
| `Inst.visit_Compare` | [tracer.py:447](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:447) | function |
| `Inst.visit_Assign` | [tracer.py:469](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:469) | function |
| `Inst.visit_AnnAssign` | [tracer.py:475](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:475) | function |
| `Inst.visit_AugAssign` | [tracer.py:481](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:481) | function |
| `Inst.visit_Return` | [tracer.py:492](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:492) | function |
| `Inst._fn` | [tracer.py:497](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:497) | function |
| `Inst._fn.Locals` | [tracer.py:505](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:505) | class |
| `Inst._fn.Locals.__init__` | [tracer.py:506](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:506) | function |
| `Inst._fn.Locals.visit_Name` | [tracer.py:507](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:507) | function |
| `Inst._fn.Locals.visit_ExceptHandler` | [tracer.py:509](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:509) | function |
| `Inst._fn.Locals.visit_FunctionDef` | [tracer.py:512](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:512) | function |
| `Inst._fn.Locals.visit_ClassDef` | [tracer.py:514](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:514) | function |
| `Inst._fn.Locals.visit_Lambda` | [tracer.py:515](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:515) | function |
| `Inst._fn.Locals.visit_ListComp` | [tracer.py:516](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:516) | function |
| `Inst.visit_FunctionDef` | [tracer.py:536](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:536) | function |
| `Inst.visit_Lambda` | [tracer.py:542](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:542) | function |
| `Inst.visit_ListComp` | [tracer.py:548](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:548) | function |
| `instrument` | [tracer.py:557](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:557) | function |
| `load_module` | [tracer.py:573](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:573) | function |
| `run_base` | [tracer.py:587](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:587) | function |
| `run_base.cand` | [tracer.py:591](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:591) | function |
| `run_base.tr` | [tracer.py:601](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:601) | function |
| `call` | [tracer.py:624](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:624) | function |
| `call.tr` | [tracer.py:633](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:633) | function |
| `trace` | [tracer.py:654](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:654) | function |
| `same` | [tracer.py:668](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:668) | function |
| `fact_hit` | [tracer.py:678](/home/phong/dev/ConceptTester/trickcatcher_linefacts/tracer.py:678) | function |

## v4_evaluation.py

| Symbol | Source location | Kind |
|---|---|---|
| `_short` | [v4_evaluation.py:19](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:19) | function |
| `validity` | [v4_evaluation.py:23](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:23) | function |
| `expected_value` | [v4_evaluation.py:33](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:33) | function |
| `false_alarm` | [v4_evaluation.py:45](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:45) | function |
| `false_alarm.close` | [v4_evaluation.py:68](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:68) | function |
| `guard_alarm` | [v4_evaluation.py:76](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:76) | function |
| `guard_alarm.alarm` | [v4_evaluation.py:82](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:82) | function |
| `guard_alarm.handler` | [v4_evaluation.py:88](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:88) | function |
| `worker` | [v4_evaluation.py:94](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:94) | function |
| `worker.run_assert` | [v4_evaluation.py:108](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:108) | function |
| `worker.run_assert.wrapped` | [v4_evaluation.py:110](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:110) | function |
| `worker.observe` | [v4_evaluation.py:122](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:122) | function |
| `evaluate` | [v4_evaluation.py:171](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:171) | function |
| `detects` | [v4_evaluation.py:199](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:199) | function |
| `comparison` | [v4_evaluation.py:203](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:203) | function |
| `report` | [v4_evaluation.py:216](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_evaluation.py:216) | function |

## v4_facts.py

| Symbol | Source location | Kind |
|---|---|---|
| `build` | [v4_facts.py:13](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_facts.py:13) | function |
| `build.first_hit` | [v4_facts.py:52](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_facts.py:52) | function |
| `build.dedupe` | [v4_facts.py:151](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_facts.py:151) | function |

## v4_offline.py

| Symbol | Source location | Kind |
|---|---|---|
| `worker` | [v4_offline.py:18](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_offline.py:18) | function |
| `worker.candidate` | [v4_offline.py:27](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_offline.py:27) | function |
| `evaluate` | [v4_offline.py:50](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_offline.py:50) | function |
| `evaluate.work` | [v4_offline.py:69](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_offline.py:69) | function |
| `evaluate.fuzz_stat` | [v4_offline.py:96](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_offline.py:96) | function |
| `main` | [v4_offline.py:142](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_offline.py:142) | function |

## v4_prompts.py

| Symbol | Source location | Kind |
|---|---|---|
| `domain_messages` | [v4_prompts.py:13](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_prompts.py:13) | function |
| `hybrid_messages` | [v4_prompts.py:19](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_prompts.py:19) | function |
| `seed` | [v4_prompts.py:30](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_prompts.py:30) | function |

## v4_runtime.py

| Symbol | Source location | Kind |
|---|---|---|
| `interpreter` | [v4_runtime.py:14](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_runtime.py:14) | function |
| `require_versions` | [v4_runtime.py:21](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_runtime.py:21) | function |
| `immutable` | [v4_runtime.py:28](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_runtime.py:28) | function |
| `isolated` | [v4_runtime.py:37](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_runtime.py:37) | function |
| `source_hashes` | [v4_runtime.py:49](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_runtime.py:49) | function |

## v4_strategies.py

| Symbol | Source location | Kind |
|---|---|---|
| `checked` | [v4_strategies.py:17](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_strategies.py:17) | function |
| `fallback_source` | [v4_strategies.py:60](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_strategies.py:60) | function |
| `draws` | [v4_strategies.py:78](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_strategies.py:78) | function |
| `mine` | [v4_strategies.py:83](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_strategies.py:83) | function |

## v4_tools.py

| Symbol | Source location | Kind |
|---|---|---|
| `enumerate_mutants` | [v4_tools.py:10](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:10) | function |
| `Coverage` | [v4_tools.py:73](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:73) | class |
| `Coverage.__init__` | [v4_tools.py:74](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:74) | function |
| `Coverage.measure` | [v4_tools.py:93](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:93) | function |
| `Coverage.trace` | [v4_tools.py:106](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:106) | function |
| `Coverage.branch_facts` | [v4_tools.py:112](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:112) | function |
| `Coverage.branch_facts.label` | [v4_tools.py:122](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_tools.py:122) | function |

## v4_worker.py

| Symbol | Source location | Kind |
|---|---|---|
| `draw` | [v4_worker.py:17](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:17) | function |
| `draw.Finished` | [v4_worker.py:39](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:39) | class |
| `draw.collect` | [v4_worker.py:45](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:45) | function |
| `capture` | [v4_worker.py:92](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:92) | function |
| `capture.wrapped` | [v4_worker.py:96](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:96) | function |
| `classify` | [v4_worker.py:122](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:122) | function |
| `main` | [v4_worker.py:170](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v4_worker.py:170) | function |

## v5_offline.py

| Symbol | Source location | Kind |
|---|---|---|
| `evaluate` | [v5_offline.py:15](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_offline.py:15) | function |
| `evaluate.work` | [v5_offline.py:34](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_offline.py:34) | function |
| `main` | [v5_offline.py:103](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_offline.py:103) | function |

## v5_worker.py

| Symbol | Source location | Kind |
|---|---|---|
| `build` | [v5_worker.py:16](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_worker.py:16) | function |
| `build.evidence` | [v5_worker.py:24](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_worker.py:24) | function |
| `targeted` | [v5_worker.py:59](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_worker.py:59) | function |
| `main` | [v5_worker.py:86](/home/phong/dev/ConceptTester/trickcatcher_linefacts/v5_worker.py:86) | function |

## validity_filters.py

| Symbol | Source location | Kind |
|---|---|---|
| `worker` | [validity_filters.py:45](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:45) | function |
| `worker.TO` | [validity_filters.py:48](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:48) | class |
| `worker.alarm` | [validity_filters.py:51](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:51) | function |
| `worker.timed` | [validity_filters.py:57](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:57) | function |
| `worker.load` | [validity_filters.py:71](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:71) | function |
| `worker.passes_base` | [validity_filters.py:77](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:77) | function |
| `signals` | [validity_filters.py:102](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:102) | function |
| `signals.one` | [validity_filters.py:108](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:108) | function |
| `llm` | [validity_filters.py:123](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:123) | function |
| `llm.one` | [validity_filters.py:135](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:135) | function |
| `f3_verdicts` | [validity_filters.py:145](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:145) | function |
| `score` | [validity_filters.py:165](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:165) | function |
| `score.invalid` | [validity_filters.py:173](/home/phong/dev/ConceptTester/trickcatcher_linefacts/validity_filters.py:173) | function |

## kaggle/qwen_gen.py

| Symbol | Source location | Kind |
|---|---|---|
| `key` | [kaggle/qwen_gen.py:15](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:15) | function |
| `seed` | [kaggle/qwen_gen.py:19](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:19) | function |
| `fingerprint` | [kaggle/qwen_gen.py:23](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:23) | function |
| `version` | [kaggle/qwen_gen.py:27](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:27) | function |
| `pip` | [kaggle/qwen_gen.py:34](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:34) | function |
| `atomic_json` | [kaggle/qwen_gen.py:39](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:39) | function |
| `save_rows` | [kaggle/qwen_gen.py:45](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:45) | function |
| `result` | [kaggle/qwen_gen.py:54](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:54) | function |
| `prepare` | [kaggle/qwen_gen.py:63](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:63) | function |
| `generate_vllm` | [kaggle/qwen_gen.py:79](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:79) | function |
| `generate_transformers` | [kaggle/qwen_gen.py:108](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:108) | function |
| `generate_transformers.RowSampler` | [kaggle/qwen_gen.py:112](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:112) | class |
| `generate_transformers.RowSampler.__init__` | [kaggle/qwen_gen.py:113](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:113) | function |
| `generate_transformers.RowSampler.__call__` | [kaggle/qwen_gen.py:117](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:117) | function |
| `generate_transformers.batch` | [kaggle/qwen_gen.py:131](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:131) | function |
| `main` | [kaggle/qwen_gen.py:177](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:177) | function |
| `main.put` | [kaggle/qwen_gen.py:207](/home/phong/dev/ConceptTester/trickcatcher_linefacts/kaggle/qwen_gen.py:207) | function |
