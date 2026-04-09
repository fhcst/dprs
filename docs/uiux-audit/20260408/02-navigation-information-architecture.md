# Chapter 02: Navigation & Information Architecture

**Overall Grade: B-**
Desktop navigation is solid; mobile and tablet have significant gaps.

---

## System Navigation Map

```
                          ┌─────────────────────────┐
                          │       Login Page         │
                          │   src/templates/login.html│
                          └───────────┬─────────────┘
                                      │ POST /pages/login
                                      ▼
                   ┌──────────────────────────────────────┐
                   │            Dashboard                  │
                   │   src/templates/student/dashboard.html │
                   │   (shared by all roles)                │
                   └──┬──────────┬──────────┬─────────────┘
                      │          │          │
            ┌─────────▼──┐ ┌────▼────┐ ┌───▼──────────┐
            │  Student    │ │ Teacher │ │  Admin        │
            │  Workflow   │ │Workflow │ │  Workflow     │
            └─────────────┘ └─────────┘ └──────────────┘
```

### Student Navigation Paths

```
Dashboard
├── [Sidebar] 儀表板 (Dashboard)
├── [Sidebar] 我的徽章 (My Badges) → badges.html
├── [Sidebar] 學習歷程 (Learning History) → learning_history.html
├── [Sidebar] 我的班級
│   └── {class_name} → class_history.html
│       ├── 任務歷程 (Task History)
│       └── 積分排行 (Leaderboard) → leaderboard.html
├── [Dashboard Card] 簽到 (Check-in) → POST form
├── [Dashboard Card] 去繳交 (Submit Task) → submit_task.html
├── [Dashboard Action] 加入班級 (Join Class) → Modal
├── [Top Bar] 個人設定 (Settings) → settings.html
└── [Top Bar/Bottom] 登出 (Logout)
```

### Teacher Navigation Paths

```
Dashboard
├── [Sidebar] 儀表板 (Dashboard)
├── [Sidebar] 班級管理
│   └── [Dropdown] 選擇班級 → class_hub.html
│       ├── 成員管理 → class_members.html
│       ├── 任務模板 → templates_list.html
│       │   ├── 新增模板 → template_form.html
│       │   ├── 編輯模板 → template_form.html
│       │   └── 指派模板 → template_assign.html
│       ├── 任務審查 → submission_review.html
│       ├── 簽到設定 → checkin_config.html
│       ├── 出席紀錄 → attendance_manage.html
│       ├── 排行榜 → leaderboard.html
│       ├── 積分管理 → points_manage.html
│       └── 徽章管理 → badges_manage.html
├── [Sidebar] 新增班級 → Dashboard?create_class=1
├── [Sidebar] 平台管理 (if admin)
│   └── 管理後台 → admin/index.html
└── [Top Bar] Settings / Logout
```

### Admin Navigation Paths

```
Admin Panel (admin/layout.html tabs)
├── 概覽 (Overview) → admin/index.html
├── 使用者 (Users) → admin/users_list.html
│   ├── 新增使用者 → admin/user_form.html
│   ├── 編輯使用者 → admin/user_form.html
│   ├── CSV 匯入
│   └── CSV 匯出
├── 班級 (Classes) → admin/classes_list.html
│   ├── 封存/解除封存
│   └── 管理成員
└── 系統設定 (System) → admin/system_settings.html
```

---

## Issue N1: Teacher Mobile Bottom Tab Bar Is Non-Functional [CRITICAL]

### Evidence

`src/templates/shared/base.html:462-518` — Mobile bottom tab bar:

```html
<nav class="md:hidden fixed bottom-0 left-0 right-0 z-40 ...">
```

**Student view** (when `not can_manage_class and not can_manage_tasks`):
- 首頁 (Home) → Dashboard
- 徽章 (Badges) → badges page
- 歷程 (History) → learning history
- 歷程 (History) → **duplicate? or class history**

**Teacher view** (lines 483-503):
- 首頁 (Home) → Dashboard
- 管理 (Manage) → Dashboard (same URL!)
- 班級 (Classes) → admin classes page (only if `can_manage_all_classes`)
- 登出 (Logout)

### Problems

1. **"管理" tab links to Dashboard** (`base.html:484`) — `href="{{ url_for('dashboard_page') }}"`. This is the same destination as "首頁". The teacher mobile nav has two tabs pointing to the same page.

2. **No path to class management on mobile** — The sidebar's class selector dropdown (`base.html:165-210`) is `hidden` on mobile (it's inside `<aside class="hidden lg:flex">`). On tablet, the horizontal nav only shows class names. On mobile (<768px), there is **no way to navigate to**:
   - Class Hub
   - Submission Review
   - Attendance Management
   - Points/Badge Management

3. **Teacher must use desktop or memorize URLs** — The critical teacher workflow (review submissions, manage attendance) is completely inaccessible on mobile.

### Impact

Teachers commonly use phones during class (quick attendance check, approve a submission between activities). This audience is completely blocked on mobile.

### Recommendation

Redesign mobile bottom tab bar for teacher role:
```
┌──────┬──────┬──────┬──────┬──────┐
│ 首頁  │ 審閱  │ 出席  │ 班級  │ 更多  │
│ Home │Review│Attend│Class │ More │
└──────┴──────┴──────┴──────┴──────┘
```

Where "更多" opens a slide-up sheet with all remaining tools.

---

## Issue N2: Sidebar Collapse State Not Persisted [HIGH]

### Evidence

`src/templates/shared/base.html:537-551`:

```javascript
function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    var labels = sidebar.querySelectorAll('.sidebar-label');
    if (sidebar.classList.contains('w-64')) {
      sidebar.classList.remove('w-64');
      sidebar.classList.add('w-16');
      labels.forEach(function(el) { el.classList.add('hidden'); });
    } else {
      sidebar.classList.remove('w-16');
      sidebar.classList.add('w-64');
      labels.forEach(function(el) { el.classList.remove('hidden'); });
    }
}
```

No `localStorage.setItem()` call. Compare with dark mode toggle at `base.html:526-535` which correctly uses `localStorage.setItem('theme', ...)`.

### Impact

Every page navigation resets sidebar to expanded. Users who prefer collapsed sidebar must click the toggle on every page load. This is especially annoying for teachers who frequently navigate between management pages.

---

## Issue N3: Tablet Horizontal Nav Overflow [MEDIUM]

### Evidence

`src/templates/shared/base.html:366-394`:

```html
<nav class="hidden md:flex lg:hidden items-center gap-1 mr-auto">
```

This horizontal nav is shown at `md` breakpoint (768-1023px) and lists class names directly:

```html
{% for c in classes %}
<a href="..." class="nav-item px-3 py-1.5 rounded-lg text-sm ...">
  {{ c.class_name }}
</a>
{% endfor %}
```

### Problem

If a teacher manages 4+ classes, or classes have long names (e.g., "112學年度上學期國語文進階班"), the horizontal nav overflows. There is no `overflow-x-auto` or truncation. The nav items simply overflow off-screen.

### Recommendation

Add `overflow-x-auto` and `flex-nowrap` to the tablet nav, with `scrollbar-hide` for clean appearance.

---

## Issue N4: Breadcrumb Navigation Inconsistency [MEDIUM]

### Evidence

Breadcrumb usage across templates:

| Template | Has Breadcrumb | Implementation |
|----------|---------------|----------------|
| `teacher/submission_review.html` | Yes | `{% block breadcrumb %}` with full path |
| `teacher/class_hub.html` | Yes | Inline in content (not in breadcrumb block) |
| `teacher/template_form.html` | Yes | Inline link |
| `student/submit_task.html` | Partial | "返回儀表板" back link only |
| `student/class_history.html` | No | — |
| `student/learning_history.html` | No | — |
| `student/badges.html` | No | — |
| `community/leaderboard.html` | No | — |
| `community/feed.html` | No | — |
| `settings.html` | Partial | "返回儀表板" back link |
| All admin templates | No | Tab bar replaces breadcrumb |

### Problems

1. `base.html:451` defines a `{% block breadcrumb %}` block, but only `submission_review.html` uses it
2. Student pages have no way to navigate "up" — if you're on `class_history.html`, there's no breadcrumb to go back to Dashboard or the class list
3. `class_hub.html` implements breadcrumb inline (lines 7-13) instead of using the `{% block breadcrumb %}` block, creating inconsistent placement

---

## Issue N5: Class Selector Dropdown UX Problems [MEDIUM]

### Evidence

`src/templates/shared/base.html:165-210` — Class selector in sidebar:

### Problems

1. **No keyboard arrow navigation** — The dropdown is a list of `<a>` elements. Users can Tab through them, but Up/Down arrow keys don't work (standard `role="listbox"` behavior expected).

2. **Search input focus management** — `base.html:566`: `searchInput.focus()` is called when dropdown opens, which is good. But when dropdown closes, focus is not returned to the trigger button.

3. **No empty state** — If a teacher has no classes, the dropdown renders an empty container with no message.

4. **Click-outside behavior only** — `base.html:571-575`: Dropdown closes on click outside, but not on ESC key press.

5. **No visual indication of dropdown state from collapsed sidebar** — When sidebar is collapsed (`w-16`), the class selector button shows only the icon (label is `hidden`). Clicking it opens the dropdown but the dropdown is clipped by the narrow sidebar width.

---

## Issue N6: Admin Panel Navigation Isolation [LOW]

### Evidence

`src/templates/admin/layout.html` extends `base.html` and adds its own tab navigation:

```
Admin Panel
├── 概覽 (Overview)
├── 使用者管理 (Users)
├── 班級管理 (Classes)
└── 系統設定 (System)
```

### Problem

When inside the admin panel, the main sidebar still shows the teacher navigation. There is no visual distinction indicating "you are in admin mode". The admin tabs are inside the content area, making them feel like content rather than navigation.

More importantly, there is **no direct link from admin back to teacher view** other than clicking "儀表板" in the sidebar. For a Site Admin who is also a teacher, switching between admin and teaching contexts requires mental context-switching with no UI support.

### Recommendation

Consider adding a breadcrumb or visual indicator: "管理後台 > 使用者管理" and a prominent "返回教學模式" link.

---

## Navigation Depth Analysis

| Role | Deepest Path | Click Count | Assessment |
|------|-------------|-------------|------------|
| Student | Dashboard → Submit Task | 1-2 clicks | Good |
| Student | Dashboard → Class History → Submission Detail | 2-3 clicks | Acceptable |
| Teacher | Dashboard → Class Hub → Submission Review | 3 clicks | Too deep for primary task |
| Teacher | Dashboard → Class Hub → Templates → Create → Assign | 5 clicks | Acceptable for setup task |
| Admin | Dashboard → Admin → Users → Edit User | 3 clicks | Acceptable |

**Key finding**: The teacher's most frequent action (reviewing submissions) is 3 clicks from Dashboard. This should be **1 click** — a "N 份待審作業" badge on the Dashboard that links directly to the review page.
