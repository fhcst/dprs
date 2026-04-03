---
id: FINDING-001
title: "Class-scoped teacher routes skip ownership checks"
severity: High
cwe: CWE-639
status: open
---

## Description

Several teacher-facing routes gate access only on coarse permission flags such as `MANAGE_TASKS` or `MANAGE_OWN_CLASS`, but never verify that the requested `class_id` actually belongs to a class the caller manages. A teacher from class A can therefore request submission, attendance, template, and point-management data for class B by supplying class B's identifier directly. The codebase already has `can_manage_class()` / `_require_class_manage()` helpers, so the issue is inconsistent use of the established authorization model rather than a missing primitive.

## Evidence

- **File**: `src/tasks/submissions/router.py:149`
- **Code**:
  ```
  @router.get("/classes/{class_id}/submissions")
  async def class_submissions(
      class_id: str,
      date_param: date | None = None,
      teacher: User = Depends(require_permission(MANAGE_TASKS)),
  ):
      target = date_param or date.today()
      subs = await get_class_submissions_for_date(class_id, target)
      return [
          {
              "id": str(s.id),
              "student_id": s.student_id,
              "date": str(s.date),
              "field_values": s.field_values,
          }
          for s in subs
      ]
  ```
- **Explanation**: The endpoint returns raw submission data for any `class_id` to any authenticated user holding `MANAGE_TASKS`. Unlike the approve/reject endpoints in the same file, it never loads the class or calls `can_manage_class()` to confirm ownership-scoped access.

- **File**: `src/tasks/checkin/router.py:201`
- **Code**:
  ```
  @router.get("/pages/teacher/classes/{class_id}/attendance", name="attendance_manage_page")
  async def attendance_manage_page(...):
      from core.auth.permissions import MANAGE_OWN_CLASS, MANAGE_ALL_CLASSES
      if not (teacher.permissions & (MANAGE_OWN_CLASS | MANAGE_ALL_CLASSES)):
          raise HTTPException(status_code=403, detail="Permission denied")
      ...
      cls = await Class.get(class_id)
      if cls is None:
          raise HTTPException(status_code=404, detail="Class not found")
      ...
      memberships = await ClassMembership.find(
          ClassMembership.class_id == class_id,
          ClassMembership.role == "student",
      ).to_list()
  ```
- **Explanation**: This page checks only whether the caller has some class-management flag, not whether they are a teacher-member of the specific class. Any teacher can browse another class's attendance roster and corrections by changing the URL.

- **File**: `src/tasks/templates/router.py:308`
- **Code**:
  ```
  @router.get("/pages/teacher/classes/{class_id}/templates", name="templates_list_page")
  async def templates_list_page(..., teacher: User = Depends(require_permission(MANAGE_TASKS))):
      templates = await TT.find(TT.class_id == class_id).to_list()
      cls = await Class.get(class_id)
      class_name = cls.name if cls else class_id
      page_ctx = await build_page_context(teacher)
      return {**page_ctx, "class_id": class_id, "class_name": class_name, "templates": templates}
  ```
- **Explanation**: The same pattern exists across template list/new/edit/assign pages and the points-management page. These routes expose invite codes, template definitions, Discord webhook presence, member balances, or other teacher-only metadata without class-scoped authorization.

## Impact

Any teacher account can enumerate or read data from other teachers' classes, including student submissions, attendance state, template definitions, and point-management data. This breaks the `MANAGE_OWN_CLASS` security model, creates cross-class privacy leaks, and allows unauthorized insight into internal class operations. Because the vulnerable routes are read-oriented and use predictable path parameters, exploitation is straightforward once an attacker learns a target class ID.

## Remediation

### Recommendation

Require a class-scoped authorization check on every teacher route that accepts `class_id` or derives a class from `template_id` / `submission_id`. The safest pattern is to centralize this in helpers such as `_require_class_manage()` and reuse the same helper for both API and SSR page routes so pages cannot drift away from API-side authorization rules.

### Before

```
@router.get("/classes/{class_id}/submissions")
async def class_submissions(
    class_id: str,
    date_param: date | None = None,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    target = date_param or date.today()
    subs = await get_class_submissions_for_date(class_id, target)
```

### After

```
@router.get("/classes/{class_id}/submissions")
async def class_submissions(
    class_id: str,
    date_param: date | None = None,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    target = date_param or date.today()
    subs = await get_class_submissions_for_date(class_id, target)
```

### References

- [CWE-639](https://cwe.mitre.org/data/definitions/639.html)
- [CWE-863](https://cwe.mitre.org/data/definitions/863.html)
