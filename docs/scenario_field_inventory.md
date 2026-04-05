# Scenario Field Inventory

This document inventories the fields present in the scenario JSON files under [`scenarios/`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/scenarios), maps them to current runtime usage, and calls out unused or inconsistent fields before we lock down a formal schema.

## Scope

- Active scenarios scanned: 34
  - `finra`: 10
  - `retail_refund_sop_v1`: 12
  - `helpdesk_access_control_v1`: 12
- Archive scenarios scanned: 5 under `scenarios/archive/20260304_rework`
- All 34 active scenarios share the same 12 top-level fields.
- Archive-only legacy fields:
  - `expected_outcomes[]`
  - `environment_setup.initial_state_patch.constants.*`

## Legend

- Direct: read directly by current pi-bench runtime.
- Pass-through: not interpreted by pi-bench itself, but merged into the environment DB for tool access.
- Diagnostic-only: used only for validation or reporting labels, not scoring/runtime behavior.
- Unused: present in scenario files but not read by the current runtime path.
- Inconsistent: present, but naming or shape differs across scenarios or from runtime assumptions.

## 1. Fixed Top-Level Schema

| Path | Presence | Current usage | Where used | Status / notes |
| --- | --- | --- | --- | --- |
| `schema_version` | 34/34 | Scenario discovery and validation gate | `src/pi_bench/scenario_loader.py`, `src/pi_bench/evaluator/scenario_validator.py` | Direct |
| `meta` | 34/34 | Mixed | See child rows | Direct container |
| `taxonomy` | 34/34 | Intended for metrics, but not wired into runtime results | `src/pi_bench/metrics.py` | Inconsistent with current wiring |
| `label` | 34/34 | Scenario label, validation, event flags, results | `src/pi_bench/scenario_loader.py`, `src/pi_bench/evaluator/scenario_validator.py`, `src/pi_bench/event_flags/__init__.py`, `src/pi_bench/a2a/results.py` | Direct |
| `decision_contract` | 34/34 | Not read | Runtime hardcodes resolution in `src/pi_bench/decision/__init__.py` | Unused |
| `policy_context` | 34/34 | Policy text loading and prompt text | `src/pi_bench/scenario_loader.py` | Direct / partial |
| `environment_setup` | 34/34 | Environment DB seeding | `src/pi_bench/scenario_loader.py`, `src/pi_bench/a2a/assessment.py` | Direct |
| `user_simulation` | 34/34 | User simulator prompt / first message / pressure script | `src/pi_bench/users/scripted_user.py`, `src/pi_bench/users/user.py`, `src/pi_bench/a2a/assessment.py` | Direct |
| `ablation_hints` | 34/34 | Not read | None | Unused |
| `evidence_pointer_contract` | 34/34 | Not read | None | Unused |
| `capability_axes` | 34/34 | Not read | None | Unused |
| `evaluation_criteria` | 34/34 | Evaluation dispatch and scoring | `src/pi_bench/evaluator/__init__.py`, `src/pi_bench/evaluator/scenario_validator.py` | Direct |

## 2. Fixed Nested Fields

### 2.1 `meta.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `meta.scenario_id` | 34/34 | Task ID, scenario result ID, scenario listing | Direct |
| `meta.domain` | 34/34 | Domain resolution | Direct |
| `meta.policy_pack` | 34/34 | Not read | Unused |
| `meta.created_at` | 34/34 | Not read | Unused |
| `meta.timezone` | 34/34 | Not read | Unused |
| `meta.notes` | 34/34 | Included in task description prompt | Direct |
| `meta.mismatch_type` | 5/34 | Not read | Unused, rebuild-only |
| `meta.previous_version` | 5/34 | Not read | Unused, rebuild-only |
| `meta.rebuild_reason` | 5/34 | Not read | Unused, rebuild-only |

Active `meta.domain` values:

- `finra`
- `retail_refund_sop_v1`
- `helpdesk_access_control_v1`

### 2.2 `taxonomy.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `taxonomy.primary` | 34/34 | Intended for metrics, but never propagated into run results | Unused by active runtime |
| `taxonomy.secondary[]` | 34/34 | Not read | Unused |
| `taxonomy.pressure[]` | 34/34 | Not read | Unused |
| `taxonomy.mismatch_type` | 5/34 | Not read | Unused, rebuild-only |

Active `taxonomy.primary` values:

- `Policy Activation`
- `Procedural Compliance`
- `Authorization Governance`
- `Operational Safety`
- `Norm Resolution`
- `Temporal Integrity`
- `Norm Interpretation`
- `Epistemic Discipline`
- `Justification Integrity`

Important inconsistency:

- [`src/pi_bench/metrics.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/metrics.py) expects a different canonical task set (`Policy Interpretation`, `Authorization & Access Control`, `Harm Avoidance`, `Privacy & Information Flow`, `Escalation Judgment`, etc.).
- Even if we start wiring `taxonomy.primary` through, the current active taxonomy labels will not match the metrics module.

### 2.3 `decision_contract.canonical_decision_resolution.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `preferred_tool` | 34/34 | Not read | Unused |
| `fallback_json_field` | 34/34 | Not read | Unused |
| `allowed_values[]` | 34/34 | Not read | Unused; active scenarios always set `["ALLOW", "DENY", "ESCALATE"]` |
| `invalid_if_multiple` | 34/34 | Not read | Unused |
| `invalid_if_missing` | 34/34 | Not read | Unused |

Important inconsistency:

- Runtime decision resolution in [`src/pi_bench/decision/__init__.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/decision/__init__.py) hardcodes support for `ALLOW-CONDITIONAL`.
- Active scenario JSON never includes `ALLOW-CONDITIONAL` in `allowed_values`.

### 2.4 `policy_context.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `policy_context.policy_text_ref` | 34/34 | Resolves policy markdown file | Direct |
| `policy_context.policy_version` | 34/34 | Not read | Unused |
| `policy_context.policy_clauses[]` | 34/34 | Folded into task description prompt text | Direct / prompt-only |
| `policy_context.policy_clauses[].clause_id` | 93 total | Prompt text only | Direct / prompt-only |
| `policy_context.policy_clauses[].section` | 93 total | Prompt text only | Direct / prompt-only |
| `policy_context.policy_clauses[].text_ref` | 93 total | Prompt text only | Direct / prompt-only |

### 2.5 `environment_setup.*`

| Path | Presence | Current usage | Where used | Status / notes |
| --- | --- | --- | --- | --- |
| `environment_setup.now` | 34/34 | Injected into DB and A2A ticket | `src/pi_bench/scenario_loader.py`, `src/pi_bench/a2a/assessment.py`, `domains/generic.py` | Direct |
| `environment_setup.initial_state_patch` | 34/34 | Deep-merged into DB seed | `src/pi_bench/scenario_loader.py` | Direct |
| `environment_setup.customer` | 22/34 | Not used in current `scenario_loader.load()` path | Only old `domains/finra/__init__.py` reads it | Inconsistent / effectively unused |
| `environment_setup.account` | 9/34 | Not used in current `scenario_loader.load()` path | Only old `domains/finra/__init__.py` reads it | Inconsistent / effectively unused |
| `environment_setup.employee` | 12/34 | Injected into DB, used by helpdesk lookups / verification | `src/pi_bench/scenario_loader.py`, `domains/generic.py` | Direct |
| `environment_setup.agent_role` | 1/34 | Not read | None | Unused, inconsistent one-off |
| `environment_setup.agent` | 1/34 | Not read | None | Unused, inconsistent one-off |

Observed shapes:

- `environment_setup.customer.{customer_id,display_name}`
- `environment_setup.account.{account_id}`
- `environment_setup.employee.{employee_id,display_name,department,job_title,account_type,manager,work_location,date_of_birth,phone_last_four,email?,role?,existing_access[]?,hire_date?,remote_classification?,data_handling_training_completed?}`
- `environment_setup.agent_role.{role,tenure_months,name,supervisor}` only in `scen_013`
- `environment_setup.agent.{agent_id,role,tenure_months}` only in `scen_019`

Important inconsistency:

- The main loader path in [`src/pi_bench/scenario_loader.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/scenario_loader.py) only copies `employee` and `now` out of `environment_setup`.
- `customer`, `account`, `agent_role`, and `agent` are not preserved in the active runtime path.

### 2.6 `user_simulation.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `persona` | 34/34 | User prompt construction | Direct |
| `initial_user_message` | 34/34 | First user turn / A2A ticket enrichment | Direct |
| `pressure_script[]` | 34/34 | Scripted or LLM user follow-up turns | Direct |

Observed personas:

- `customer`
- `employee`
- `internal_manager`

### 2.7 `ablation_hints.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `structured_policy` | 34/34 | Not read | Unused |
| `no_pressure_user_message` | 34/34 | Not read | Unused |

### 2.8 `evidence_pointer_contract.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `on_fail_include[]` | 34/34 | Not read | Unused |
| `notes` | 34/34 | Not read | Unused |

Observed `on_fail_include` values are identical in all active scenarios:

- `outcome_id`
- `message_index`
- `step_index`
- `tool_call_id`
- `matched_span`

### 2.9 `capability_axes[]`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `capability_axes[]` | 34/34 | Not read | Unused |

Observed active values:

- `rule_application`
- `escalation_judgment`
- `framing_resistance`
- `information_containment`
- `pattern_detection`
- `justification_fidelity`

### 2.10 `evaluation_criteria.*`

| Path | Presence | Current usage | Status / notes |
| --- | --- | --- | --- |
| `reward_basis[]` | 34/34 | Evaluator dispatch | Direct |
| `policy_checks[]` | 34/34 | Deterministic evaluator | Direct |
| `nl_judge_checks[]` | 20/34 | LLM judge evaluator | Direct |
| `state_field_checks[]` | 3/34 | Deterministic DB-field evaluator | Direct |

Observed active `reward_basis` values:

- `POLICY`
- `NL_JUDGE`
- `STATE_FIELD`

Evaluator-supported but absent from active scenarios:

- `ACTION`
- `DB`
- `COMMUNICATE`
- `ENV_ASSERTION`
- `NL_ASSERTION`

#### `policy_checks[]` keys

| Path | Current usage | Status / notes |
| --- | --- | --- |
| `outcome_id` | Validation labels only | Diagnostic-only in current runtime |
| `type` | Policy evaluator dispatch | Direct |
| `notes` | Not read | Unused |
| `tool_name` | Used by tool-based checks | Direct |
| `equals` | Used by `decision_equals` | Direct |
| `arguments` | Used by `tool_called_with` | Direct |
| `tool_names[]` | Used by `tool_called_any` | Direct |
| `first_tool` | Used by `tool_before_tool` | Direct |
| `second_tool` | Used by `tool_before_tool` | Direct |
| `min_times` | Used by `tool_called_min_times` | Direct |
| `axis` | Not read | Unused |

Observed active `policy_checks[].type` values:

- `tool_called`
- `tool_not_called`
- `decision_equals`
- `tool_called_with`
- `tool_called_any`
- `tool_before_tool`
- `tool_called_min_times`

Policy evaluator supports but active scenarios do not use:

- `tool_before_tool_any`
- `message_not_contains`
- `escalation_attempted`

#### `state_field_checks[]` keys

| Path | Current usage | Status / notes |
| --- | --- | --- |
| `outcome_id` | Returned in results and validator labels | Direct / reporting |
| `type` | Dispatch | Direct |
| `field_path` | DB navigation path | Direct |
| `equals` | Expected value | Direct |
| `notes` | Not read | Unused |

#### `nl_judge_checks[]` keys

| Path | Current usage | Status / notes |
| --- | --- | --- |
| `outcome_id` | Returned in result objects | Direct / reporting |
| `type` | Dispatch | Direct |
| `scope` | Judge message scope | Direct |
| `judge_question` | Judge prompt | Direct |
| `expected_answer` | Judge assertion target | Direct |
| `notes` | Not read | Unused |
| `axis` | Not read | Unused |

Observed active `nl_judge_checks[].type` value:

- `nl_assertion_llm_judge`

Observed active `nl_judge_checks[].scope` values:

- `assistant_messages`
- `final_assistant_message`

## 3. Domain-Specific `initial_state_patch` Fields

The critical design point is in [`domains/generic.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/domains/generic.py): the scenario `initial_state_patch` is treated as the environment DB. That means these fields are closer to domain fixture schema than benchmark-core schema.

### 3.1 FINRA

Present top-level patch sections:

- `customer_profile`
- `account_status`
- `activity`
- `monitoring`
- `investigations`
- `dual_authorization` (1 scenario)

#### `customer_profile`

- Fields: `customer_id`, `display_name`, `tier`, `kyc_status`, `risk_rating`, `account_open_date`, `pep_flag`, `linked_accounts[]`, `assigned_banker`, `notes[]`
- Runtime use:
  - returned by `query_customer_profile`
  - read by generic fallback / retail-style matching helpers only if explicitly queried
- Shape issue:
  - `assigned_banker` is usually `null`
  - one scenario uses `assigned_banker.{name,status,return_date}`

#### `account_status`

- Common fields: `account_id`, `account_type`, `status`, `balance_usd`, `available_balance_usd`, `holds[]`, `lock_up_period`, `compliance_flags[]`, `investigation_hold`
- Runtime use:
  - returned by `query_account_status`
  - referenced by `get_full_history`
- Shape issue:
  - 9 scenarios use a single object
  - 1 scenario uses a map: `account_status.<account_id> -> object`
  - `lock_up_period` is usually `null`; one scenario uses `lock_up_period.{fund_name,start_date,end_date,penalty_description}`

#### `activity`

- `pending_requests[].{request_id,requested_at,requested_by_customer_id,account_id,type,status,details}`
- `pending_requests[].details.{direction,method,amount,currency,beneficiary,purpose?,customer_note?,deadline_at?}`
- `pending_requests[].details.beneficiary.{name,bank?,account_ref?,relationship?}`
- `money_movements[].{movement_id,timestamp,account_id,customer_id,direction,method,amount,currency,originator?,beneficiary?}`
- `money_movements[].originator.{description?,bank?,account_ref?,account_id?}`
- `money_movements[].beneficiary.{name?,bank?,account_ref?,account_id?}`
- `orders[]`
- `trades[]`
- Runtime use:
  - `query_activity`
  - `hold_transaction`
  - `process_wire_transfer`
  - `update_request_status`
  - `verify_dual_authorization`
  - `get_full_history`

#### `monitoring.alerts[]`

- Fields: `alert_id`, `account_id`, `category`, `severity`, `status`, `description`, `created_at`
- Runtime use:
  - seeded prior alerts
  - mutated by `create_alert`
  - read / mutated by `dismiss_alert`

#### `investigations.cases[]`

- Fields: `case_id`, `customer_id`, `case_type`, `status`, `assigned_to`, `opened_at`, `summary`
- Runtime use:
  - seeded prior cases
  - mutated by `open_case`

#### `dual_authorization`

- Fields: `request_id`, `dual_auth_required`, `authorizations[]`, `authorization_complete`, `missing_authorizers`
- Runtime use:
  - currently not read from DB by the active generic handler
  - `verify_dual_authorization` recomputes status from `activity.pending_requests` instead
- Status: pass-through data with no current reader

### 3.2 Retail

Present top-level patch sections:

- `customer_profile`
- `orders`
- `product_warranty` (1 scenario)
- `return_history_last_90_days` (1 scenario)

#### `customer_profile`

- Fields: `customer_id`, `display_name`, `loyalty_tier`, `loyalty_points`, `member_since`, `lifetime_spend`, `returns_last_90_days`, `returns_last_365_days`, `account_flags[]`, `fraud_score_internal`
- Runtime use:
  - returned by `lookup_customer_profile`
  - read by `check_return_eligibility`
  - mutated by `flag_account`

#### `orders[]`

- Common fields: `order_id`, `customer_id`, `order_date`, `delivery_date`, `status`, `payment_method`, `total_amount`, `is_final_sale`, `flags[]`, `items[]`
- `items[]` fields: `item_id`, `name`, `category`, `price`, `quantity`
- Optional item fields: `activation_date`, `device_activated`, `defect_reported`, `product_description`
- Runtime use:
  - returned by `lookup_order`
  - read by `check_return_eligibility`
  - mutated by `process_refund`

#### `product_warranty`

- Fields: `item_id`, `manufacturer_support_url`, `manufacturer_warranty`, `replacement_available`, `replacement_sku`
- Runtime use:
  - no current generic retail handler reads this object
- Status: currently unused

#### `return_history_last_90_days[]`

- Fields: `return_id`, `date`, `category`, `amount`
- Runtime use:
  - no current generic retail handler reads this array
- Status: currently unused

### 3.3 Helpdesk

Present top-level patch sections:

- `accounts`
- `account_status` (1 scenario)
- `tickets`
- `approvals`
- `approval_tickets` (1 scenario)
- `business_hours` (1 scenario)
- `database_access` (1 scenario)
- `device_inventory` (1 scenario)
- `hr_remote_work_policy` (1 scenario)
- `it_security_on_call` (1 scenario)
- `printer_access` (1 scenario)
- `requested_resource` (1 scenario)
- `shared_drives` (1 scenario)
- `software_catalog` (2 scenarios)
- `admin_dashboard` (1 scenario)
- `byod_policy` (1 scenario, `null`)
- `personal_device_procedures` (1 scenario, `null`)

#### `accounts.<employee_id>`

- Common fields: `account_type`, `lockout_status`, `status`
- Optional fields: `password_last_changed`, `failed_attempts`, `lockout_reason`, `lockout_timestamp`, `admin_privileges[]`, `vpn_status`, `vpn_approval_ticket`, `admin_dashboard_access`, `privileged_flag`, `is_privileged`, `security_flagged`, `affected_system`, `system_classification`
- Runtime use:
  - `lookup_employee` fallback
  - `reset_password`
  - `unlock_account`

#### `account_status`

- Fields: `employee_id`, `account_type`, `lockout_status`, `is_privileged`, `security_flagged`
- Runtime use:
  - no active generic handler reads this object
- Status: inconsistent with the dominant `accounts.<employee_id>` shape

#### `tickets[]`

- Fields seen: `ticket_id`, `type`, `status`, `approved_at`, `approved_by`, `resource`, `resource_type`, `access_level`, `employee_id`, `data_owner_approval`
- Runtime use:
  - seeded prior tickets
  - appended to by `log_ticket`

#### `approvals[]`

- Fields: `ticket_id`, `employee_id`, `request_type`, `resource_name`, `status`
- Runtime use:
  - read by `check_approval_status`

#### Other helpdesk patch objects

| Path | Observed fields | Current usage |
| --- | --- | --- |
| `approval_tickets[]` | empty list only | No current reader |
| `business_hours` | `days[]`, `start`, `end`, `timezone` | No current reader |
| `database_access` | `requested_resource`, `data_owner`, `classification`, `requires_data_owner_approval` | No current reader |
| `device_inventory.<employee_id>[]` | `device_id`, `type`, `model`, `ownership`, `status` | No current reader |
| `hr_remote_work_policy` | `policy_ref`, `section_3` | No current reader |
| `it_security_on_call` | `status`, `next_available`, `reason` | No current reader |
| `printer_access` | `resource_name`, `resource_type`, `approval_status`, `approval_ticket_id` | No current reader |
| `requested_resource` | `resource_name`, `resource_type`, `system_classification`, `data_owner`, `data_owner_approval` | No current reader |
| `shared_drives.marketing_assets` | `department`, `classification`, `data_sensitivity`, `access_type` | No current reader |
| `software_catalog.approved[]` | strings | Not read by current `install_software` handler |
| `software_catalog.Figma` | `license_required`, `restricted_to_departments[]`, `status` | No current reader |
| `software_catalog.prohibited_categories[]` | strings | No current reader |
| `software_catalog.prohibited_examples[]` | strings | No current reader |
| `admin_dashboard` | `authorized_roles`, `classification`, `current_users[]` | No current reader |
| `byod_policy` | `null` | No current reader |
| `personal_device_procedures` | `null` | No current reader |

Important helpdesk mismatch:

- The generic `install_software` handler checks `db["prohibited_software"]`, but active scenarios populate `software_catalog.prohibited_categories` and `software_catalog.prohibited_examples` instead.
- That means the current active data shape does not line up with the active handler logic.

## 4. Archive-Only Legacy Fields

Archive scenarios add two legacy shapes that are not present in active scenarios:

- `expected_outcomes[]`
  - legacy evaluation format
  - still supported by `_convert_outcomes_to_criteria()` in [`src/pi_bench/scenario_loader.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/scenario_loader.py)
- `environment_setup.initial_state_patch.constants.*`
  - seen only in archived rebuild inputs
  - not read by current runtime

## 5. Cleanup Candidates

These are the fields most likely to be removed, renamed, or formalized in the next schema pass:

1. Unused benchmark-level fields
   - `meta.policy_pack`
   - `meta.created_at`
   - `meta.timezone`
   - `meta.mismatch_type`
   - `meta.previous_version`
   - `meta.rebuild_reason`
   - `ablation_hints.*`
   - `evidence_pointer_contract.*`
   - `capability_axes[]`
   - `decision_contract.canonical_decision_resolution.*`

2. Unwired taxonomy fields
   - `taxonomy.*` is present everywhere, but current runtime does not propagate it into results.
   - `src/pi_bench/metrics.py` currently expects a different taxonomy vocabulary.

3. Inconsistent environment wrapper fields
   - `environment_setup.customer`
   - `environment_setup.account`
   - `environment_setup.agent_role`
   - `environment_setup.agent`

4. Check metadata fields that do not affect runtime behavior
   - `policy_checks[].notes`
   - `policy_checks[].axis`
   - `state_field_checks[].notes`
   - `nl_judge_checks[].notes`
   - `nl_judge_checks[].axis`
   - `policy_checks[].outcome_id` is currently diagnostic-only in the active runtime

5. Domain patch fields with no current reader
   - FINRA: `dual_authorization`
   - Retail: `product_warranty`, `return_history_last_90_days`
   - Helpdesk: `approval_tickets`, `business_hours`, `database_access`, `device_inventory`, `hr_remote_work_policy`, `it_security_on_call`, `printer_access`, `requested_resource`, `shared_drives`, `software_catalog.*`, `admin_dashboard`, `byod_policy`, `personal_device_procedures`

## 6. Recommended Schema Boundary

Based on current code, the cleanest schema split is:

1. Benchmark-core scenario schema
   - `schema_version`
   - `meta.scenario_id`
   - `meta.domain`
   - `meta.notes`
   - `label`
   - `policy_context.policy_text_ref`
   - `policy_context.policy_clauses[]`
   - `environment_setup.now`
   - `environment_setup.employee` for helpdesk only
   - `environment_setup.initial_state_patch`
   - `user_simulation.*`
   - `evaluation_criteria.*`

2. Optional analysis / authoring metadata
   - `taxonomy.*`
   - `capability_axes[]`
   - `ablation_hints.*`
   - `evidence_pointer_contract.*`
   - rebuild-only `meta.*` fields

3. Domain fixture schema
   - the contents of `environment_setup.initial_state_patch`
   - ideally split into separate per-domain schemas keyed by `meta.domain`

That split matches the current code better than trying to make every leaf under `initial_state_patch` part of one monolithic benchmark-wide JSON schema.
