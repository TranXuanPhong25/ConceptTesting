# Full HumanEval: Plain, EP+BVA và Decision Table — timeout8s

Raw detection:Plain68,EP+BVA89,DT74 trên1454eligible base-pass PUTs. EP+BVA tăng chủ yếu ở resource;wrong-value chỉ54→55. DT có57wrong-valuePUTs. Matched-valid-input-budget chưa cho thấy khác biệt rõ (Plain/EP+BVA p≈0,073;Plain/DT p≈0,556). Không suy rằng formal EP/BVA/DT đã được thực hiện đúng chỉ từ detection:EP+BVA chỉ27/157catalogue qua schema,DT87/157applicable.

| Metric | Plain | EP+BVA | DT |
|---|---:|---:|---:|
| Novel valid inputs | 2906 | 2402 | 2608 |
| Confirmed detected PUTs /1454eligible PUTs | 68 | 89 | 74 |
| Task có detection /157eligible tasks | 25 | 30 | 25 |
| Wrong-value PUTs | 54 | 55 | 57 |
| Exception-only PUTs | 0 | 4 | 5 |
| Resource-only PUTs | 14 | 30 | 12 |
| Known total tokens | 400482 | 604042 | 593975 |

Mỗi PUT lấy kind mạnh nhất trong các confirming inputs:wrong-value→exception→resource;không cộng trùng.PUT detected khác số input gây lỗi. EP+BVA rawgain+21 gồm net+1wrong-value,+4exception,+16resource;đây là chênh lệch count theo strongest kind,không phải paired attribution từngPUT.

Config:164task records/157eligible tasks,1454base-pass PUTs,7task skips(2generation_shortfall,5no_base_pass). Shared Plain baseline,visiblePUTset jointlytrim cho3arms,20inputs/task/arm,1generation call/task/arm,completion4096tokens/call,context8192tokens,temp0.7,inputseed314159+task,referenceseed271828+task,timeout8s/input,correctedHumanEval+reference2runs,confirm_first_failures scorer. Input freeze toàn bộ trước nativeevaluation. Scope DT là fulleligiblecohort,không đồng nghĩa157task đềuDT-applicable.

471receivedgenerationresponses/472physicalattempts/1unknown từ lần userđổitimeout. Tổngknown generationtokens1,598,499 (prompt985,123+completion613,376). Unknown usage không điền0. Keepalive tính riêng:29attempts,20received/9unknown,280known tokens.

Catalogue:EP+BVA27applicable+130invalid/157;DT87applicable+65invalid+3not_applicable+2unresolved/157. Invalid catalogue không tự loại validinputs;structural applicability không chứng minh semantic correctness. Specgrounding,partitionexhaustiveness,base-callcoverage và phần mechanical thiếu metadata vẫnpending.

Matched-valid-input-budget dùng seededrandomsubsets theo task/pair,giữ task có0matchedinputs;không lấy prefix.
- plain vs ep_bva:macroPUTfraction0.042481 vs0.058457; p=0.072593;taskwins8vs15;zero-matchedtasks10/157.
- plain vs decision_table:macroPUTfraction0.043047 vs0.047859; p=0.55634;taskwins7vs7;zero-matchedtasks9/157.
- ep_bva vs decision_table:macroPUTfraction0.057537 vs0.043967; p=0.091991;taskwins10vs5;zero-matchedtasks12/157.

SourceGuardPASS,immutable replaymatches;report chỉ đọc artifacts có sẵn,0newmodel/nativecalls. Source/checkpoints/results gốc giữ nguyên.
Prefect:http://127.0.0.1:4200/runs/flow-run/d3a095ba-e5d2-46a4-bbe8-44deebdb6073
Output:`final/out/console_resume_d3a095ba-e5d2-46a4-bbe8-44deebdb6073`.
