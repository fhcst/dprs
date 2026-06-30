# Chapter 01: Accessibility (WCAG 2.1 AA Compliance)

**Overall Grade: FAIL**
**WCAG 2.1 AA violations found: 12**

This chapter documents all accessibility issues found during the audit. In an educational platform, accessibility is especially critical — students may include individuals with visual, motor, or cognitive disabilities.

---

## Issue A1: No `prefers-reduced-motion` Support [CRITICAL]

**WCAG Reference**: 2.3.3 Animation from Interactions (AAA), best practice for AA
**Occurrences**: 0 uses across all 27 templates

### Evidence

Automated search for `prefers-reduced-motion` across all `.html` files returned **zero results**.

Meanwhile, the codebase uses motion extensively:

| File | Line | Animation |
|------|------|-----------|
| `shared/base.html` | 69 | `transition-all duration-300` on sidebar collapse |
| `shared/base.html` | 85 | `transition-colors duration-150` on nav items (27+ instances) |
| `student/badges.html` | 191 | `transition-all duration-150` on badge hover |
| `community/feed.html` | 15 | `transition-shadow duration-200` on post cards |
| `student/dashboard.html` | 191 | `transition-all duration-150` on badge strip |
| `teacher/submission_review.html` | multiple | Filter tab transitions |

### Impact

Users with vestibular disorders (estimated 35% of adults over 40 experience some form) may experience motion sickness, dizziness, or nausea from:
- Sidebar collapse/expand animation (300ms `transition-all` — changes width + repositions all content)
- Badge hover animations
- Modal fade-in/out
- Card shadow transitions

### Recommendation

Add a global CSS rule in `base.html`:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## Issue A2: Missing Skip-to-Content Link [CRITICAL]

**WCAG Reference**: 2.4.1 Bypass Blocks (A)

### Evidence

`src/templates/shared/base.html:1-60` — The `<body>` tag at line 60 is immediately followed by the layout wrapper. There is no skip link.

The sidebar navigation (`base.html:82-314`) contains **15+ interactive elements** (nav links, class selector dropdown, sub-navigation items) that a keyboard user must Tab through before reaching main content.

### Impact

A keyboard-only user navigating the teacher dashboard must press Tab approximately **20-25 times** to reach the first interactive element in the page content. This is required on **every page load**.

### Recommendation

Add immediately after `<body>` in `base.html`:

```html
<a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-brand-600 focus:text-white focus:rounded-lg">
  Skip to main content
</a>
```

And add `id="main-content"` to the `<main>` tag at line 449.

---

## Issue A3: Modals Lack Proper ARIA Roles and Focus Management [CRITICAL]

**WCAG Reference**: 4.1.2 Name, Role, Value (A), 2.4.3 Focus Order (A)

### Evidence

**Create Class Modal** (`student/dashboard.html:131-148`):
```html
<div id="create-class-modal" class="hidden fixed inset-0 z-50 ...">
  <div class="bg-white ... p-6 w-full max-w-sm mx-4">
```

Issues found:
- No `role="dialog"` on the modal container
- No `aria-modal="true"`
- No `aria-labelledby` pointing to the modal title
- No focus trap — Tab key can navigate behind the modal to sidebar/header elements
- No ESC key handler to close
- No focus restoration — when modal closes, focus does not return to the trigger button

**Join Class Modal** (`student/dashboard.html:164-179`): Same issues.

**Global Modal utility** (`base.html` — Modal class in scripts section): The JS-based `Modal.confirm()` and `Modal.alert()` create dynamic overlays but do not implement:
- `role="alertdialog"` for confirmations
- `aria-describedby` for the message content
- Focus trap within the dialog
- Return focus to trigger on close

### Affected Templates

| Template | Modal Purpose | Has role="dialog" | Has focus trap | Has ESC close |
|----------|--------------|-------------------|----------------|---------------|
| `student/dashboard.html` | Create class | No | No | No |
| `student/dashboard.html` | Join class | No | No | No |
| `teacher/badges_manage.html` | Badge CRUD | No | No | Partial |
| `teacher/submission_review.html` | Reject panel | No | No | No |
| `base.html` (Modal class) | Confirm/Alert | No | No | No |

### Impact

- Screen reader users cannot identify modals as dialog regions
- Keyboard users can Tab behind the modal overlay, interacting with obscured elements
- No way to dismiss modal via keyboard (ESC)

---

## Issue A4: Insufficient ARIA Attributes Across Templates [HIGH]

**WCAG Reference**: 4.1.2 Name, Role, Value (A)

### Quantitative Evidence

Total `aria-*` and `role=` attribute occurrences across all 27 templates: **19**

Distribution:
| File | Count | What's Present |
|------|-------|---------------|
| `shared/base.html` | 8 | `aria-expanded`, `aria-haspopup`, `aria-label` (sidebar toggle, class dropdown) |
| `admin/classes_list.html` | 8 | `role="option"`, `aria-selected` (class list) |
| `teacher/template_assign.html` | 1 | — |
| `teacher/class_hub.html` | 1 | — |
| `teacher/badges_manage.html` | 1 | — |
| All other 22 templates | 0 | — |

### Missing ARIA Landmarks

The entire template set lacks:
- `role="navigation"` on the sidebar nav (line 82) — currently just a `<nav>` (acceptable as implicit)
- `role="main"` on content area — the `<main>` tag at line 449 provides this implicitly (acceptable)
- `role="banner"` on header — `<header>` provides this implicitly (acceptable)
- `role="alert"` on any error/success messages — **MISSING**
- `role="status"` on any dynamic status updates — **MISSING**
- `aria-live` regions on any template — **MISSING**

### Specific Missing Attributes

**Error/Success Alert Boxes** — Found in 8+ templates but none have `role="alert"`:

| Template | Line | Element |
|----------|------|---------|
| `login.html` | 19-25 | Error alert (login failure) |
| `settings.html` | 20-27 | Success banner |
| `settings.html` | 28-35 | Error banner |
| `submit_task.html` | 29-41 | Success message |
| `submit_task.html` | 44-51 | Error message |
| `setup.html` | various | Setup errors |

**Toast Notifications** — `submission_review.html:21`:
```html
<div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2 pointer-events-none"></div>
```
No `aria-live="polite"` or `role="status"`. Toasts are dynamically inserted via JS but invisible to screen readers.

**Status Badges** — Check-in status, submission status badges use color alone:
```html
<!-- student/dashboard.html:292 — green badge for "已簽到" -->
<span class="... bg-green-50 ... text-green-700 ...">已簽到</span>

<!-- No aria-label or sr-only text alternative when status changes dynamically -->
```

**Filter Tabs** — `submission_review.html:34-51`:
- No `role="tablist"` on the container
- No `role="tab"` on individual tabs
- No `aria-selected` state management
- No `aria-controls` linking tabs to content panels

---

## Issue A5: Tables Missing Accessibility Markup [HIGH]

**WCAG Reference**: 1.3.1 Info and Relationships (A)

### Evidence

**Admin Users Table** (`admin/users_list.html`):
- Has `<table>` but no `<caption>` or `aria-label`
- Column headers use `<th>` (good) but no `scope="col"`
- No `aria-sort` for sortable columns

**Templates List Table** (`teacher/templates_list.html`):
- Same issues as above
- Hidden columns on mobile (`hidden sm:table-cell`) have no `aria-label` alternative

**Attendance Table** (`teacher/attendance_manage.html`):
- Student status rows have no `aria-label` describing the row's semantic meaning
- Status badges (checked in / absent / late) conveyed only by color

**Leaderboard Table** (`community/leaderboard.html`):
- Rank column uses emoji medals (🥇🥈🥉) — screen readers read these as "first place medal" etc., which is acceptable, but the rest of the rank column (`4`, `5`, etc.) has no `aria-label` context

---

## Issue A6: Color as Sole Indicator [HIGH]

**WCAG Reference**: 1.4.1 Use of Color (A)

### Evidence

Status indicators throughout the system rely on color alone:

| Context | Colors Used | Text Label Present | Icon Present |
|---------|------------|-------------------|-------------|
| Submission status (pending) | Amber bg + text | Yes ("待審閱") | No |
| Submission status (approved) | Green bg + text | Yes ("已確認") | Yes (checkmark) |
| Submission status (rejected) | Red bg + text | Yes ("已退回") | Yes (X icon) |
| Check-in status (checked in) | Green badge | Yes ("已簽到") | Yes (checkmark) |
| Check-in status (not checked) | No badge shown | No — absence conveys status | No |
| Attendance (absent) | Red text | Yes ("缺席") | No icon |
| Attendance (late) | Amber text | Depends on context | No icon |
| Points (positive) | Green text | Number only (e.g., "+10") | No |
| Points (negative) | Red text | Number only (e.g., "-5") | No |

The **Points transaction display** is the worst offender — positive/negative amounts are distinguished **only by green/red text color** with no `+`/`-` prefix icon or text alternative for color-blind users.

### Recommendation

Add consistent icon + text pairing for all status states. Example for points:
- Positive: `↑ +10` with green
- Negative: `↓ -5` with red
- Both states also need `aria-label="獲得 10 積分"` / `aria-label="扣除 5 積分"`

---

## Issue A7: Badge Icons Use Emoji [MEDIUM]

**WCAG Reference**: 1.1.1 Non-text Content (A)

### Evidence

Badge display across templates:

`student/dashboard.html:192`:
```html
{{ defn.icon if defn else "🏅" }}
```

`student/badges.html` — Badge grid uses `defn.icon` which stores emoji strings from the database.

`teacher/badges_manage.html` — Badge creation allows teachers to input any emoji as the badge icon.

### Problems

1. **Cross-platform inconsistency**: Emoji render differently across Windows, macOS, iOS, Android, and Linux. A badge designed on macOS may look completely different on a student's Windows laptop.

2. **Screen reader behavior**: Screen readers announce emoji descriptions (e.g., "sports medal" for 🏅, "star" for ⭐). When used as the primary visual for a badge named "Perfect Attendance", the screen reader says "sports medal Perfect Attendance" — confusing semantic overlap.

3. **No fallback**: If emoji rendering fails (older browsers, terminal-based browsers), the badge becomes invisible.

### Recommendation

Replace emoji with SVG icon system. Provide a curated set of 20-30 education-themed SVG icons (book, star, trophy, flame, lightning, heart, checkmark, etc.) as selectable badge icons in `badges_manage.html`.

---

## Issue A8: Keyboard Navigation Gaps [MEDIUM]

**WCAG Reference**: 2.1.1 Keyboard (A), 2.4.7 Focus Visible (AA)

### Evidence

**Focus indicators present**: 80 occurrences of `focus:ring` across 19 templates — generally good coverage on form inputs.

**Gaps found**:

1. **Class selector dropdown** (`base.html:165-210`): Arrow key navigation not implemented. Users can Tab into the dropdown but cannot use Up/Down arrows to navigate options.

2. **Filter tabs** (`submission_review.html:34-51`): No arrow key navigation between tabs. Each tab is a `<button>`, so Tab works, but conventional tab widget behavior (Arrow Left/Right to switch) is missing.

3. **Badge strip** (`student/dashboard.html:186-198`): Horizontal scrollable container with no keyboard scroll mechanism. `overflow-x-auto` only responds to mouse scroll/touch swipe.

4. **Mobile bottom tab bar** (`base.html:462-518`): Tab items are `<a>` and `<button>` (keyboard accessible), but no `role="tablist"` / `role="tab"` semantics.

5. **Sidebar collapse toggle** (`base.html:397-404`): Has `aria-label="切換側邊欄"` (good), but collapsed state is not announced — no `aria-expanded` on the toggle button.

---

## Issue A9: Form Labels and Autocomplete [LOW]

**WCAG Reference**: 1.3.5 Identify Input Purpose (AA)

### Evidence

**Login form** (`login.html:33-44`):
- `autocomplete="username"` — correct
- `autocomplete="current-password"` — correct
- Labels with `for` attribute — correct

**Settings page** (`settings.html:82-116`):
- `autocomplete="current-password"` — correct
- `autocomplete="new-password"` — correct
- Labels with `for` attribute — correct

**Setup wizard** (`setup.html`):
- `autocomplete="username"` — correct
- `autocomplete="new-password"` — correct

**Missing autocomplete**:
- `admin/user_form.html` — Username and password fields for admin user creation lack `autocomplete` attributes
- `teacher/class_members.html` — Search input lacks `autocomplete="off"` (browser may show irrelevant suggestions)

### Assessment

Form labels and autocomplete are **generally well implemented** — this is one of the stronger accessibility areas. Minor gaps in admin forms.

---

## Summary Table

| Issue ID | Title | Severity | WCAG | Effort |
|----------|-------|----------|------|--------|
| A1 | No prefers-reduced-motion | CRITICAL | 2.3.3 | Low (1 CSS rule) |
| A2 | No skip-to-content link | CRITICAL | 2.4.1 | Low (2 lines HTML) |
| A3 | Modal ARIA + focus trap | CRITICAL | 4.1.2, 2.4.3 | Medium |
| A4 | Insufficient ARIA attributes | HIGH | 4.1.2 | Medium |
| A5 | Tables missing a11y markup | HIGH | 1.3.1 | Low |
| A6 | Color as sole indicator | HIGH | 1.4.1 | Medium |
| A7 | Emoji badge icons | MEDIUM | 1.1.1 | High (system change) |
| A8 | Keyboard navigation gaps | MEDIUM | 2.1.1 | Medium |
| A9 | Form labels/autocomplete | LOW | 1.3.5 | Low |
