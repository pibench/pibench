# Shared DB Migration Plan

## What tau2-bench Does (The Reference)

tau2-bench uses **one shared `db.json` per domain** containing ALL data — 500 users, 1,000 orders, 50 products — in a single file. Every scenario starts from the same full database. The scenario just says WHO the user is and WHAT they want. No per-scenario data patching at all.

```
domains/retail/
├── db.json       ← 83,751 lines. ALL users, ALL orders, ALL products.
├── policy.md
└── tasks.json    ← 114 tasks. Each has initial_state: null (no patches).
```

## What pi-bench Does Today (The Problem)

Every scenario carries its **entire world inline** inside `initial_state_patch`. A single finance scenario is ~100 lines of duplicated customer/account data. Across 34 scenarios, the same customer profiles, account details, and policy constants are copy-pasted over and over.

The `db.json` files per domain exist but are **empty skeletons** — right keys, no data:

| File | Lines | Content |
|------|-------|---------|
| `domains/finra/db.json` | 18 | All empty: `{}`, `[]` |
| `domains/retail/db.json` | 7 | All empty |
| `domains/helpdesk/db.json` | 21 | All empty |

When a scenario loads, `scenario_loader.py` does:

```python
base_db = load db.json          # empty
patch = scenario.initial_state_patch  # everything
db = deep_merge(base_db, patch)       # patch IS the entire DB
```

### Why This Is a Problem

1. **Massive duplication** — Customer "Linda Park" is fully defined in scen_010. If another scenario uses her, her entire profile gets copied again. Constants like `ctr_threshold_usd = 10000` repeat in every finance scenario.

2. **Hard to maintain** — Updating a customer field or adding a new field to all customers means editing every scenario that references that customer.

3. **Bloated scenarios** — Each scenario JSON is 150–230 lines. Most is generic entity data. The actual scenario-specific part (pending requests, active alerts) is maybe 10–20 lines buried inside.

4. **Doesn't match tau2-bench pattern** — We want pi-bench to follow the same architecture: shared DB as the "world", scenarios as lightweight instructions.

### Concrete Example of Duplication

**scen_010 (finance) — ~100 lines in `initial_state_patch`:**
- Full `constants` block (5 fields) — identical across all 10 finance scenarios
- Full `customer_profile` for Linda Park (10 fields) — would be duplicated if another scenario used her
- Full `account_status` for ACCT_LINDA_001 (9 fields) — same
- `activity` with pending wire + 3 money movements — **this is the only scenario-specific part**

## Proposed Approach

### Core Idea

Move ALL **static/generic entity data** into the shared `db.json` per domain, keyed by ID. Each scenario's `initial_state_patch` shrinks to just:
- **Which entities to activate** (by ID reference)
- **Scenario-specific dynamic state** (pending requests, active alerts, lockouts)

### Before vs After

**BEFORE (scen_010, ~100 lines in patch):**
```json
"initial_state_patch": {
  "constants": { "ctr_threshold_usd": 10000, ... },
  "customer_profile": {
    "customer_id": "CUST_LINDA_PARK",
    "display_name": "Linda Park",
    "tier": "standard",
    ... 7 more fields ...
  },
  "account_status": {
    "account_id": "ACCT_LINDA_001",
    "account_type": "brokerage",
    ... 7 more fields ...
  },
  "activity": {
    "pending_requests": [{ ...wire transfer... }],
    "money_movements": [{ ...deposit 1... }, { ...deposit 2... }, { ...deposit 3... }]
  }
}
```

**AFTER (scen_010, ~20 lines in patch):**
```json
"initial_state_patch": {
  "customer_id": "CUST_LINDA_PARK",
  "account_ids": ["ACCT_LINDA_001"],
  "activity": {
    "pending_requests": [{ ...wire transfer... }],
    "money_movements": [{ ...deposit 1... }, { ...deposit 2... }, { ...deposit 3... }]
  }
}
```

Linda Park's profile and ACCT_LINDA_001 details live in `domains/finra/db.json` — single source of truth.

### Where the Generic Data Goes

**`domains/finra/db.json`** will contain:
- `constants` — CTR threshold, SAR threshold, etc. (shared by ALL finance scenarios)
- `customers` — ALL 10 customer profiles keyed by ID
- `accounts` — ALL 13 accounts keyed by ID

**`domains/retail/db.json`** will contain:
- `customers` — ALL 12 customer profiles keyed by ID
- `orders` — ALL 12 orders keyed by ID
- `return_history` — keyed by customer ID
- `product_warranties` — keyed by item ID

**`domains/helpdesk/db.json`** will contain:
- `employees` — ALL 12 employee profiles keyed by ID
- `software_catalog` — approved/prohibited lists
- `resources` — admin dashboard, printers, shared drives, etc.
- `policies` — HR remote work, business hours

### What Stays in Each Scenario's Patch

| Domain | Stays in patch (scenario-specific) | Moves to db.json (shared) |
|--------|-----------------------------------|--------------------------|
| **Finance** | `customer_id`, `account_ids`, `activity` (pending requests, money movements), monitoring/investigation overrides | Customer profile, account details, constants |
| **Retail** | `customer_id`, `order_id`, order-level overrides | Customer profile, full order, return history, warranties |
| **Helpdesk** | `employee_id`, account state (lockout), resource/policy flags | Employee profile, software catalog, resource details, policies |

### How It Gets Assembled at Runtime

A new `_resolve_scenario_db()` function in `scenario_loader.py` will:

1. Load the full `db.json` (now has all entities)
2. Read the slim `initial_state_patch` from the scenario
3. Look up referenced entities by ID
4. Build the flat DB in the exact shape tool handlers expect
5. Merge any scenario-specific overrides on top

```
db.json (all entities)  +  scenario patch (just refs + dynamic state)
         ↓                              ↓
    _resolve_scenario_db() combines them
         ↓
    flat DB (same shape tools already expect)
         ↓
    tool handlers work unchanged
```

**Tool handlers don't change at all.** The resolver produces the exact same flat DB shape they already read from.

### Backward Compatibility

The resolver detects legacy (inline) format by checking if the patch already has old-style keys (`customer_profile` dict, `orders` list, `accounts` with `EMP_*` keys). If so, it falls back to `deep_merge()` — current behavior. This means scenarios can be migrated one at a time.

### Files Affected

- 3 `db.json` files → populated with full entity data
- 1 `scenario_loader.py` → add resolver function
- 34 scenario JSONs → shrink patches to refs + dynamic state
- **38 files total**

### Execution Plan

1. Finance domain first (most complex, proves the pattern)
2. Retail domain
3. Helpdesk domain
4. Each domain: build db.json → write resolver logic → rewrite scenario patches → run tests
5. All 67 tests must pass after each domain

Full implementation details are in `IMPLEMENTATION_GUIDE.md`.
