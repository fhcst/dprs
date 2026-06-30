# Chapter 03: Role-Based Workflow Analysis

**Overall Grade: C+**
Workflows function but lack feedback loops, shortcuts, and progressive disclosure.

---

## Role 1: Student

### Primary Workflows

#### Workflow S1: Daily Check-in

```
Dashboard → Find class card → Click "簽到" button → Page reload with success
```

**Evidence**: `student/dashboard.html:297-300`:
```html
<form method="post" action="{{ url_for('checkin_browser', class_id=c.class_id) }}">
  <button type="submit" class="... bg-green-600 hover:bg-green-700 ...">
    <svg ...>✓</svg> 簽到
  </button>
</form>
```

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **No loading state on submit** — Button doesn't disable or show spinner during POST. On slow connections, users may double-click. | HIGH | Line 298: No `onclick` disable handler |
| **Full page reload** — Check-in is a standard form POST (PRG pattern via `checkin_browser`). The entire dashboard reloads instead of in-place update. | MEDIUM | Router: `src/tasks/checkin/router.py` — `checkin_browser` redirects back |
| **No countdown to window close** — If check-in window closes in 5 minutes, there's no visual countdown. Student sees "簽到" button then suddenly "已結束" without warning. | MEDIUM | `dashboard.html:296-320` — static status, no timer |
| **Missed check-in has no recovery path** — If a student misses the window, there is no "request late check-in" option. They must ask the teacher verbally. | LOW | No UI for student-initiated correction request |

#### Workflow S2: Task Submission

```
Dashboard → Find class card → Click "去繳交" → Fill form → Submit → Success message
```

**Evidence**: `student/submit_task.html:68-80` — Dynamic form rendering based on template fields.

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **No autosave / draft** — If the browser crashes mid-writing, all content is lost. Markdown fields (Toast UI Editor) can contain substantial text. | HIGH | `submit_task.html:70` — Standard `<form>` with no localStorage draft |
| **Success message lacks next-step guidance** — After submission, student sees "任務提交成功！獲得 N 積分" but no link to "查看其他任務" or "回到儀表板". | MEDIUM | `submit_task.html:29-41` — Static success div, no CTA buttons |
| **Toast UI Editor mobile UX** — `previewStyle: 'vertical'` creates side-by-side split view. On mobile (<640px), each panel gets ~160px width — barely usable. | HIGH | `submit_task.html` scripts section — editor config has fixed `previewStyle: 'vertical'` |
| **No character count / word count** — For text and markdown fields, there's no indication of expected length or current count. | LOW | Fields render without `maxlength` or counter UI |

#### Workflow S3: Resubmission After Rejection

```
Dashboard → "被退回" indicator → Click → submission_rejection.html →
"重新繳交" → submit_task.html (empty form)
```

**Evidence**: `student/submission_rejection.html` shows rejection reason and deadline. The "重新繳交" button links to `submit_task.html`.

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **Previous content not pre-filled** — When a student resubmits, the form is blank. They must retype everything, even fields that were acceptable. | HIGH | `submit_task.html:70` — Form always renders empty `{% for field in template.fields %}` without checking for previous values |
| **No diff view** — Student cannot see what they submitted before alongside the rejection reason while editing. | MEDIUM | `submission_rejection.html` and `submit_task.html` are separate pages |
| **Deadline display is absolute datetime** — Shows "2026-04-10 23:59" but no relative ("還有 2 天") or urgency coloring. | LOW | `submit_task.html:62` — `strftime('%Y-%m-%d %H:%M')` only |

#### Workflow S4: Viewing Learning History

```
Dashboard → [Sidebar] 學習歷程 → learning_history.html (all classes)
   or
Dashboard → [Sidebar] {class_name} → class_history.html (single class)
```

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **No filtering or search** — History pages show a flat timeline with no date filter, status filter, or search. A student with 100+ submissions must scroll endlessly. | HIGH | `learning_history.html` and `class_history.html` — no filter UI |
| **No pagination** — All submissions loaded in one page. Performance degrades with history volume. | MEDIUM | Both templates render `{% for sub in submissions %}` without pagination |
| **No data visualization** — Pure text timeline. No submission count chart, streak visualization, or progress indicators. | MEDIUM | No chart library included in these templates |

#### Workflow S5: Viewing Badges and Points

```
Dashboard → [Sidebar] 我的徽章 → badges.html
Dashboard → [Card] → Task card points display
```

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **No celebration moment** — When a badge is earned, nothing happens. No animation, no notification, no modal. The badge silently appears in the list. | MEDIUM | Badge award happens server-side (`badges/service.py`), no push mechanism to client |
| **Points balance is Dashboard-only** — Students can see total points on Dashboard stat card but have no detailed transaction history page from sidebar. Must navigate to class-specific points page. | MEDIUM | `student/dashboard.html:44-48` — Shows `stats.total_points` without link |
| **Badge page has placeholder "locked" badges** — `badges.html` shows skeleton badges as placeholders, but these are purely decorative and don't indicate "what badge can I earn next". | LOW | `badges.html` empty state section |

---

## Role 2: Teacher

### Primary Workflows

#### Workflow T1: Reviewing Submissions (Most Critical Daily Task)

```
Dashboard → [Sidebar dropdown] Select class → Class Hub →
[Tool card or sidebar] 任務審查 → submission_review.html →
Review each submission → Approve/Reject/Comment
```

**Evidence**: `teacher/submission_review.html:54-80` — Flat card list with filter tabs.

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **3+ clicks from login to first review action** — Dashboard → sidebar class dropdown → select class → sidebar "任務審查". Should be 1 click for the most frequent teacher task. | HIGH | Navigation analysis in Chapter 02 |
| **No batch operations** — Teacher must approve/reject one submission at a time. For a class of 30 students submitting daily, this means 30 individual clicks minimum. | HIGH | `submission_review.html` — Each card has individual Approve/Reject buttons, no "Select all pending → Approve" |
| **No date navigation** — Review page shows today's submissions only (based on `date` query param). No calendar picker or "previous day / next day" navigation. | MEDIUM | Router: `src/tasks/submissions/router.py` — `date` param defaults to today |
| **Toast notification position conflicts with filter tabs** — `submission_review.html:21`: Toast container is `fixed top-4 right-4`, which overlaps the filter tab area when scrolled to top. | LOW | Visual overlap, no z-index conflict but confusing placement |

#### Workflow T2: Managing Attendance

```
Dashboard → Class Hub → [Sidebar] 出席紀錄 → attendance_manage.html →
Select date → View student list → Mark late / Revoke
```

**Evidence**: `teacher/attendance_manage.html` — Date picker + student list.

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **No bulk late marking** — Must mark each student individually as "late" with partial points. For 10 late students, that's 10 modal interactions. | MEDIUM | Individual correction per student row |
| **No visual calendar view** — Attendance is viewed one day at a time via date picker. No weekly/monthly calendar view showing patterns. | MEDIUM | Single `<input type="date">` control |
| **No export** — Attendance data cannot be exported to CSV for grade books or parent reports. | LOW | No export button in template |

#### Workflow T3: Creating and Assigning Task Templates

```
Class Hub → [Sidebar] 任務模板 → templates_list.html →
新增模板 → template_form.html → Save →
templates_list.html → 指派 → template_assign.html → Configure schedule
```

**Evidence**: `teacher/template_form.html` — Dynamic field builder. `teacher/template_assign.html` — Schedule rule creation.

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **Schedule mode UX is confusing** — 4 modes (once/range/weekday/open) with similar button styling. Mode switching hides/shows form sections, but there's no visual explanation of what each mode does. | HIGH | `template_assign.html` — Mode buttons are styled identically with no description text |
| **No preview** — Teacher cannot preview what the student will see before publishing a template. | MEDIUM | `template_form.html` — Save-only, no preview button |
| **No template duplication** — To create a similar template, teacher must recreate from scratch. No "duplicate" action in templates_list.html. | LOW | `templates_list.html` — Actions are Edit, Assign, Archive only |

#### Workflow T4: Managing Class Members

```
Class Hub → [Sidebar] 成員管理 → class_members.html →
View pending join requests → Approve/Reject
Batch invite students → Search/Select → Invite
```

**Evidence**: `teacher/class_members.html` — Two-column layout with batch invite and member list.

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **Batch invite lazy loading is opaque** — Student list loads via JS fetch after page render. Before loading completes, the section appears empty with no loading indicator. | MEDIUM | `class_members.html` — JS loads student list after DOM ready |
| **Join request approval/rejection is per-request** — No batch approval for multiple pending requests. | LOW | Individual review per request |

#### Workflow T5: Points and Badge Management

**Points** (`teacher/points_manage.html`):
- Point deduction requires selecting student, entering amount, entering reason
- No bulk point operations
- Transaction history is read-only with no filtering

**Badges** (`teacher/badges_manage.html`):
- Badge creation uses emoji picker (text input for emoji) — discussed in Chapter 01, Issue A7
- Manual award requires selecting student from list
- No badge templates or presets

---

## Role 3: Site Admin

### Primary Workflows

#### Workflow A1: User Management

```
Admin Panel → 使用者管理 → users_list.html →
[New user / Edit user / Bulk actions]
```

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **CSV import has no preview** — File upload triggers immediate import. No "preview these 50 users before committing" step. Errors are reported after the fact. | HIGH | `admin/users_list.html` — Hidden file input triggers direct upload |
| **Permission matrix is raw IntFlag** — `admin/user_form.html` presents permissions as checkboxes with technical names like `MANAGE_OWN_CLASS`. No tooltip or explanation of what each permission enables. | MEDIUM | `user_form.html` — Permission checkboxes use flag names directly |
| **No search in user list** — Users table has pagination but no search input. Finding a specific student among hundreds requires paging through. | HIGH | `admin/users_list.html` — No search input visible |
| **No user activity summary** — Admin cannot see when a user last logged in, their submission count, or activity status. | LOW | User table columns: Username, Display Name, Name, Role, Permissions, Tags |

#### Workflow A2: System Configuration

```
Admin Panel → 系統設定 → system_settings.html →
Edit site name / admin email / cooldown hours → Save
```

**Issues Found**:

| Issue | Severity | Evidence |
|-------|----------|---------|
| **Very limited settings** — Only 3 fields: site name, admin email, cooldown hours. No branding customization, no feature flags, no SMTP configuration. | MEDIUM | `admin/system_settings.html` — 3 input fields |
| **No confirmation for settings changes** — Pressing "Save" immediately applies. No "Are you sure?" for potentially disruptive changes like site name. | LOW | Standard form POST, no confirmation |

---

## Cross-Role Issue: Notification Void

**Severity: HIGH**

No role has any in-app notification mechanism. This is the single biggest UX gap across the entire system.

### Evidence

Automated search for "notification", "notify", "alert" (in context of push/real-time), "websocket", "SSE", "event-source" across all templates and router files: **zero results**.

### Impact by Role

| Role | Missing Notification | Current Workaround |
|------|---------------------|-------------------|
| Student | Submission approved/rejected | Must manually check history page |
| Student | Badge earned | Must manually check badges page |
| Student | Join request approved/rejected | Must manually check dashboard |
| Teacher | New submission awaiting review | Must manually check review page |
| Teacher | New join request | Must manually check members page |
| Admin | System events (new user, errors) | Must manually check admin panel |

### Minimum Viable Notification

At minimum, the Dashboard should show a "pending actions" count:
- Student: "1 份作業被退回需要重交"
- Teacher: "5 份作業待審閱" + "2 個加入申請待處理"
- Admin: (lower priority)

This can be implemented server-side (query on Dashboard page load) without WebSocket infrastructure.
