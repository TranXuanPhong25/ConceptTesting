#include "ledger.h"

#include <stdlib.h>

struct Ledger {
    int staged_amount;
    int is_open;
};

Ledger *ledger_create(void) {
    Ledger *ledger = calloc(1, sizeof(*ledger));
    if (ledger != NULL) {
        ledger->is_open = 1;
    }
    return ledger;
}

int ledger_add(Ledger *ledger, int amount) {
    if (ledger == NULL || !ledger->is_open) {
        return -1;
    }
    ledger->staged_amount += amount;
    return 0;
}

int ledger_commit(Ledger *ledger) {
    if (ledger == NULL || !ledger->is_open) {
        return -1;
    }
    if (ledger->staged_amount < 0) {
        return -2;
    }
    ledger->is_open = 0;
    return 0;
}

void ledger_destroy(Ledger *ledger) {
    free(ledger);
}
