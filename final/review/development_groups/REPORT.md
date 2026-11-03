# Bốn nhóm development theo test_slides

Phân loại toàn bộ164task và source PUT, không chạy model/reference/plus tests.
Mỗi task có một nhóm chính và nhiều nhãn phụ. Đây là nhóm ưu tiên phát triển, không phải nhãn loại bug.

| Nhóm | Task chính | Task có PUT phù hợp | Smoke | Development | Check |
|---|---:|---:|---|---|---|
| boundary | 47 | 44 | 0, 18, 81, 99, 120, 5 | 0, 18, 81, 99, 120, 5, 47, 71, 115, 124, 140, 10 | 2, 77, 138, 159 |
| equivalence | 47 | 46 | 11, 22, 26, 51, 85, 137 | 11, 22, 26, 51, 85, 137, 54, 78, 98, 104, 128, 151 | 7, 27, 116, 158 |
| statement | 31 | 15 | 31, 141, 43, 57, 59, 64 | 31, 141, 43, 57, 59, 64, 75, 94, 110, 143, 154 | 40, 82, 12, 24 |
| def_use | 39 | 35 | 3, 9, 25, 46, 114, 4 | 3, 9, 25, 46, 114, 4, 6, 8, 55, 61, 111, 123 | 13, 106, 139, 1 |

Smoke≤6PUT/group, development≤12, check≤4; default dùng một PUT/task.
Development bao gồm smoke; check tách theo task khỏi development của cả4nhóm.
PUT chọn từ source/base evidence, không chọn bằng kết quả phát hiện lỗi. Nhóm ít candidate có thể thiếu quota.

## Toàn bộ164task

| Task | Entry point | Nhóm chính | Nhãn phụ | Obligation cần phát triển |
|---|---|---|---|---|
| 0 | has_close_elements | boundary | equivalence,statement | Khoảng cách bằng threshold và hai phía; threshold=0 chỉ khi contract cho phép. |
| 1 | separate_paren_groups | def_use | equivalence,statement | Balance tăng/giảm, start được cập nhật rồi dùng để cắt group; nhiều group liên tiếp. |
| 2 | truncate_number | boundary | equivalence | Số nguyên dương và float sát số nguyên; không giả định số âm hợp lệ. |
| 3 | below_zero | def_use | boundary,statement | Balance khởi tạo→cộng nhiều lần→p-use; từng âm rồi phục hồi vẫn phải được phát hiện. |
| 4 | mean_absolute_deviation | def_use | equivalence | Mean được tính trước rồi dùng cho mọi độ lệch; data âm/dương, đồng nhất/khác nhau. |
| 5 | intersperse | boundary | equivalence,statement | Độ dài list 0/1/2; delimiter xuất hiện giữa phần tử, không thêm ở đầu/cuối. |
| 6 | parse_nested_parens | def_use | equivalence,statement | Depth hiện tại và maximum qua tăng/giảm/reset giữa các group. |
| 7 | filter_by_substring | equivalence | boundary | Substring có/không xuất hiện, empty substring, khớp cả từ hay một phần; giữ thứ tự. |
| 8 | sum_product | def_use | boundary,equivalence | Hai accumulator sum/product có giá trị khởi tạo khác nhau; empty và phần tử zero. |
| 9 | rolling_max | def_use | boundary,statement | Current maximum cũ/mới phải tới đúng lần append; max âm, tăng, giảm, bằng nhau. |
| 10 | make_palindrome | boundary | equivalence,statement | Empty, một ký tự, đã palindrome, suffix palindrome ngắn/dài; chiều dài nối tối thiểu. |
| 11 | string_xor | equivalence | boundary | Bốn tổ hợp bit 00/01/10/11 và giữ leading zeros; chỉ strings đúng domain. |
| 12 | longest | statement | equivalence,boundary | Return None ở empty và nhánh cập nhật longest; tie phải giữ phần tử đầu tiên. |
| 13 | greatest_common_divisor | def_use | boundary,equivalence | Euclid cập nhật đồng thời a,b; giá trị trước/sau phép modulo tới đúng iteration. |
| 14 | all_prefixes | boundary | equivalence | Empty, length1, prefix đầu và prefix toàn chuỗi; inclusive endpoint. |
| 15 | string_sequence | boundary | statement | Dãy phải chứa cả 0 và n; n=0 và n=1 nếu domain cho phép. |
| 16 | count_distinct_characters | equivalence | boundary | Lower/upper cùng ký tự, lặp, ký tự khác; Unicode chỉ khi contract cho phép. |
| 17 | parse_music | equivalence | statement | Ba token o/o\|/.\|, khoảng trắng hợp lệ và chuỗi nhiều token. |
| 18 | how_many_times | boundary | equivalence,def_use | Vị trí đầu/cuối và match chồng lấp; tránh bỏ occurrence cuối hoặc skip quá xa. |
| 19 | sort_numbers | equivalence | boundary | Mười numeral hợp lệ, trùng lặp và thứ tự khác; không đưa token ngoài domain. |
| 20 | find_closest_elements | boundary | def_use,equivalence | List tối thiểu2; tie khoảng cách và duplicate zero-gap theo contract. |
| 21 | rescale_to_unit | boundary | def_use,equivalence | Min/max phải thành0/1; tránh chia zero với miền hằng nếu contract loại. |
| 22 | filter_integers | equivalence | statement | Integer và non-integer cùng list; bool/int theo contract chứ không tự chọn semantics. |
| 23 | strlen | boundary | equivalence | Length0/1/n và ký tự nhiều byte nếu domain cho phép; không dùng byte length thay char length. |
| 24 | largest_divisor | statement | boundary,equivalence | Nhánh tìm divisor và fallback1; composite, square, prime với n hợp lệ. |
| 25 | factorize | def_use | boundary,equivalence | Remainder n và divisor được cập nhật qua nhiều lần chia; lũy thừa prime và residual prime. |
| 26 | remove_duplicates | equivalence | def_use | Xuất hiện một lần/nhiều lần, không được chỉ deduplicate; giữ thứ tự phần còn lại. |
| 27 | flip_case | equivalence | statement | Lower/upper/non-letter; flip case từng nhóm trong cùng chuỗi. |
| 28 | concatenate | equivalence | boundary | List rỗng, string rỗng xen kẽ và nhiều strings; preserve concatenation order. |
| 29 | filter_by_prefix | equivalence | boundary | Prefix match/nonmatch, exact match, prefix rỗng nếu hợp lệ. |
| 30 | get_positive | boundary | equivalence | Phân cách tại0; -1/0/1, giữ strict positive. |
| 31 | is_prime | statement | boundary,equivalence | Early return n<2, divisor found và no divisor; square cần đi vào body kiểm divisor. |
| 32 | find_zero | def_use | boundary | Các coefficient đi qua poly/root update; giữ điều kiện bậc lẻ và coefficient cao nhất khác0. |
| 33 | sort_third | def_use | equivalence,boundary | Tách subsequence index%3=0→sort→ghi lại; index khác phải giữ nguyên. |
| 34 | unique | equivalence | boundary | Trùng/không trùng, thứ tự input khác, âm/zero; output vừa unique vừa sorted. |
| 35 | max_element | def_use | boundary,equivalence | Candidate max khởi tạo→update→return; list toàn số âm và maximum ở các vị trí. |
| 36 | fizz_buzz | boundary | equivalence | Range loại n, bội11/13 sát n và số chứa nhiều digit7; không double count bội chung. |
| 37 | sort_even | def_use | equivalence,boundary | Sort riêng even-index subsequence rồi ghi lại; odd-index giữ nguyên. |
| 38 | decode_cyclic | boundary | equivalence | Nhóm3 và phần dư length0/1/2; inverse cycle đúng chiều. |
| 39 | prime_fib | def_use | statement | Fibonacci state và counter prime được update khác nhau; prime thứ1 và nhiều lần lặp. |
| 40 | triples_sum_to_zero | statement | boundary,equivalence | Nhánh tìm được triple và không tìm thấy; list<3, indices phân biệt. |
| 41 | car_race_collision | boundary | equivalence | Số xe0/1/n theo contract, quan hệ n*n; task đơn giản làm sanity control. |
| 42 | incr_list | equivalence | boundary | Mỗi phần tử cộng1, âm/zero/dương, list rỗng; không chỉ update một phần list. |
| 43 | pairs_sum_to_zero | statement | boundary,equivalence | Nhánh pair found/not found, một zero không được tự ghép chính nó. |
| 44 | change_base | boundary | def_use,equivalence | Chuyển tại0, base-1/base/base+1 theo contract; remainder và quotient. |
| 45 | triangle_area | boundary | equivalence | Kích thước nguyên/lẻ tạo area .5; zero chỉ khi domain cho phép. |
| 46 | fib4 | def_use | boundary,statement | Bốn state/base cases0..3 và recurrence update từ n=4; snapshot trước khi cập nhật. |
| 47 | median | boundary | equivalence,statement | Length1/2, odd/even; median hai giá trị giữa không làm integer truncation. |
| 48 | is_palindrome | statement | equivalence,boundary | True/false return và mismatch ở đầu/giữa/cuối; empty là palindrome. |
| 49 | modp | def_use | boundary | Accumulator modular exponent qua nhiều bước; n=0, modulus nhỏ hợp lệ. |
| 50 | decode_shift | equivalence | boundary | Alphabet wrap-around của inverse shift; tránh input không thuộc alphabet của encoder. |
| 51 | remove_vowels | equivalence | statement | Vowel/consonant, lower/upper, non-letter; chuỗi toàn vowel và không vowel. |
| 52 | below_threshold | boundary | statement,equivalence | Tất cả dưới t, có phần tử=t hoặc>t; empty theo contract. |
| 53 | add | equivalence | boundary | Các lớp dấu và cancellation của hai integer; sanity control ít cấu trúc. |
| 54 | same_chars | equivalence | boundary | Cùng set nhưng khác multiplicity/order; một ký tự thiếu hoặc thừa. |
| 55 | fib | def_use | boundary,statement | Hai Fibonacci state qua simultaneous update; base cases và bước thứ2 trở đi. |
| 56 | correct_bracketing | def_use | statement,equivalence | Balance prefix không âm và final zero cho <>; cùng số ngoặc chưa đủ. |
| 57 | monotonic | statement | equivalence | Increasing/decreasing/constant và đổi chiều; nhánh chấp nhận hai hướng. |
| 58 | common | equivalence | boundary | Giao rỗng/không rỗng, duplicates và thứ tự; output unique sorted. |
| 59 | largest_prime_factor | statement | def_use,equivalence | Chia factor lặp và residual lớn nhất; tuân thủ n>1 và không prime. |
| 60 | sum_to_n | boundary | def_use | Inclusive upper endpoint1..n, n nhỏ; công thức hoặc loop đều cùng spec. |
| 61 | correct_bracketing | def_use | statement,equivalence | Balance prefix và final cho (); cập nhật trước khi kiểm âm, không chỉ đếm tổng. |
| 62 | derivative | def_use | boundary,equivalence | Coefficient index→nhân với bậc→dịch vị trí output; constant polynomial theo domain. |
| 63 | fibfib | def_use | boundary,statement | Ba base state0/1/2 và recurrence ba phần tử trước; tránh sequential overwrite. |
| 64 | vowels_count | statement | equivalence,boundary | Nhánh y cuối từ so với y ở giữa; vowels lower/upper theo spec/contract. |
| 65 | circular_shift | boundary | statement,equivalence | Shift nhỏ hơn/bằng/lớn hơn số digits; rule lớn hơn là reverse, không modulo. |
| 66 | digitSum | equivalence | def_use | Uppercase đóng góp ASCII, lowercase và nonletter không đóng góp; empty=0. |
| 67 | fruit_distribution | def_use | equivalence,boundary | Parse số apples/oranges đúng biến rồi total-a-b; số nhiều chữ số/zero hợp lệ. |
| 68 | pluck | statement | equivalence,boundary | Empty/no even và update minimum even; tie giữ smallest index. |
| 69 | search | boundary | equivalence,def_use | Frequency bằng value so với thiếu1/dư1; greatest qualifying positive. |
| 70 | strange_sort_list | def_use | boundary,equivalence | Hai đầu min/max luân phiên và phần tử cuối khi odd length; state toggle. |
| 71 | triangle_area | boundary | statement,equivalence | Triangle inequality đúng tại a+b=c và hai phía; round area theo spec. |
| 72 | will_it_fly | boundary | equivalence,statement | Sum bằng weight limit và hai phía, kết hợp balanced/unbalanced. |
| 73 | smallest_change | def_use | boundary,equivalence | Counter mismatch các cặp đối xứng, không đếm hai lần hoặc đếm center. |
| 74 | total_match | boundary | equivalence,statement | Tổng chars bằng nhau phải chọn list thứ1; không so số phần tử. |
| 75 | is_multiply_prime | statement | equivalence,boundary | Nhánh nhận đủ3prime factors và từ chối số factor khác; repeated prime hợp lệ. |
| 76 | is_simple_power | statement | boundary,def_use | Nhánh n=1 và power exact/nonpower; tránh loop không tiến triển. |
| 77 | iscube | boundary | equivalence | Cube exact và integer cạnh cube; zero/negative cube hợp lệ. |
| 78 | hex_key | equivalence | boundary | Prime hex symbols2/3/5/7/B/D đối với tập còn lại; uppercase domain. |
| 79 | decimal_to_binary | boundary | equivalence | 0,1 và2^k-1/2^k/2^k+1 theo contract; format db ở hai đầu. |
| 80 | is_happy | boundary | equivalence,statement | Length2/3/4, mỗi window3 phân biệt; lỗi ở window cuối. |
| 81 | numerical_letter_grade | boundary | equivalence,statement | Mọi GPA cutoff exact và hai phía;4.0/0.0 đặc biệt, không tạo cutoff ngoài domain. |
| 82 | prime_length | statement | boundary,equivalence | Length prime/composite/<2; nhánh phát hiện divisor và prime. |
| 83 | starts_one_ends | boundary | equivalence | n=1 là trường hợp giao start/end; n=2 và n lớn hơn, không double count. |
| 84 | solve | def_use | boundary,equivalence | Digit sum trước rồi convert binary; N=0 và tổng digits nhiều bit. |
| 85 | add | equivalence | boundary,statement | Tích hai phân hoạch index odd/even và value even/odd; không đảo điều kiện. |
| 86 | anti_shuffle | equivalence | boundary | Các từ riêng, nhiều blank spaces và uppercase/punctuation; giữ nguyên khoảng trắng. |
| 87 | get_row | def_use | equivalence,statement | Row/column indices tới tuple đúng thứ tự; nested ragged rows và matches lặp. |
| 88 | sort_array | statement | equivalence,boundary | Empty/singleton guard và chọn sort direction theo parity tổng endpoint. |
| 89 | encrypt | equivalence | boundary | Alphabet shift4 và wrap-around; input đúng alphabet theo contract. |
| 90 | next_smallest | statement | equivalence,boundary | Không có second distinct value trả None; duplicates và candidate update. |
| 91 | is_bored | statement | equivalence,boundary | Sentence bắt đầu I sau .?!; I trong từ hoặc giữa câu không tính. |
| 92 | any_int | equivalence | boundary,statement | Integer/noninteger và ba vị trí sum relation; đồng thời thỏa cả type lẫn arithmetic. |
| 93 | encode | equivalence | statement | Vowel/consonant × lower/upper và shift2; chỉ letters theo domain. |
| 94 | skjkasdkd | statement | def_use,equivalence | Reject composite/0/1 và update largest prime trước khi sum digits. |
| 95 | check_dict_case | statement | equivalence | Empty, nonstring key, mixed case, all-lower/all-upper; không accept title case. |
| 96 | count_up_to | boundary | statement,equivalence | Prime nhỏ hơn n, không bao gồm n; n sát0/1/2/3 nếu domain cho phép. |
| 97 | multiply | boundary | equivalence | Unit digits ở bội10 và hai phía, số âm dùng magnitude theo spec. |
| 98 | count_upper | equivalence | boundary | Index parity × uppercase vowel; lowercase/consonant là lớp khác. |
| 99 | closest_integer | boundary | equivalence,statement | Half-integer positive/negative và hai phía; tie round away from zero. |
| 100 | make_a_pile | def_use | boundary,equivalence | State giá trị mỗi level tăng2, length=n; parity của n được giữ qua toàn pile. |
| 101 | words_string | equivalence | boundary | Comma/space/mixed/repeated separator; không tạo empty token sai. |
| 102 | choose_num | statement | boundary,equivalence | Range rỗng, singleton odd/even, endpoint y odd/even; fallback-1. |
| 103 | rounded_avg | boundary | statement,equivalence | n=m, n>m và average .5; theo đúng rounding convention của oracle. |
| 104 | unique_digits | equivalence | statement | Mọi digits odd so với có ít nhất một even; filter trước sort. |
| 105 | by_length | equivalence | boundary,statement | Trong1..9 và ngoài range, duplicates, empty; sort-desc và mapping name. |
| 106 | f | def_use | equivalence,boundary | State factorial/sum cho even/odd i; không reset hoặc dùng stale accumulator. |
| 107 | even_odd_palindrome | boundary | equivalence,def_use | Bao gồm n khi n palindrome; parity tách hai counter, n=1. |
| 108 | count_nums | equivalence | boundary,def_use | Số âm chỉ digit đầu mang dấu; digit-sum<0/=0/>0. |
| 109 | move_one_ball | def_use | equivalence,statement | Số descents và cạnh last→first quyết định khả năng rotate; unique input. |
| 110 | exchange | statement | equivalence,boundary | Nhánh đủ/thiếu số even thay odd; count bằng đúng nhu cầu. |
| 111 | histogram | def_use | equivalence,statement | Count map và current max qua nhiều lần update; tie phải giữ mọi key. |
| 112 | reverse_delete | equivalence | def_use,statement | Delete-set overlap/disjoint/all và palindrome sau deletion, không trước. |
| 113 | odd_count | equivalence | boundary | Digits odd/even/zero trong từng string và format thay tất cả i đúng count. |
| 114 | minSubArraySum | def_use | boundary,equivalence | Running minimum-ending-here và global minimum; không cho subarray rỗng0. |
| 115 | max_fill | boundary | def_use,equivalence | Số1 mỗi row bằng capacity*k và hai phía; ceiling theo từng well, không gộp nước. |
| 116 | sort_array | equivalence | boundary | Bit-count khác nhau/cùng nhau và tie theo decimal; không sort lexicographic. |
| 117 | select_words | equivalence | boundary,statement | Consonant-count<n/=n/>n và chữ hoa/thường; giữ word order. |
| 118 | get_closest_vowel | statement | boundary,equivalence | Nhánh vowel giữa hai consonants từ phải; loại ký tự đầu/cuối. |
| 119 | match_parens | def_use | statement,equivalence | Balance/min-prefix khi ghép theo cả hai order; tổng balance0 chưa đủ. |
| 120 | maximum | boundary | equivalence | k=0/1/len(arr), giữ duplicates và sort kết quả; không dùng slice[-0:]. |
| 121 | solution | equivalence | boundary,statement | Value odd/even × index even/odd; index bắt đầu0. |
| 122 | add_elements | boundary | equivalence,statement | k=1/len và abs(value) quanh99/100; chỉ first k elements. |
| 123 | get_odd_collatz | def_use | statement,boundary | n update theo parity tới1 và collect odd state trước/sau đúng thời điểm. |
| 124 | valid_date | boundary | equivalence,statement | Month1/12 và day theo nhóm tháng28/29/30/31; invalid là behavior được đặc tả. |
| 125 | split_words | statement | equivalence | Ba return modes theo whitespace/comma/neither; precedence whitespace trước comma. |
| 126 | is_sorted | equivalence | boundary,statement | Sorted/unsorted × multiplicity1/2/3; phát hiện cả hai ràng buộc. |
| 127 | intersection | boundary | equivalence,statement | Intervals disjoint/touch/overlap và intersection length prime; dùng end-start theo spec. |
| 128 | prod_signs | equivalence | boundary,def_use | Empty, zero-containing, odd/even negatives; sum magnitudes × combined sign. |
| 129 | minPath | def_use | boundary,statement | Current cell/neighbors và lexicographic choice qua k bước; corner/edge/interior. |
| 130 | tri | def_use | boundary,equivalence | Tri base cases và even direct/odd recurrence với dependency n+1; output n+1 values. |
| 131 | digits | equivalence | boundary,def_use | Có/không odd digit và zero digit; product identity không được biến no-odd thành1. |
| 132 | is_nested | statement | equivalence,def_use | Nested subsequence tồn tại/không, flat groups và unmatched brackets; không chỉ đếm tổng. |
| 133 | sum_squares | boundary | equivalence | Sát integer từ hai phía, negative float; ceil trước square. |
| 134 | check_if_last_char_is_a_letter | statement | equivalence,boundary | Empty/trailing space/multi-character last word và single-letter final token. |
| 135 | can_arrange | def_use | boundary,statement | Current index và largest qualifying index; nhiều descents phải trả cái cuối. |
| 136 | largest_smallest_integers | equivalence | boundary,def_use | Negative/zero/positive và không có một trong hai miền; extremum gần0. |
| 137 | compare_one | equivalence | boundary,statement | Int/float/string và decimal dot/comma; equal numeric values trả None, giữ original type. |
| 138 | is_equal_to_sum_even | boundary | equivalence | Threshold nhỏ nhất8 và parity;6/7/8/9/10 trong domain. |
| 139 | special_factorial | def_use | boundary | Factorial tích lũy bên trong và product các factorial; n=1 và nhiều step. |
| 140 | fix_spaces | boundary | equivalence,statement | Space run length1/2/3/4 và run ở đầu/cuối;2 vẫn underscores,3 thành hyphen. |
| 141 | file_name_check | statement | equivalence,boundary | Mỗi reject return của validator và accept path; dot count, first char, digit cap3, extension. |
| 142 | sum_squares | def_use | equivalence,boundary | Original value/index tới square/cube/unchanged rồi sum; index%12=0 ưu tiên square. |
| 143 | words_in_sentence | statement | equivalence,boundary | Word-length prime/composite và empty filtered result; giữ thứ tự và format join. |
| 144 | simplify | equivalence | boundary | Fraction product whole/nonwhole; cross cancellation giữa hai fractions, denominator khác0. |
| 145 | order_by_points | equivalence | def_use | Signed digit-sum key, ties giữ original order; không sort theo numeric value khi tie. |
| 146 | specialFilter | boundary | equivalence,statement | Value>10 strict và first/last digit odd; quanh10/11 với middle digits khác nhau. |
| 147 | get_max_triples | def_use | boundary,equivalence | Index i<j<k và sum modulo3 qua triple traversal; n<3 và n=3 theo domain. |
| 148 | bf | statement | equivalence,boundary | Invalid planet guard và order hai endpoint; chỉ planets strictly between. |
| 149 | sorted_list_sum | equivalence | boundary | Word length parity và same-length lexical tie; domain mâu thuẫn phải theo contract. |
| 150 | x_or_y | statement | equivalence,boundary | Return x/y ở prime/nonprime n, đặc biệt0/1/2 theo contract; x khác y. |
| 151 | double_the_difference | equivalence | boundary,statement | Integer/noninteger × sign × parity; lọc negative và float trước square sum. |
| 152 | compare | equivalence | boundary | Equal-length score/guess lists, equal/over/under và abs difference; pair theo index. |
| 153 | Strongest_Extension | equivalence | def_use | CAP-SM strength âm/zero/dương và tie chọn first; không dùng total length. |
| 154 | cycpattern_check | statement | equivalence,boundary | Return true khi rotation hợp lệ xuất hiện và false khi mọi rotation fail; wrap positions. |
| 155 | even_odd_count | equivalence | boundary,def_use | Digit odd/even, sign ignored và integer0 có một even digit. |
| 156 | int_to_mini_roman | boundary | equivalence | Roman cutoffs4/9/40/90/400/900 và hai phía; num1..1000. |
| 157 | right_angle_triangle | boundary | equivalence,statement | Pythagorean equality và hai phía, side permutation; valid triangle constraints. |
| 158 | find_max | equivalence | def_use | Unique-char count so với length, tie lexical không phải input order. |
| 159 | eat | boundary | statement,equivalence | Need bằng remaining và thiếu/dư1, number/need/remaining ở0/1000. |
| 160 | do_algebra | def_use | equivalence,statement | Operand/operator tới expression evaluation đúng precedence/associativity; input hợp lệ an toàn. |
| 161 | solve | statement | equivalence | Nhánh có letter thì swapcase, no-letter thì reverse; digit/punctuation mixed. |
| 162 | string_to_md5 | statement | boundary,equivalence | Empty→None, nonempty→hash; đúng bytes/encoding theo domain. |
| 163 | generate_integers | boundary | equivalence,statement | Endpoint inclusive, đảo a/b và giao range với even digits2/4/6/8. |

## Giới hạn

- Primary labels are manual development priorities, not exclusive bug categories.
- Statement fit needs a cached uncovered executable line and a supported static graph; feasibility remains unknown.
- Static def-use candidates do not establish uncovered def-clear paths; heap/alias mutation is not modeled.
- No reference source, plus tests, detected outcomes or model responses select tasks/PUTs.
- Check subsets are development checks, not a scientifically held-out dataset.
- Old TrickCatcher availability is source availability only; no current-runtime qualification is asserted.
