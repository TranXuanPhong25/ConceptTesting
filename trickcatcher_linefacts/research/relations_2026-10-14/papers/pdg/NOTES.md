# The Program Dependence Graph and Its Use in Optimization

Ferrante, Ottenstein, Warren; TOPLAS 1987. [Full paper](https://www.cs.utexas.edu/~pingali/CS395T/2009fa/papers/ferrante87.pdf), bản lưu ở university site. Kiểm data/control dependence definitions; không có artifact hiện đại được kiểm.

**Paper facts:** PDG biểu diễn data và control dependences; control dependence được định nghĩa từ control-flow graph và postdominance. Đây là foundation về program representation/optimization. [Nguồn: dependence definitions](https://www.cs.utexas.edu/~pingali/CS395T/2009fa/papers/ferrante87.pdf).

**Áp dụng đề xuất:** Đặt tên evidence đúng: v12 syntactically enclosing guards là approximation; observed def-use là trace-specific evidence. Cần xử lý early return/break và object mutation nếu muốn nâng claim về complete dependency graph.

**Giới hạn:** PDG không chứa intended specification. Có path data/control không tự sinh behavioral oracle. Thêm graph representation quen thuộc chưa tạo novelty; LineFacts phải chứng minh obligation selection và semantic counterexamples dựa trên concepts.
