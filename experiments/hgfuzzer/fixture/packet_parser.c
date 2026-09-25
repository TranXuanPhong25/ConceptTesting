/* Deliberately vulnerable local teaching fixture. Never use as production code. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint8_t xor_checksum(const uint8_t *data, size_t length) {
  uint8_t value = 0;
  for (size_t i = 0; i < length; ++i) value ^= data[i];
  return value;
}

static int copy_payload(const uint8_t *payload, uint8_t declared_len) {
  uint8_t destination[8];
  printf("TARGET_HIT\\n");
  fflush(stdout);
#ifdef FIXED
  if (declared_len > sizeof(destination)) {
    printf("FIXED_REJECT\\n");
    return 0;
  }
#endif
  memcpy(destination, payload, declared_len);
  return destination[0] == 0xff;
}

static int parse_packet(const uint8_t *input, size_t input_len) {
  if (input_len < 5 || input[0] != 'H' || input[1] != 'G' || input[2] != 1) return 0;
  uint8_t declared_len = input[3];
  if (input_len != (size_t)declared_len + 5) return 0;
  if (xor_checksum(input, input_len - 1) != input[input_len - 1]) return 0;
  if (declared_len <= 8) return 0;
  return copy_payload(input + 4, declared_len);
}

int main(void) {
  uint8_t input[260];
  size_t input_len = fread(input, 1, sizeof(input), stdin);
  return parse_packet(input, input_len);
}
