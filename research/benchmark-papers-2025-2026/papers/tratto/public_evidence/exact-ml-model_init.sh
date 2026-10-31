export PYTHONPATH="./"

# Get current directory
current_dir=$(realpath "$(dirname "${BASH_SOURCE[@]}")")
# Setup global variables
source "${current_dir}/utils/global_variables.sh"

# Check the number of parameters
if [ "$#" -gt 2 ]; then
    echo "Error: Too many parameters provided. Maximum allowed is 2 (--datasets, --checkpoint)."
    exit 1
fi

# Initialize variables
datasets=""
checkpoint=""

# Loop through the parameters
while [ "$#" -gt 0 ]; do
    case "$1" in
        --datasets)
            datasets="--datasets"
            ;;
        --checkpoints)
            checkpoints="--checkpoint"
            ;;
        *)
            echo "Error: Unknown parameter '$1'."
            exit 1
            ;;
    esac
    shift
done

if [ -n "$datasets" ]; then
  if [ ! -d "$DATASETS_DIR" ]; then
    echo "Generating datasets directory"
    mkdir -p "$DATASETS_DIR"
  fi
  while IFS=, read -r file_name link; do
    # Remove possible leading and trailing whitespaces
    link="${link//[$'\t\r\n ']/}"
    wget -O "${DATASETS_DIR}/${file_name}" "$link"
  done < "$DATASETS_LINKS"
fi
if [ -n "$checkpoints" ]; then
  if [ ! -d "$CHECKPOINT_DIR" ]; then
    echo "Generating checkpoint directory"
    mkdir -p "$CHECKPOINT_DIR"
  fi
  while IFS=, read -r file_name link; do
    # Remove possible leading and trailing whitespaces
    link="${link//[$'\t\r\n ']/}"
    wget -O "${CHECKPOINT_DIR}/${file_name}" "$link"
  done < "$CHECKPOINT_LINKS"
fi
