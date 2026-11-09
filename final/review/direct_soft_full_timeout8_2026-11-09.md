# Direct vs Soft BVA full HumanEval — timeout8s

Soft BVA phát hiện85/1454eligible PUTs,Direct77/1454 (+8PUT raw). Riêng wrong-value,Soft58 so vớiDirect61; lợi thế tổng chủ yếu ở resource/exception. Đây là hai arm với input yield khác nhau; không suy rằng BVA tốt hơn về correctness chỉ từ tổngraw. Cũng không phải thí nghiệm chỉ thay timeout3→8 trên cùng inputs đã hoàn tất trước đó.

| Metric | Direct | Soft BVA |
|---|---:|---:|
| Novel valid inputs | 2913 | 2842 |
| Confirmed detected PUTs / eligible PUTs | 77/1454 | 85/1454 |
| Task có detection / eligible tasks | 28/157 | 33/157 |
| Wrong-value PUTs | 61 | 58 |
| Exception-only PUTs | 1 | 5 |
| Resource-only PUTs | 15 | 22 |

Kind của mỗiPUT là mạnh nhất trong confirming inputs:wrong-value→exception→resource; không cộng mộtPUT nhiều lần. Raw shared64PUTs,Direct-only13,Soft-only21. Taskwins theo sốPUTdetected:Direct5,Soft11,tie141 trên157eligible tasks.

Matched-valid-input-budget dùng seeded random subsets theo task/pair: tổng2766inputs mỗiarm; macro detected PUT fraction 0.048071 vs 0.057219, paired permutation p=0.18618;taskwins4vs12,zero-matched-budget tasks3/157. Không lấy prefix.

Config:164taskrecords,157eligible/1454base-passPUTs;7taskskip(2generation_shortfall,5no_base_pass). 20inputs/task/arm,1generationcall/task/arm,completioncap2048tokens/call,context8192,temperature0.7,inputseed314159+task,referenceseed271828+task,nativetimeout8s/input;correctedHumanEval+reference2runs vàconfirm_first_failures scorer.

314receivedgenerationresponses/315physicalattempts;1unknown từlầnuserđổitimeoutđượcgiữhistory. Known tokens815,831(prompt600,585+completion215,246);unknownusagekhôngđượcđiền0. Keepalive10receivedcalls/140tokens báo riêng. Continuation tái dùng35receivedresponses,279responses mới;không regeneration responseđãnhận.

Source/hash verification vàimmutable replayPASS. Report này chỉ đọc artifacts đã có,0model/nativecalls. Source/checkpoint/result gốc không sửa.

Prefect:http://127.0.0.1:4200/runs/flow-run/43c7061b-38c6-4bbb-8c5a-6da366d337f9
Output:`final/out/console_resume_43c7061b-38c6-4bbb-8c5a-6da366d337f9`.
