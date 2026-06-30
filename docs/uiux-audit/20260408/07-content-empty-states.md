# Chapter 07: Content Strategy & Empty States

**Overall Grade: C+**
Functional text content; empty states and onboarding need significant work.

---

## Content Language Audit

The system uses Traditional Chinese (zh-TW) throughout, which is appropriate for the target audience (Taiwan educational institutions).

### Terminology Consistency

| Concept | Terms Used | Consistent? |
|---------|-----------|-------------|
| Task submission | 任務提交, 作業, 繳交, 提交 | Mixed — "任務" and "作業" used interchangeably |
| Check-in | 簽到, 打卡 | Mostly "簽到", occasional "打卡" in descriptions |
| Review/Approve | 審查, 審閱, 確認 | Mixed — page title uses "審查", button uses "確認" |
| Class | 班級 | Consistent |
| Template | 模板 | Consistent |
| Badge | 徽章 | Consistent |
| Points | 積分 | Consistent |
| Leaderboard | 排行榜 | Consistent |

### Issue C1: "任務" vs "作業" Inconsistency [LOW]

**Evidence**:
- `submit_task.html:2`: `{% block title %}提交每日任務{% endblock %}` — uses "任務"
- `submission_review.html:2`: `{% block title %}任務審查{% endblock %}` — uses "任務"
- `dashboard.html:239-241`: `作業審閱` — uses "作業" for the same concept
- `class_hub.html` tool links: Mixed usage

**Impact**: Minor confusion for users. "任務" (task) and "作業" (homework) have slightly different connotations in Chinese education. Recommend standardizing on one term.

### Issue C2: "審查" vs "確認" for Approval Action [LOW]

**Evidence**:
- Page title: `submission_review.html:16` — "任務審查" (Task Review)
- Filter tab: `submission_review.html:41` — "已確認" (Confirmed)
- API endpoint name: `/api/submissions/{id}/approve` — "approve"

The action is called "確認" (confirm) in the UI but the underlying concept is "審查" (review) in the page title and "approve" in the API. Using "確認" makes the action sound less authoritative than "通過" (pass/approve).

---

## Empty State Inventory

### Comprehensive Empty State Audit

| Page | Trigger Condition | Empty State Quality | Evidence |
|------|------------------|--------------------|---------|
| Dashboard (student, no classes) | New student, not enrolled | **Poor** — Text only: "尚未加入任何班級。" | `dashboard.html:256-259` |
| Dashboard (student, no tasks today) | Enrolled but no task assigned | **Poor** — Shows empty class cards with no task section | Template logic falls through |
| Dashboard (teacher, no classes) | New teacher, no classes created | **Poor** — Same "尚未加入任何班級。" | `dashboard.html:256-259` |
| Badges page (no badges) | Student hasn't earned any badges | **Medium** — Icon + text + decorative placeholder badges | `badges.html` empty state |
| Learning history (no submissions) | Student hasn't submitted anything | **Poor** — "目前沒有任何提交紀錄" text only | `learning_history.html` |
| Class history (no submissions) | No submissions for this class | **Poor** — "目前沒有任何提交紀錄" text only | `class_history.html` |
| Community feed (no posts) | No one has shared yet | **Medium** — Icon (speech bubble) + encouraging text | `feed.html:69-74` |
| Templates list (no templates) | Teacher hasn't created templates | **Good** — Icon + text + "新增模板" CTA button | `templates_list.html` |
| Submission review (no submissions) | No submissions for the date | **None** — No explicit empty state | `submission_review.html` |
| Attendance (no students) | Class has no members | **None** — No explicit empty state | `attendance_manage.html` |
| Leaderboard (no data) | Leaderboard disabled or empty | **Poor** — Lock icon + "尚未開放" text | `leaderboard.html` |
| Admin users (no users) | Impossible state (admin exists) | N/A | — |
| Points manage (no transactions) | No point transactions yet | **Poor** — Text only | `points_manage.html` |

### Issue C3: Dashboard Empty State Doesn't Guide Users [HIGH]

**Evidence**: `student/dashboard.html:256-259`:
```html
<div class="bg-white dark:bg-gray-900 rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-10 text-center">
  <p class="text-sm text-gray-500 dark:text-gray-400">尚未加入任何班級。</p>
</div>
```

**Problems**:
1. No icon or illustration
2. No explanation of what to do next
3. No CTA button ("加入班級" button is above this card, in a separate section)
4. Same text for both student and teacher roles — but the action is different (student: join class; teacher: create class)

**Recommended empty state for students**:
```
  [Illustration: person joining a group]
  尚未加入任何班級
  向老師索取邀請碼，或搜尋公開班級
  [加入班級] button
```

**Recommended empty state for teachers**:
```
  [Illustration: chalkboard]
  尚未建立任何班級
  建立您的第一個班級，開始管理學生每日練習
  [建立班級] button
```

### Issue C4: First-Time User Experience (FTUX) Missing [HIGH]

**Evidence**: No onboarding flow exists anywhere in the system. After setup wizard completes:

1. Admin creates the first user accounts
2. Students receive credentials (presumably offline)
3. Students log in to... a completely empty dashboard
4. No tutorial, no walkthrough, no "getting started" guide
5. Students must figure out: "How do I join a class?" "Where do I submit tasks?" "What are badges?"

**Specific gaps**:
- No "Welcome! Here's how to get started" message for first login
- No tooltips or hints on key UI elements
- No progress indicator ("Set up your profile → Join a class → Complete your first task")
- No sample/demo class for new teachers

### Issue C5: Empty Submission Review Has No Feedback [MEDIUM]

**Evidence**: `teacher/submission_review.html:54`:
```html
{% if students %}
<div id="submissions-list" class="space-y-3">
  ...
{% else %}
  {# No explicit empty state #}
{% endif %}
```

When there are no students/submissions for the selected date:
- Filter tabs still show (pending/approved/rejected/all)
- "Pending" count badge shows "0"
- Below the tabs: nothing — blank white space

**Recommended**:
```
  [Illustration: inbox empty]
  今天沒有待審作業
  學生提交後會顯示在這裡
```

---

## Microcopy Quality

### Positive Examples

| Location | Microcopy | Assessment |
|----------|-----------|------------|
| `dashboard.html:11` | "今天也繼續加油吧！" | Warm, motivational — good for student engagement |
| `feed.html:73` | "還沒有人分享，快來第一個分享你的作業吧！" | Encouraging, action-oriented |
| `class_hub.html:33` | "學生輸入即可加入" | Clear, concise instruction |
| `submit_task.html:37` | "獲得 N 積分" | Immediate reward feedback |

### Areas for Improvement

| Location | Current | Issue |
|----------|---------|-------|
| `login.html` | No "forgot password" link | Users who forget credentials have no self-service path |
| `setup.html` | "系統初始化設定" | Technical; could be "歡迎！讓我們設定您的學習平台" |
| `settings.html:8` | "管理您的帳號顯示名稱與密碼" | Accurate but dry — could mention what else is here |
| Error messages | Generic `{{ error }}` from server | No friendly wrapping; raw server messages shown directly |
| `submission_rejection.html` | Shows rejection reason as-is | No empathetic framing ("老師有一些建議：") |

### Issue C6: Error Messages Are Raw Server Text [MEDIUM]

**Evidence**: Throughout the system, error messages from the backend are displayed directly:

`login.html:23`:
```html
<p class="text-sm text-red-700 dark:text-red-400">{{ error }}</p>
```

If the backend returns `"Invalid credentials"`, the user sees exactly that (or its Chinese translation, depending on the endpoint). No:
- User-friendly wrapping
- Suggestion of what to do
- Distinction between "wrong password" and "user not found" (which is intentional for security, but the generic message could still be friendlier)

**Recommendation**: Backend error messages should be error codes. Frontend templates should map codes to user-friendly messages:
```python
ERROR_MESSAGES = {
  "invalid_credentials": "帳號或密碼錯誤，請確認後重試",
  "rate_limited": "操作太頻繁，請稍後再試",
  "already_submitted": "今天已經繳交過了",
}
```

---

## Information Density

### Issue C7: Dashboard Information Density Imbalance [MEDIUM]

**Student Dashboard**: 4 stat cards + badge strip + task list + activity sidebar = high density, well-organized

**Teacher Dashboard**: N stat cards (one per class, showing member count only) + class management cards with tool links

**Problem**: The teacher dashboard shows **the same information twice** — the stat card grid shows member counts, and the class cards below also show "N 位學生". Meanwhile, the most important information for teachers (pending submissions count, today's check-in rate) is **inside the Class Hub**, not on the dashboard.

**Evidence**: `student/dashboard.html:19-33` (teacher widget grid) shows one card per class with member count. Then lines 211-254 show class cards with the same member count plus tool links.

**Recommendation**: Teacher dashboard stat cards should show:
1. Total pending submissions (across all classes)
2. Today's aggregate check-in rate
3. Unreviewed join requests
4. Recent badge awards

Not just member counts repeated.

---

## Help & Documentation

### Issue C8: No Contextual Help [LOW]

**Evidence**: No template contains:
- Tooltip elements (`title="..."` on buttons with unclear purpose — except invite code button)
- Help icons (? circles)
- Links to documentation
- "Learn more" links

**Specific needs**:
- `template_assign.html`: Schedule modes (once/range/weekday/open) need explanations
- `trigger-rules.html`: DSL syntax needs in-page reference (partially addressed by WASM autocomplete)
- `admin/user_form.html`: Permission flags need descriptions
- `points_manage.html`: Point transaction sources need explanation

### Issue C9: No Feedback Collection Mechanism [LOW]

No template includes:
- Bug report link
- Feature request mechanism
- User satisfaction survey
- "Is this helpful?" on help content
- Contact admin/support link (beyond admin email in system settings)

---

## Summary

| Issue ID | Title | Severity |
|----------|-------|----------|
| C1 | "任務" vs "作業" inconsistency | LOW |
| C2 | "審查" vs "確認" for approval | LOW |
| C3 | Dashboard empty state doesn't guide users | HIGH |
| C4 | First-time user experience missing | HIGH |
| C5 | Empty submission review has no feedback | MEDIUM |
| C6 | Error messages are raw server text | MEDIUM |
| C7 | Dashboard information density imbalance | MEDIUM |
| C8 | No contextual help | LOW |
| C9 | No feedback collection mechanism | LOW |
