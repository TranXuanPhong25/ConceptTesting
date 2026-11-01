# Oracle design — source note

Primary source: [Mathews and Nagappan, Design choices made by LLM-based test
generators prevent them from finding bugs](https://arxiv.org/abs/2412.14137), 2024.
The paper motivates separating test inputs from oracles designed to pass the PUT.
Our benchmark keeps PUT-failing inputs and supplies gold through the reference.
Read for design comparison only; no reproduction or reimplementation.
