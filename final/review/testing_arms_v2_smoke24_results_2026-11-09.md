# V2 smoke24 — kết quả

EP+BVA v1/v2 cùng1/6PUT;DT v1/v2 raw0vs1/6PUT. Các detection đềuwrong-value ởHumanEval99/PUT0. **DT rawgain không chứng minh hypothesis/refinement chọn input tốt hơn:**DTv1task99 có0validinputs doinvalidresponse;matched-valid-budget0vs0. EP matched1vs1,p=1;DTmatched0vs0,p=1. Không có kết luận efficacy từ6PUT này.

| Arm | Novel valid inputs | Detected PUTs /6 | Total known tokens | Applicable catalogue /6 |
|---|---:|---:|---:|---:|
| ep_bva | 112 | 1/6 | 18126 | 2/6 |
| ep_bva_v2 | 62 | 1/6 | 20700 | 1/6 |
| decision_table | 80 | 0/6 | 20156 | 3/6 |
| decision_table_v2 | 72 | 1/6 | 22903 | 4/6 |

Catalogue-invalid counts:EPv1 4/6,EPv2 5/6,DTv1 3/6,DTv2 2/6. Whole-responseinvalid:EPv2 2,DTv1 2,DTv2 2. Truncation:EPv1 0,EPv2 0,DTv1 1,DTv2 1;không quy mọiinvalidresponse thànhtruncation. Schema-valid không phải semantic-valid;hypothesis annotation vẫn self-reported/pendingsemanticvalidation. EPv2 lưu10/10classhypotheses trong catalogue decodeđược;DTv2 lưu27/27rulehypotheses. Không coi đó làconfirmedfaults.

Config:6tasks0/5/18/81/99/120,1PUT/task;4arms cùngvisibility/sharedpacket,budget20inputs/task/arm,cap4096tokens/call,context8192,temp.7,seeds314159/271828+task,timeout8s,inputfreeze/reference2runs/confirm-first-failures. 24receivedresponses/25attempts/1historicalunknown dointentionalreorder;4responsesđãnhậngiữlạivà20responsesmới trongcontinuation. Known generationtokens81885(prompt31796+completion50089);unknownusage không điền0. Một keepaliveunknown báo riêng,chưa cóknownusage cho nó.

V2 chứa instruction+soft example package nên comparison không isolate riêngFaultHypotheses hoặc examples. Baseline-rerun đã bắt đầu nativeevaluation trước V2 generation theo gate hashfreeze;native lock vẫnserialize evaluation. Cả hai run Completed/sourceguard/immutable replayPASS;không tự nối thêm run. Report chỉ đọc artifacts,0newmodel/nativecalls.

Prefect:http://127.0.0.1:4200/runs/flow-run/4fb900d7-321a-476e-8c1e-0ec8870ce909
