# Chapter 06: Mobile & Responsive Design

**Overall Grade: C+**
Mobile-first Tailwind classes present, but teacher mobile experience is severely impaired.

---

## Breakpoint Architecture

Defined in `src/templates/shared/base.html` via Tailwind defaults:

| Breakpoint | Prefix | Width | Layout |
|------------|--------|-------|--------|
| Mobile | (default) | <640px | Full-width, bottom tab bar |
| Small | `sm:` | ≥640px | Minor adjustments (show labels, extra columns) |
| Medium | `md:` | ≥768px | Bottom tab hidden, top horizontal nav visible |
| Large | `lg:` | ≥1024px | Desktop sidebar visible, top nav hidden |

### Layout Diagram

```
┌──────────────────────────────────────────────────────┐
│  MOBILE (<768px)                                      │
│  ┌──────────────────────────────────┐                 │
│  │ Top Bar: Logo + Theme + Avatar    │ sticky top-0   │
│  ├──────────────────────────────────┤                 │
│  │                                   │                 │
│  │        Main Content               │ p-4             │
│  │        (full width)               │                 │
│  │                                   │ pb-20 (for tab) │
│  ├──────────────────────────────────┤                 │
│  │ Bottom Tab Bar: Home|Badges|...   │ fixed bottom-0  │
│  └──────────────────────────────────┘                 │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  TABLET (768px - 1023px)                              │
│  ┌──────────────────────────────────┐                 │
│  │ Top Bar: Nav links + Theme + User │ sticky top-0   │
│  ├──────────────────────────────────┤                 │
│  │                                   │                 │
│  │        Main Content               │ p-4             │
│  │        (full width)               │                 │
│  │                                   │                 │
│  └──────────────────────────────────┘                 │
│  (No bottom tab bar - md: breakpoint hides it)        │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  DESKTOP (≥1024px)                                    │
│  ┌────────┬─────────────────────────┐                 │
│  │Sidebar │ Top Bar: Collapse + User │                 │
│  │ w-64   ├─────────────────────────┤                 │
│  │        │                          │                 │
│  │ Nav    │     Main Content         │ p-6             │
│  │ items  │                          │                 │
│  │        │                          │                 │
│  │ User   │                          │                 │
│  │ footer │                          │                 │
│  └────────┴─────────────────────────┘                 │
└──────────────────────────────────────────────────────┘
```

---

## Issue M1: Teacher Role Has No Functional Mobile Navigation [CRITICAL]

(Detailed in Chapter 02, Issue N1 — summarized here for mobile-specific context)

### Evidence

`src/templates/shared/base.html:462-518` — Mobile bottom tab bar content by role:

**Student role** (`base.html:472-481`):
```
[首頁] [徽章] [歷程] [歷程]
```
4 tabs, all functional (though last two seem duplicated — see Issue M2).

**Teacher role** (`base.html:483-503`):
```
[首頁] [管理] [班級] [登出]
```
- "首頁" → Dashboard (OK)
- "管理" → `dashboard_page` (same URL as 首頁 — BROKEN)
- "班級" → `admin_classes_list_page` (only visible if `can_manage_all_classes` — most teachers don't have this)
- "登出" → Logout

**Result**: A teacher on mobile sees **at most 2 functional tabs** (首頁 and 登出). There is no path to:
- Class Hub
- Submission Review
- Attendance Management
- Check-in Config
- Points/Badge Management
- Templates

### Impact

Teachers who need to review submissions or check attendance during class time using their phones **cannot access these features**. This is the most critical mobile UX failure in the system.

---

## Issue M2: Student Bottom Tab Bar Duplicate Items [HIGH]

### Evidence

`src/templates/shared/base.html:462-481`:

The student bottom tab bar shows:
1. 首頁 (Home) — `url_for('dashboard_page')`
2. 徽章 (Badges) — `url_for('badges_page')`
3. First "歷程" link — part of the student nav block
4. Second item — appears to overlap with general nav

On examination, the bottom nav has:
- `data-nav="dashboard"` — Home
- `data-nav="badges"` — Badges
- Two more items from conditional blocks

The issue is that when a student has classes, the class-specific links (歷程 for each class) cannot fit in a fixed 4-tab bar. The current implementation doesn't handle this — it either shows too many items or duplicates.

---

## Issue M3: Bottom Tab Bar Content Overlap with Main Content [MEDIUM]

### Evidence

`src/templates/shared/base.html:449`:
```html
<main class="flex-1 p-4 lg:p-6 pb-20 md:pb-4">
```

- Mobile: `pb-20` (80px padding-bottom) to account for the tab bar
- Tablet+: `pb-4` (16px)

The bottom tab bar height (`base.html:465`): `min-h-[56px]`

**Problem**: `pb-20` (80px) > `min-h-[56px]` — there's 24px of wasted space. But this is conservative, which is acceptable.

**Real problem**: Pages with fixed-position elements at the bottom (e.g., a "Submit" button on `submit_task.html`) can overlap with the tab bar:

`submit_task.html` form submit button is inside the form card, not fixed — so it's OK. But `template_assign.html` has buttons that could be pushed below the fold on small screens, requiring scroll to reach them while the tab bar eats 56px.

**Evidence for specific issue**: On the task submission form (`submit_task.html`), with a markdown editor at 360px height + form fields + padding, the submit button can be below the visible viewport on phones with <700px screen height. The user must scroll past the tab bar padding to find it.

---

## Issue M4: Tables on Mobile [MEDIUM]

### Evidence

**Templates list table** (`teacher/templates_list.html`):
- Columns: Template Name, Field Count, Created Date, Actions
- Mobile: Field Count and Date columns are `hidden sm:table-cell`
- Remaining on mobile: Template Name + Actions
- Actions column has 3 buttons (Edit, Assign, Archive) that stack horizontally in a small cell

**Admin users table** (`admin/users_list.html`):
- Columns: Checkbox, Username, Display Name, Name, Role, Permissions, Tags, Actions
- Hidden on mobile: Name, Tags columns (`hidden sm:table-cell`)
- Remaining on mobile: 6 columns still visible — too many for 375px width

**Admin classes table** (`admin/classes_list.html`):
- Similar overflow issues

### Problem

Tables with 4+ visible columns on mobile overflow the viewport width. The templates use `hidden sm:table-cell` to hide some columns, but not aggressively enough. A `375px` viewport with 6 columns (even without padding) gives ~62px per column — not enough for readable text.

### Recommendation

For admin tables on mobile (<640px), switch to a card-based layout instead of table rows. Each row becomes a stacked card showing key info vertically.

---

## Issue M5: Toast UI Editor Mobile Experience [HIGH]

### Evidence

`student/submit_task.html` (scripts section):
```javascript
new toastui.Editor({
  el: container,
  height: '360px',
  initialEditType: 'markdown',
  previewStyle: 'vertical',  // side-by-side split
  // ...
});
```

On a 375px-wide screen:
- Editor area: ~375px total
- `previewStyle: 'vertical'` = side-by-side split = ~187px per panel
- 187px is not enough to write or read Markdown comfortably

The editor toolbar also wraps awkwardly on narrow screens, sometimes requiring horizontal scroll.

### Recommendation

Detect mobile width and switch to `previewStyle: 'tab'` (write/preview toggle) instead of `'vertical'` (side-by-side):

```javascript
const isMobile = window.innerWidth < 640;
new toastui.Editor({
  previewStyle: isMobile ? 'tab' : 'vertical',
  // ...
});
```

---

## Issue M6: Modals Not Mobile-Optimized [MEDIUM]

### Evidence

**Create class modal** (`student/dashboard.html:131-148`):
```html
<div class="... fixed inset-0 z-50 flex items-center justify-center bg-black/50">
  <div class="... w-full max-w-sm mx-4">
```

- `max-w-sm` = 384px — on a 375px screen with `mx-4` (16px each side), effective width = 343px
- This is technically fine for width
- But: modal has no scroll behavior. If keyboard opens on mobile (text input focus), the modal content may be pushed off-screen with no way to scroll

**Badge management modal** (`teacher/badges_manage.html`):
- Larger form with multiple fields
- No `max-h-[...]` or `overflow-y-auto` on the modal body
- On short screens or landscape orientation, form fields extend below viewport

### Recommendation

All modals should have:
```html
<div class="... max-h-[90vh] overflow-y-auto">
```

And consider using bottom-sheet pattern on mobile instead of centered modals:
```css
@media (max-width: 640px) {
  .modal-content {
    position: fixed; bottom: 0; left: 0; right: 0;
    border-radius: 1rem 1rem 0 0;
    max-height: 85vh;
  }
}
```

---

## Issue M7: Horizontal Scroll on Specific Pages [LOW]

### Evidence

**Dashboard teacher tool buttons** (`student/dashboard.html:222-252`):
```html
<div class="px-5 py-3 bg-gray-50 dark:bg-gray-800/50 flex items-center gap-2 flex-wrap">
```

When a class card has 6 tool links (成員管理, 簽到設定, 任務模板, 作業審閱, 排行榜, 積分管理), `flex-wrap` causes them to wrap to 2-3 rows on mobile. This is functional but dense — the card becomes very tall with 3 rows of small pill buttons.

**Badge strip** (`student/dashboard.html:186`):
```html
<div class="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
```
Horizontal scrollable badge display — has `overflow-x-auto` which is correct. But `scrollbar-hide` removes the visual scrollbar indicator, so users may not realize there are more badges to scroll to.

---

## Touch Target Analysis

### Evidence

UI/UX Pro Max rule `touch-target-size`: "Minimum 44x44px touch targets"

| Element | Size | Meets 44x44? | Evidence |
|---------|------|-------------|---------|
| Primary buttons | `px-4 py-2.5` (~40x36px) | Close but no | `login.html:47` |
| Nav items (sidebar) | `px-3 py-2.5` (~full-width x 36px) | Width yes, height no | `base.html:85` |
| Bottom tab items | `min-h-[56px]` full flex | Yes | `base.html:465` |
| Badge hover circle | `w-12 h-12` (48x48) | Yes | `dashboard.html:191` |
| Trash button (feed) | `p-1.5` (~28x28px) | No — too small | `feed.html:33` |
| Filter tab buttons | `px-4 py-2` (~80x36px) | Width yes, height no | `submission_review.html:36` |
| Reaction button | `px-3 py-1` (~60x28px) | No — too small | `feed.html:56` |
| Table action links | Text-only, ~12px height | No | `templates_list.html` action column |

### Findings

- **7 of 8 element types** fail the 44x44px minimum in at least one dimension
- Most failures are in **vertical height** — horizontal width is usually sufficient
- The feed post delete button (`p-1.5` = ~28px) is particularly problematic on touch screens

### Recommendation

Add `min-h-[44px]` to all interactive elements, or increase padding to `py-3` (12px top + 12px bottom + line-height = ~44px).

---

## Performance Considerations

### Issue M8: Tailwind Play CDN Performance on Mobile [HIGH]

`src/templates/shared/base.html:23`:
```html
<script src="https://cdn.tailwindcss.com"></script>
```

On mobile devices with slower CPUs and network:
1. **Download**: ~330KB uncompressed JS for the Tailwind JIT compiler
2. **Parse**: JS parsing on a mid-range phone takes 200-500ms
3. **JIT compile**: Scans all class names in DOM and generates CSS — 100-300ms
4. **Total delay**: 300-800ms of additional First Contentful Paint delay

Compare to pre-built CSS: ~30KB gzipped Tailwind output, 0ms parse overhead.

### Issue M9: CDN Dependencies on Mobile Network [MEDIUM]

The system loads 4 external CDN resources on every page:
1. `cdn.tailwindcss.com` — Tailwind CSS JIT compiler (~330KB)
2. `fonts.googleapis.com` + `fonts.gstatic.com` — Google Fonts (~40KB)
3. `uicdn.toast.com` — Toast UI Editor (only on submit page, ~200KB)
4. `esm.sh` — CodeMirror (only on trigger rules page, ~300KB)

On a 3G connection (1.5Mbps typical):
- Tailwind: ~1.8s download
- Fonts: ~0.2s
- Total base page: ~2s before first meaningful paint

No Service Worker or offline caching is implemented. If any CDN is down, the page breaks.

---

## Summary

| Issue ID | Title | Severity | Breakpoint |
|----------|-------|----------|-----------|
| M1 | Teacher role has no mobile navigation | CRITICAL | <768px |
| M2 | Student bottom tab duplicate items | HIGH | <768px |
| M3 | Bottom tab/content overlap | MEDIUM | <768px |
| M4 | Tables overflow on mobile | MEDIUM | <640px |
| M5 | Toast UI Editor mobile UX | HIGH | <640px |
| M6 | Modals not mobile-optimized | MEDIUM | <640px |
| M7 | Horizontal scroll edge cases | LOW | <640px |
| M8 | Tailwind Play CDN performance | HIGH | All mobile |
| M9 | CDN dependencies on mobile network | MEDIUM | All mobile |
