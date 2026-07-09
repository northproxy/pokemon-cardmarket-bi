# Local Database

This folder contains the local SQLite database used for MVP development and testing.

Included demo file:

```text
pokemon_cardmarket_bi.db
```

This demo database contains the `expansions` table and one verified example row for `id_expansion = 5093`.

To recreate or update the table locally:

```bash
python scripts/reference/load_expansions.py
```
