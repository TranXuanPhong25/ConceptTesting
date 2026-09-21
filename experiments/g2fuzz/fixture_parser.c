#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { HEADER_SIZE = 8 };

static uint8_t checksum(const uint8_t *data, size_t size) {
  uint8_t total = 0;
  for (size_t i = 0; i < size; ++i) total = (uint8_t)(total + data[i]);
  return total;
}

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  FILE *file = fopen(argv[1], "rb");
  if (!file) return 65;
  uint8_t data[512];
  size_t size = fread(data, 1, sizeof(data), file);
  fclose(file);

  if (size < HEADER_SIZE + 1 || data[0] != 'G' || data[1] != '2' ||
      data[2] != 'F' || data[3] != 'Z' || data[4] != 1)
    return 10;
  uint16_t payload_size = ((uint16_t)data[6] << 8) | data[7];
  if (payload_size != size - HEADER_SIZE - 1 || checksum(data, size - 1) != data[size - 1])
    return 11;

  const uint8_t *payload = data + HEADER_SIZE;
  int has_bug_marker = payload_size >= 4 && payload[0] == 'B' && payload[1] == 'U' &&
                       payload[2] == 'G' && payload[3] == '!';
#ifdef CONTROLLED_MUTANT
  /* Deliberate local mutant: target marker is accepted without its required flag. */
  if (has_bug_marker) return 42;
#else
  if ((data[5] & 1) && has_bug_marker) return 42;
#endif
  return 0;
}
