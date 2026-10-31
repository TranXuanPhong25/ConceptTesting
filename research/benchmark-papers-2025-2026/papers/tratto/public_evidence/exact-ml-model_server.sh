export PYTHONPATH="./"

# Get current directory
current_dir=$(realpath "$(dirname "${BASH_SOURCE[@]}")")
# Setup global variables
source "${current_dir}/utils/global_variables.sh"

# Parameters to run server with model
model_type="codellama"
tokenizer_name="codellama/CodeLlama-7b-hf"
model_name_or_path="${ROOT_DIR}/checkpoint"
max_src_length=2015
max_tgt_length=30
port="${1:-5000}"

python3 scripts/server/server.py \
  --port "$port" \
  --model_type "$model_type" \
  --tokenizer_name "$tokenizer_name" \
  --model_name_or_path "$model_name_or_path" \
  --max_src_length "$max_src_length" \
  --max_tgt_length "$max_tgt_length"