# Vì sao Direct77 thành Plain68 — audit saved artifacts

Hai baseline không phải cùng request/inputs chỉ đổi tên. Chúng thuộc cùng baseline family nhưng có guidance suffix khác,completion cap2048vs4096 và được generate lại. Direct77 vàPlain68 có64PUTs chung;Direct-only13,Plain-only4 nên net−9. Không có bằng chứng việc tăng cap tự nó gây−9.

## Accounting cụ thể

- 3/13Direct-only PUTs thuộc2task bị Plain mất toàn response:task45 có biểu thức1/3 ngoàiJSON literal,decoderreject→0inputs, mất1exceptionPUT;task61 response bịtruncation(length4096) ở string dấu ngoặc dài, mất2wrong-valuePUTs.
- 10/13Direct-only PUTs còn lại có Plain inputs decode được,nhưng thiếu các Direct input đã phơi lỗi. Tất cả13Direct-onlyPUT đều không có Direct witness trong Plain novel-valid pool;không thấy scorer đánh khác cùng witness hợp lệ.
- Ví dụtask72:Direct có([-1,-2,-1],-3) và([-1,-2,-1],-4),phơi3PUTs màPlain20validinputs không phơi. Task2 thiếu0.9999999;task126thiếu[1,0];task99thiếu strings ±0.4999999999999999. Resourceinputs như1000 hoặc cặp số nguyên tố lớn cũng khác.
- Plain đồng thời có4PUTs mới:task140(1wrong-value),task27(1wrong-value),task24(2resource). Vì vậy không phải chỉ mất9PUTscũ.

## Confounds đã kiểm

- 153/157eligible tasks có cùng shared packet/PUTvisibility;4task khácvisibility là39,94,124,129. Không task nào thuộc nhóm13Direct-only,dođókhôngquy9netlosstới4contextchanges này.
- Seed vàtemperature giống ở157task,nhưng fullrequestkhác:Direct guidance rỗng;Plain thêm `No additional analysis packet. Choose useful new tests from the information above.`
- Cùng inputbudget20 vànativetimeout8,nhưngcap2048vs4096;capcao hơn không tănginputbudget,sốvalidinputs gầnnhau2913vs2906.
- Đang so generation mới trênconfigkhác,không phải pairedrerun chỉ thay mộtfactor. Không thể phân bổcausal−9 cho câuextra/cap/sampling khi chưa cócontrolledcomparison.

| Metric | Direct | Plain |
|---|---:|---:|
| Detected PUTs /1454 | 77 | 68 |
| Wrong-value PUTs | 61 | 54 |
| Exception-only PUTs | 1 | 0 |
| Resource-only PUTs | 15 | 14 |
| Novel valid inputs | 2913 | 2906 |

So sánh Plain/EP+BVA/DT trong cùng run vẫn chung sharedpacket/budget/scorer;nhưngkhôngđượccoibaseline77và68 là mộtbaselineđượctáilậpgiốnghệt. Audit chỉ đọc savedresponses/inputs/results,0newmodel/nativecalls;không sửa source/output/checkpoints hoặc pendingv2run.
