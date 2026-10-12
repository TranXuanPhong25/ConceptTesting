# Đánh giá khả năng hiểu fact

Bộ này gồm 30 fact đã được hiển thị ở K=3, chỉ lấy từ DEV sau khi đóng băng v3. Các loại fact được lấy mẫu phân tầng với seed 20261010. Không có task pilot/design, lời giải canonical, nhãn HumanEval+ hay input gợi ý trong phiếu đánh giá.

Đọc từng mục trong `items.md`: docstring là đặc tả, PUT là hàm cần kiểm thử, và fact mô tả điều bộ test hiện có chưa bao phủ. Điền `ratings.csv`:

- Q1 **I understand what this fact says**: từ 1 (hoàn toàn không hiểu) đến 5 (hiểu rõ).
- Q2 **an input that satisfies it**: viết một lời gọi Python cụ thể, ví dụ `function_name([1, 2], 0)`. Chỉ dùng giá trị literal; không viết assertion hay biểu thức như `[0] * 10`.

Hoàn thành cả hai câu trước khi dùng checker để tránh phản hồi ảnh hưởng điểm Q1. Checker xác nhận input có đạt hành vi thiếu được mô tả trong fact; checker không đánh giá output đúng/sai theo đặc tả và không xác nhận input hợp lệ trong miền bài toán.

```bash
python3 trickcatcher_linefacts/human_eval/check.py H01 'function_name([1, 2], 0)'
```

Đọc `reaches_fact`: `true` là đạt fact, `false` là chưa đạt. `put_status` cho biết hàm hoàn tất, báo lỗi hay hết ngân sách bước; lỗi/hết bước vẫn có thể đạt fact. Mọi lần thực thi PUT của checker đều nằm trong `unshare -rn python3 -I`. Giữ một bản CSV riêng cho mỗi người đánh giá; các cột task/kind/fact_index dùng để ghép dữ liệu, không sửa chúng.
