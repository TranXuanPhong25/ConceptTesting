#include <stdio.h>
#include <string.h>

int main(void) {
  char kind[8], payload[64];
  unsigned declared_len;

  if (scanf("%7[^|]|%u|%63s", kind, &declared_len, payload) != 3) {
    puts("REJECT");
    return 0;
  }
  if (strcmp(kind, "MSG") != 0 || declared_len != strlen(payload)) {
    puts("REJECT");
    return 0;
  }
  if (declared_len > 7 && strncmp(payload, "MAGMA", 5) == 0) {
    puts("GUARD_HIT");
    return 0;
  }
  puts("ACCEPT");
  return 0;
}
