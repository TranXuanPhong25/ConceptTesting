#ifndef CKGFUZZER_LEDGER_H
#define CKGFUZZER_LEDGER_H

typedef struct Ledger Ledger;

Ledger *ledger_create(void);
int ledger_add(Ledger *ledger, int amount);
int ledger_commit(Ledger *ledger);
void ledger_destroy(Ledger *ledger);

#endif
