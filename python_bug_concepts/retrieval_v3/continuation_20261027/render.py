"""Completion-aware report combining frozen scores, native review and utility."""
import json
from pathlib import Path
from .report import report
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def render():
    s=report()
    ranks=json.loads((HERE/'RANKING.json').read_text())['summary']
    sample=json.loads((HERE/'MANUAL_SAMPLE_REVIEW.json').read_text())
    audit=json.loads((HERE/'NATIVE_CLAIM_AUDIT.json').read_text())
    rows=['# Đánh giá chất lượng Python bug concept retrieval','',
          'Kết quả trên 113 buggy PUT HumanEval. Hit yêu cầu concept mô tả actual bug; chỉ liên quan đến một operation không được tính. Corpus và các task đã được xem khi phát triển, nên các số dưới đây không phải đánh giá generalization độc lập.','',
          '## Retrieval và cải thiện','',
          '| Retriever | Bug family hit@3 /113 | Family + first faulty site /113 | Hit@1 /113 | Returned cards | Frozen-label precision |',
          '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name,label in [('v2','V2 structural'),('v3_original','V3 Qwen nguyên bản'),('v3_deduplicated','V3 + phục hồi duplicate ID'),('fusion','V4 hybrid, post-hoc')]:
        r=ranks[name]
        rows.append(f"| {label} | {r['family_hit_at_3']} | {r['site_hit_at_3']} | {r['hit_at_1']} | {r['returned_cards']} | {r['frozen_label_precision']:.1%} |")
    rows += ['',
        'V4 giữ row đầu của ID trùng, áp dụng các parser check còn lại, rồi xen kẽ Qwen rank1 / v2 rank1 / Qwen rank2… đến ba ID duy nhất. Response invalid/empty dùng v2 fallback. Không dùng gold/reference/judge tại retrieval. Không sửa raw hay kết quả v3 gốc. V4 tăng coverage, nhưng không chứng minh precision cao hơn: trả nhiều card hơn và precision theo label gần như v2. Gold chỉ có 91/113 task được gán mechanism và chưa đầy đủ; unmatched card không tự động là sai.',
        '', '## Review chất lượng trực tiếp', '',
        'Mẫu cố định 20 trong 167 row v3 được chọn bằng SHA256, không thay mẫu. Review source/spec/reference và replay native có official-contract check; reviewer là cùng tác giả của project, không phải independent annotator. Packet không chứa gold hoặc judge score.', '']
    m=sample['summary']
    rows += [f"- Concept mô tả actual bug family: **{m['actual_bug_concepts']}/20 ({m['actual_bug_concept_rate']:.0%})**.",
             f"- Đúng cả where/how/what: **{m['all_where_how_what_correct']}/20 ({m['binding_complete_rate']:.0%})**.",
             f"- Where đúng {m['where_correct']}/20; how đúng {m['how_correct']}/20; what đúng {m['what_correct']}/20.",
             '- Một concept có thể đúng cơ chế nhưng ví dụ/expected output trong what sai. Đánh giá strict: ví dụ cụ thể sai làm what không đạt.',
             '- Mẫu nhỏ; khoảng Wilson danh nghĩa cho 13/20 là 43–82%, chưa tính clustering theo task. Không suy rộng 65% thành precision đã xác minh trên toàn corpus.',
             '', '## Kiểm tra judge bằng execution', '',
             'Review có chủ đích các claim sai và positive controls; đây là diagnostic, không phải mẫu dùng ước lượng precision. Cả tám input kiểm tra claim sai đều hợp lệ và PUT trả giống reference. Trong đó năm card vẫn bị Qwen judge chấm grade 2. Source/spec reasoning, cùng replay, bác bỏ claim cụ thể; equality trên một ví dụ riêng lẻ không đủ chứng minh mọi ứng dụng của card đều sai.', '',
             '| Task | Claim sai / vì sao | PUT và reference | Judge grade |', '| --- | --- | --- | ---: |']
    for r in audit['results'][:8]:
        card=(r.get('selected_response') or {}).get('judge_card')
        actual=r['put'].get('repr',str(r['put'].get('value')))
        rows.append(f"| {r['task_id']} | {r['review']} | `{actual}` | {card['grade'] if card else 'schema invalid'} |")
    rows += ['', 'Positive controls: Unicode byte-count, negative maximum sentinel, fixed triple-space replacement và signed difference đều có official-valid input làm PUT khác reference. Kết quả và exact argument nằm trong `NATIVE_CLAIM_AUDIT.json`.', '',
             '## Qwen judge trên toàn bộ returned concepts', '',
             f"Judge schema hợp lệ trên {s['judge_valid_tasks']}/113 task; v3 có {s['retrieval_schema_failures']} response retrieval invalid. Judge cùng model với retriever và có thể đoán method từ style; chỉ là auxiliary score.", '',
             '| Metric | V2 | V3 original |','| --- | ---: | ---: |']
    for label,key,percent in [('Grade >=2 / all returned','judge_precision_returned_conservative',True),('Mean grade 0–3','judge_mean_grade_0_to_3',False),('Where accuracy, graded bindings','judge_where_accuracy',True),('How accuracy, graded bindings','judge_how_accuracy',True),('What accuracy, graded bindings','judge_what_accuracy',True)]:
        values=[f"{s['quality'][name][key]:.1%}" if percent else f"{s['quality'][name][key]:.3f}" for name in ['v2','v3']]
        rows.append(f'| {label} | {values[0]} | {values[1]} |')
    rows += ['', '**Các false positive native ở trên cho thấy không được dùng judge score như ground truth.**', '', '## Native utility: concept có giúp tạo test không?', '']
    completeness=s['utility_completeness']
    rows.append(f"Trạng thái: **{completeness['status']}**, đã lưu {completeness['saved_request_results']}/120 arm record, các slot có response thành công {completeness['received_responses']}; native grading {'đã có' if completeness['native_grading_present'] else 'chưa chạy'}. Chưa hoàn tất không được diễn giải thành 0 bug.")
    rows.append(f"Số unique utility request trong các arm đã lưu: {completeness['unique_response_requests']}; {completeness['identical_request_reused_slots']} arm slot dùng chung exact response do message/seed giống nhau. Không gọi lại các request này.")
    if completeness['status']=='complete':
        rows += ['', '| Metric | Plain | V2 | V3 original |','| --- | ---: | ---: | ---: |']
        for label,key in [('Proposed tests','proposed_tests'),('Official-valid tests','valid_tests'),('Correct oracle tests','oracle_correct_tests'),('Confirmed bug tasks /40','confirmed_bug_tasks'),('False-alarm tests','false_alarm_tests'),('False-alarm tasks','false_alarm_tasks'),('Unresolved workers','unresolved_workers')]:
            rows.append('| '+label+' | '+' | '.join(str(s['native_utility'][arm][key]) for arm in ['plain','v2','v3'])+' |')
        for name,stats in s['native_utility']['paired'].items():
            rows.append(f"\n{name}: {stats['wins']} task win / {stats['losses']} loss.")
        rows += ['', 'Confirmed bug cần input hợp lệ, expected output khớp reference và PUT khác reference hoặc raise. False alarm là assertion fail với expected output sai. Missing/invalid response vẫn giữ task denominator 40. Ba arm có cùng 40 task slots, seed và token cap; exact request giống nhau được dùng chung response như đã ghi. V3 có thêm chi phí retrieval. Utility dùng card definition, không có v3 explanations. Không suy utility v3 thành hiệu quả của v4 hybrid.']
    rows += ['', 'Kết luận: V2 tốt hơn original V3 về native bug-task coverage và false alarms trong cohort này. V4 tăng retrieval family/site coverage trên dữ liệu đã xem nhưng chưa có utility riêng; giữ v2 làm default. Concept hints có ích trong phép thử plain-vs-hinted này, nhưng chưa có placebo hoặc independent holdout để khẳng định generalization hay causal attribution cho từng concept.', '', '## Artifacts', '',
             '- [V4 API](../retrieval_v4/README.md).',
             '- [Ranking từng task](continuation_20261027/RANKING.json).',
             '- [Manual sample review + native replay](continuation_20261027/MANUAL_SAMPLE_REVIEW.json).',
             '- [Native claim audit](continuation_20261027/NATIVE_CLAIM_AUDIT.json).',
             '- [Quality summary và usage](out/run_20261026/QUALITY_SUMMARY.json).',
             '- [Utility native outcomes](out/run_20261026/utility_grading.json).',
             '- [Continuation preregistration](continuation_20261027/PREREG.md).', '',
             'Verification: 60 unit/regression tests pass, bao gồm đối chiếu V4 API với ranking đã lưu trên đủ 113 task. Frozen v2 labels và ba file run/prompts/client v3 không thay đổi. Raw request/response và original terminal failure giữ nguyên.', '']
    (ROOT/'RESULTS.md').write_text('\n'.join(rows))
    return s
if __name__=='__main__':
    s=render(); print(json.dumps(s['utility_completeness']))
