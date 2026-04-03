---
id: FINDING-005
title: "Submit page exposes class templates to non-members"
severity: Medium
cwe: CWE-200
status: open
---

## Description

The browser submission page renders today's task template for any authenticated user who knows a class identifier. The corresponding submission API correctly enforces membership in `submit_task()`, but the SSR route does not check whether the current user belongs to the class before loading and returning the template. This creates an API/page authorization mismatch and leaks private class task content.

## Evidence

- **File**: `src/tasks/submissions/router.py:419`
- **Code**:
  ```
  @router.get("/pages/student/classes/{class_id}/submit", name="submit_task_page")
  async def submit_task_page(
      request: Request,
      class_id: str,
      ...,
      current_user: User = Depends(get_page_user),
  ):
      from tasks.templates.service import get_template_for_date

      today_template = await get_template_for_date(class_id, date.today())
      if today_template is None:
          return {"current_user": current_user, "class_id": class_id, "template": None, ...}
      ...
      return {"current_user": current_user, "class_id": class_id, "template": today_template, ...}
  ```
- **Explanation**: The route trusts any authenticated user and never verifies a `ClassMembership` for `class_id`. By contrast, `submit_task()` explicitly rejects non-members with `MembershipError`, so the page is materially less strict than the write path.

## Impact

Students or other authenticated users can inspect the existence and contents of daily assignments for classes they do not belong to, including private classes if they can obtain the class ID. Even if the actual submission attempt is later blocked, the page already discloses teacher-authored task names, descriptions, and field definitions.

## Remediation

### Recommendation

Use the same class-membership check for the page route that the submission API relies on. The simplest fix is to require an existing `ClassMembership` (or a manager override via `can_manage_class`) before calling `get_template_for_date()`.

### Before

```
today_template = await get_template_for_date(class_id, date.today())
```

### After

```
membership = await ClassMembership.find_one(
    ClassMembership.class_id == class_id,
    ClassMembership.user_id == str(current_user.id),
)
if membership is None:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")
today_template = await get_template_for_date(class_id, date.today())
```

### References

- [CWE-200](https://cwe.mitre.org/data/definitions/200.html)
- [CWE-863](https://cwe.mitre.org/data/definitions/863.html)
