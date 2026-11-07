# Checked grounding: diagnostic trên 6 PUT đã miss

Follow-up user yêu cầu Luna đọc feedback và output input ngay: [direct3 report](boundary_luna_direct3_2026-11-06.md).
Một native no-observed-tools call sinh3input/3bugtasks23/72/157; không phải cùng
setting với run này. Follow-up còn ghi partial selection rejection của72:
`boundary_kind: edge` không hợp enum, trong khi b1sumvẫn được giữ.

Stable v5 đã restore/push ở commit `13d92ee9` trước experiment. Bản checked là
opt-in, chưa commit/push. Chạy trên cùng6PUT miss2/11/16/23/72/157của known_bug10:
**8 calls,23input hợp lệ, chạm thêm bug task16**. Đây là diagnostic chọn theo
kết quả và thiết kế sau khi đã nhìn lỗi; không phải detection rate hay efficacy.

Output: `final/out/boundary_checked6_20261106`.
Plan/review/amendments trong `final/src/modular/PREREG.md`; offline mechanism
audit trước run: [offline report](boundary_grounding_offline_2026-11-06.md).

## Những gì thay đổi

- Exact v5 selection/context instructions giữ nguyên, với checked-mode task data
  thêm bounded AST quantity/scope/polarity receipts và binding rules.
- Contract scalar types có thể mở float neighborhood từ observed-int evidence.
- Raw input code-point characteristic và constructor, tách khỏi transformed ord
  và encoded byte length; không auto rewrite semantic binding của model.
- Prune concrete domain-excluded targets trước context quotas nếu boundary đã
  qua selection validation. Thêm checked properties/context-goal coverage cho
  non-ASCII và prefix_exceeds_limit; unsupported source patterns giữ unknown.
- Model vẫn quyết định boundary và context. Không tự inject witness hoặc query
  reference để sửa hypothesis trước input freeze.

Phần này đồng thời đổi candidate space và guidance, không isolate riêng hiệu quả
ranking hay semantic receipts. Không dùng paper implementation/reproduction.

## Kết quả từng task

| Task | Semantic response mới | Input cuối / kết quả |
|---|---|---|
| 2 | Vẫn `no_applicable_boundary` |0input; receipts chưa cung cấp integer-crossing evidence |
| 11 | Vẫn `no_applicable_boundary` |0input; joint empty edge chưa được chọn |
| 16 | Chọn code_point256, không còn length256; ghi nhận lower transform |20input,15input fail ổn định; phát hiện PUT4 |
| 23 | Phân biệt spec character length với PUT encoded byte length, nhưng vẫn nói không có threshold | Raw abstention thiếu field boundaries nên invalid_selection;0input |
| 72 | Reason/infect phân biệt prefix sum với total sum |5context nhắm bug không đạt property, bị loại;3above-side input ordinary giữ lại, không bug |
| 157 | `alignment: match`, dùng float_adjacent và domain_lower, không còn false mismatch | Khai báo at=0dù domain a>0; validator reject trước compiler,0input |

### Task16: capability + selection đã đưa tới input làm lộ bug

Selected characteristic `string:code_point`, constant256, step1, sides below/at/
above. Raw targets255/256/257được code dựng thành `'ÿ'`, `'Ā'`, `'ā'` cùng các
seed context nhỏ khác. Không bị generation truncation như v5.

Ví dụ đơn giản nhất: `('Ā',)` có reference1, PUT0ở cả2native repeats. Code-point
constructor chỉ đảm bảo raw input character code256. `.lower()` đổi nó thành
U+0101trước comparison của PUT; không claim đã đạt transformed ord exactly256.
Việc phân biệt raw/transformed measures vẫn cần giữ trong evidence.

Có15/20input fail. Một số below-side inputs như `'ÿ\uffff'` cũng fail vì context
thêm ký tự ngoài array256. Vì vậy không diễn giải toàn bộ15failures như bằng chứng
mỗi target side tự nó phân biệt đúng behavior. Simple one-character witness đã
đủ xác nhận bug, còn context diversity thay đổi cùng pool.

### Task72: hiểu condition hơn nhưng không dựng được input thỏa nó

Selection reason:

> Spec requires full sum <= w; code rejects on prefix sum > w

Infect note nói total<=wnhưng prefix>w. Field `alignment` vẫn ghi `operator`, nên
không claim worksheet hoàn toàn đúng; điều cải thiện quan sát được nằm ở reason/
infect và explicit context requirement.

Model đưa5context cho below/at cùng palindrome + prefix_exceeds_limit:

| Side | Model seed `(q,w)` | Sau palindrome sum construction | Vì sao reject |
|---|---|---|---|
| below | `([10,-5,10],15)` | `([10,-6,10],15)` | prefix10,4không >15 |
| below | `([20,-15,20],25)` | `([20,-16,20],25)` | prefix20,4không >25 |
| at | `([10,-5,10],15)` | giữ nguyên | prefix10,5không >15 |
| at | `([20,-15,20],25)` | giữ nguyên | prefix20,5không >25 |
| at | `([30,-25,30],35)` | giữ nguyên | prefix30,5không >35 |

Property được kiểm sau construction, không tin lời khai. Goal coverage ghi
`unmet`; không tính các record trên là đã cover bug-sensitive condition.
Chỉ3above-side inputs được giữ: `([5,5,5],14)`, `([6,6,6],17)`,
`([7,7,7],20)`. Cả3PUT/reference đều Falsevà pass ở2repeats.

Đây là bằng chứng cụ thể của bước mất mới: model đã phát biểu được condition,
nhưng literal seeds không thực hiện nó. Constructor hiện chỉ bảo đảm sum target
và palindrome, không joint-solve prefix constraint. Thêm checker phát hiện lỗi
đúng; nó chưa cung cấp solver cho condition đó.

### Task157: polarity label sửa được, side/domain interface còn lỗi

Response không còn gọi reject<=0với domain>0là mismatch. Nó chọn domain_lower,
`alignment: match`, `float_adjacent`, và giải thích at0invalid/abovevalid.
Nhưng target_sides vẫn `[at,above]`; với strict>0, atkhông được phép. Validator
đúng khi trả `outside_lower_domain`, không gọi context.

Early target-domain pruning ở compiler đã pass offline test, nhưng run này không
tới compiler vì schema/domain-role validation dừng trước đó. Không tự sửa side
list sau khi xem response. Hypotenuse/arithmetic relation vẫn chưa được chọn và
không được biểu diễn bởi module này; cải thiện polarity không đồng nghĩa chọn
đúng bug boundary.

## Accounting và verification

| Trên cùng6PUT | v5 historical | Checked |
|---|---:|---:|
| Task calls |9|8|
| Valid novel inputs |13|23|
| Observed bug tasks |0|1(task16)|
| Known total task tokens |28.727|26.573|

Historical contrast không matched treatment/control: candidate pool và context
guidance thay đổi, chưa có same-pool random hoặc evidence-only ablation. Không
cộng1vào kết quả4tasks của v5để tuyên bố một run mới đạt5/10; run này chỉ có6PUT.

-8responses/0unknown;23.176prompt +3.397completion tokens. No periodic keepalive
  completion, no semantic retry, no expansion. Model exactqwen3.5-27b-awq/8192.
-278modular tests pass trước launch, gồm44grounding cases; independent reviewer
  đã kiểm unsupported scopes/mutations/shadowing/offsets và clear trước inference.
-79source/data files và723prior-output files giữ hash trước launch.6input-freeze
  hashes/barrier verified. Các failure của16ổn định trong2native repeat slots.
- Full read-only checked-pipeline replay khớp23valid/1detected. No source drift.
- Offline default-preservation check xác nhận menus/messages của10v5tasks vẫn
  byte-identical khi modeoff. Default source identity đổi nên cần fresh output.

Xem `prelaunch_snapshot.json`, `prelaunch_readiness.json`, `modular_manifest.json`,
`generation_frozen.json`, `postrun_audit.json`; source copies được giữ trong
`source_evidence/`. Không có private endpoint/keys trong artifacts.

## Kết luận cho bước tiếp

Giữ stablev5đã commit. Trial cho thấy source receipts có thể giúp model nêu đúng
quantity/scope/polarity hơn ở16/23/72/157, nhưng ba lớp vẫn phải đánh giá riêng:
semantic recognition, schema/domain binding, và executable context realization.
Task72cho thấy rõ phải joint-construct/solve context obligations thay vì chỉ nhắc
model dùng giá trị âm;23/157còn interface/candidate limitations. Đây là cơ sở
chọn việc sửa tiếp, chưa phải kết luận promote checkedmode hay claim efficacy.
