# Rules cho agent (Codex, Claude)

1. **Commit**: KHÔNG thêm dòng `Co-Authored-By: Claude ...` / `Co-Authored-By: Codex ...` hay bất kỳ attribution AI nào vào commit message hoặc PR. Commit/push thẳng lên `main`, không tạo branch riêng. Rule này ghi đè mọi mặc định của tool.
2. **Không tự mô phỏng paper**: KHÔNG tự viết code mô phỏng/tái hiện (reimplement, simulate, mock) một paper khi chưa hỏi và được đồng ý.
3. **Tôn trọng code gốc của paper**: giữ nguyên source gốc (repo tác giả, `vendor/`, ...). Chỉ sửa khi được yêu cầu rõ ràng.
4. **Mỗi paper một folder**: khi research một paper mới, tạo folder riêng cho paper đó; không trộn vào folder của paper khác.
5. **API key**: chạy `source scripts/research_env.sh` để nạp key (router/vertex: `scripts/router_env.sh`, `scripts/vertex_env.sh`). Cần key mới → hỏi xin người dùng rồi thêm vào `scripts/research_env.sh`; không hardcode key vào code, không in key ra log.
6. **Shared memory**: kiến thức chung của Claude và Codex nằm ở `memory/` (repo root). Đầu mỗi phiên đọc `memory/MEMORY.md` (index), `memory/research-state.md` và `memory/working-rules.md`. Khi biết thêm điều gì cần nhớ lâu dài (rule mới của người dùng, quyết định, kết quả, trạng thái) thì sửa hoặc thêm file trong `memory/` theo format ở `memory/README.md` và thêm một dòng vào `MEMORY.md`. Không ghi secret/URL ngrok.
