# Directories
ROOT_DIR=$(dirname "$(realpath "$(dirname "$BASH_SOURCE")")")
RESOURCES_DIR="${ROOT_DIR}/resources"
DATASETS_DIR="${ROOT_DIR}/datasets"
CHECKPOINT_DIR="${ROOT_DIR}/checkpoint"

# Files
CHECKPOINT_LINKS="${RESOURCES_DIR}/checkpoint.csv"
DATASETS_LINKS="${RESOURCES_DIR}/datasets.csv"