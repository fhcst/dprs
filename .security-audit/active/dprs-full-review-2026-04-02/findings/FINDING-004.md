---
id: FINDING-004
title: "Schedule-rule API accepts malformed rules and persists them"
severity: Medium
cwe: CWE-20
status: open
---

## Description

The schedule-rule API accepts an unbounded `str` for `schedule_type`, optional dates with no mode-specific validation, arbitrary weekday integers, and negative `max_submissions_per_student` values. It then inserts the rule into MongoDB before calling `expand_schedule_rule()`. For malformed payloads such as `schedule_type="range"` without `start_date`, the service crashes with a server error after the invalid rule has already been persisted, leaving inconsistent state behind.

## Evidence

- **File**: `src/tasks/templates/router.py:55`
- **Code**:
  ```
  class ScheduleRuleRequest(BaseModel):
      template_id: str
      schedule_type: str
      start_date: Optional[_DateField] = None
      end_date: Optional[_DateField] = None
      weekdays: list[int] = []
      max_submissions_per_student: int = 0
      date: Optional[_DateField] = None
      ...

  rule = TaskScheduleRule(...)
  await rule.insert()
  assignments = await expand_schedule_rule(rule)
  ```
- **Explanation**: The request model does not constrain `schedule_type` to the supported enum, does not require the right date fields for each mode, and persists the rule before expansion succeeds.

- **File**: `src/tasks/templates/service.py:83`
- **Code**:
  ```
  elif rule.schedule_type == "range":
      current = rule.start_date
      limit = rule.start_date + timedelta(days=364)
      end = min(rule.end_date, limit)
      while current <= end:
          ...

  elif rule.schedule_type == "open":
      current = rule.start_date
      for _ in range(90):
          dates.append(current)
          current += timedelta(days=1)
  ```
- **Explanation**: `rule.start_date` and `rule.end_date` are dereferenced unconditionally. A malformed request turns into a `TypeError` or comparable runtime exception, which yields a 500 after the bad rule is already stored.

## Impact

An authenticated teacher can create orphaned or nonsensical schedule rules that the UI did not intend to support, and malformed requests can trigger 500s instead of deterministic validation errors. This weakens the integrity of scheduling data, complicates support/debugging, and makes the API diverge from the OpenSpec scheduling modes.

## Remediation

### Recommendation

Constrain `schedule_type` to the declared `ScheduleType` enum, add mode-specific validation in the request model or service layer, reject weekday values outside `0..6`, and validate all invariants before inserting the rule. Prefer a transaction-like flow: validate first, expand dates next, then persist the rule and assignments only after the inputs are known-good.

### Before

```
await rule.insert()
assignments = await expand_schedule_rule(rule)
```

### After

```
validate_schedule_rule_payload(body)
assignments = compute_assignments(body)
rule = TaskScheduleRule(...)
await rule.insert()
for assignment in assignments:
    await assignment.insert()
```

### References

- [CWE-20](https://cwe.mitre.org/data/definitions/20.html)
- [CWE-703](https://cwe.mitre.org/data/definitions/703.html)
