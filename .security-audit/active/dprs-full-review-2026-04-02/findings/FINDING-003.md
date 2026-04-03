---
id: FINDING-003
title: "Leaderboard page bypasses class membership checks"
severity: High
cwe: CWE-862
status: open
---

## Description

The HTML leaderboard page does not enforce the same access-control rules as the JSON leaderboard API. Any authenticated user can load `/pages/classes/{class_id}/leaderboard` for a private class when `leaderboard_enabled` is true, and any teacher-like account can bypass the visibility flag entirely because the route treats the presence of `MANAGE_OWN_CLASS` as sufficient even when the caller is not a teacher-member of the target class.

## Evidence

- **File**: `src/gamification/leaderboard/router.py:95`
- **Code**:
  ```
  @router.get("/pages/classes/{class_id}/leaderboard", name="leaderboard_page")
  async def leaderboard_page(
      request: Request,
      class_id: str,
      user: User = Depends(get_page_user),
  ):
      cls = await Class.get(class_id)
      if cls is None:
          raise HTTPException(status_code=404, detail="Class not found")

      visible = bool(user.permissions & MANAGE_CLASS) or cls.leaderboard_enabled
      entries = await _build_class_leaderboard(class_id) if visible else []
  ```
- **Explanation**: The route never checks whether the user belongs to the class, and it never calls `can_manage_class()` for teacher access. This is weaker than the corresponding API route, which explicitly verifies membership unless the caller has `MANAGE_ALL_CLASSES`.

- **File**: `src/gamification/leaderboard/router.py:45`
- **Code**:
  ```
  @router.get("/classes/{class_id}/leaderboard")
  async def class_leaderboard(class_id: str, user: User = Depends(get_current_user)):
      cls = await Class.get(class_id)
      ...
      if not (user.permissions & MANAGE_ALL_CLASSES):
          membership = await ClassMembership.find_one(
              ClassMembership.class_id == class_id,
              ClassMembership.user_id == str(user.id),
          )
          if membership is None:
              raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")
  ```
- **Explanation**: The API already implements the intended authorization rule. The page route drifted from this logic and now exposes a broader audience than the spec allows.

## Impact

Private-class rankings, student display names, scores, and badge counts are exposed to users outside the class. Because `leaderboard_enabled` defaults to true, the SSR route leaks data even when a class is private. Teacher accounts are even more privileged here: any teacher can browse other teachers' leaderboards without membership in the target class.

## Remediation

### Recommendation

Make the page route reuse the same membership / manager checks as the API route. If teachers should bypass `leaderboard_enabled`, require `can_manage_class(user, cls)` rather than a bare permission bit. If students should see the page only when the class enables leaderboards, enforce membership first and then apply the visibility flag.

### Before

```
visible = bool(user.permissions & MANAGE_CLASS) or cls.leaderboard_enabled
entries = await _build_class_leaderboard(class_id) if visible else []
```

### After

```
is_manager = await can_manage_class(user, cls)
if not is_manager:
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == str(user.id),
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")
visible = is_manager or cls.leaderboard_enabled
entries = await _build_class_leaderboard(class_id) if visible else []
```

### References

- [CWE-862](https://cwe.mitre.org/data/definitions/862.html)
- [CWE-200](https://cwe.mitre.org/data/definitions/200.html)
