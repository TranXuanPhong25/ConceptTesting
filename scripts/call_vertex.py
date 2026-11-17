#!/usr/bin/env python3
"""Gọi Gemini qua Vertex AI/ADC bằng backend có sẵn, một lần và không retry."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from final.src.models.core_model import ModelError
from final.src.models.vertex import VertexAIModel


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prompt', nargs='?', help='Prompt; bỏ trống để đọc stdin')
    parser.add_argument('--project', help='Google Cloud project; mặc định VERTEX_PROJECT/GOOGLE_CLOUD_PROJECT')
    parser.add_argument('--model', default='gemini-3.1-flash-lite')
    parser.add_argument('--max-tokens', type=int, default=1024)
    options = parser.parse_args(arguments)
    prompt = options.prompt
    if prompt is None:
        if sys.stdin.isatty():
            parser.error('Truyền prompt hoặc pipe nội dung qua stdin')
        prompt = sys.stdin.read()
    if not prompt.strip():
        parser.error('Prompt không được rỗng')
    if not 1 <= options.max_tokens <= 8192:
        parser.error('--max-tokens phải từ1đến8192')
    try:
        model = VertexAIModel(model=options.model, project=options.project, context=18192)
        response = model.generate([{'role': 'user', 'content': prompt}],
                                  temperature=.7, max_tokens=options.max_tokens, seed=314159)
    except ModelError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(response.text)
    if response.finish_reason != 'stop':
        print('Câu trả lời chạm giới hạn output; có thể tăng --max-tokens.', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
