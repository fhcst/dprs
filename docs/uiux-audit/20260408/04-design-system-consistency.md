# Chapter 04: Design System & Visual Consistency

**Overall Grade: B**
Strong visual foundation with inconsistencies in component patterns.

---

## Color System Analysis

### Brand Palette

Defined in `src/templates/shared/base.html:29-42`:

```javascript
brand: {
  50:  '#f5f3ff',
  100: '#ede9fe',
  200: '#ddd6fe',
  300: '#c4b5fd',
  400: '#a78bfa',
  500: '#8b5cf6',
  600: '#7c3aed',   // Primary action color
  700: '#6d28d9',   // Hover state
  800: '#5b21b6',
  900: '#4c1d95',
  950: '#2e1065',
}
```

### Color Usage Audit

| Purpose | Light Mode | Dark Mode | Assessment |
|---------|-----------|-----------|------------|
| Primary button | `bg-brand-600` | Same | Good — consistent |
| Primary button hover | `hover:bg-brand-700` | Same | Good |
| Link text | `text-brand-600` | `dark:text-brand-400` | Good |
| Active nav item | `bg-brand-50 text-brand-700` | `dark:bg-brand-900/30 dark:text-brand-300` | Good |
| Focus ring | `focus:ring-brand-500` | Same | Good |
| Success | `bg-green-50 text-green-700 border-green-200` | Dark variants | Good |
| Error | `bg-red-50 text-red-700 border-red-200` | Dark variants | Good |
| Warning | `bg-amber-50 text-amber-700 border-amber-200` | Dark variants | Good |
| Info | `bg-blue-50 text-blue-700` | Dark variants | Good |
| Body text | `text-gray-900` | `dark:text-gray-100` | Good |
| Muted text | `text-gray-500` | `dark:text-gray-400` | Good |
| Card background | `bg-white` | `dark:bg-gray-900` | Good |
| Page background | `bg-gray-50` | `dark:bg-gray-950` | Good |

### Color Issues

**Issue D1: brand-600 semantic overload** [LOW]

`brand-600` (#7c3aed) is used for:
- Primary action buttons (`bg-brand-600`)
- Active navigation items (`text-brand-700`)
- Link text (`text-brand-600`)
- Focus rings (`focus:ring-brand-500`)
- Badge backgrounds (badges with brand gradient)
- Stat card icons (`text-brand-600`)
- Filter tab active state (`bg-brand-600`)
- Avatar letter color (`text-brand-700`)

Everything purple blends together. There's no visual distinction between "this is clickable" and "this is decorative" when both use brand-600.

**Recommendation**: Use brand-600 only for primary CTA buttons. Use brand-500 for links, brand-100/brand-900 for decorative backgrounds.

**Issue D2: Inconsistent emerald vs green** [LOW]

`settings.html:21` uses `bg-emerald-50` for success messages, while all other templates use `bg-green-50`. Tailwind's emerald and green are different hues.

Evidence:
- `settings.html:21`: `bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700`
- `submit_task.html:30`: `bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800`
- `teacher/class_hub.html:74`: `bg-green-100 dark:bg-green-900/40`

---

## Typography Analysis

### Font Configuration

`base.html:44-47`:
```javascript
fontFamily: {
  heading: ['Poppins', 'sans-serif'],
  sans: ['Open Sans', 'sans-serif'],
}
```

Google Fonts loaded at `base.html:56`:
```
Poppins: wght@600;700
Open Sans: wght@400;600
```

### Typography Usage Audit

| Element | Font | Weight | Size | Line Height | Assessment |
|---------|------|--------|------|-------------|------------|
| Page heading (h1) | `font-heading` | `font-bold` (700) | `text-2xl` | Default | Good |
| Card heading (h2/h3) | `font-heading` | `font-semibold` (600) | `text-base` | Default | Good |
| Body text | `font-sans` (Open Sans) | Default (400) | `text-sm` | Default | See issue below |
| Muted text | `font-sans` | Default | `text-xs` | Default | Good |
| Stat numbers | `font-heading` | `font-bold` | `text-2xl` | Default | Good |
| Nav items | `font-sans` | `font-medium` | `text-sm` | Default | Good |
| Button text | `font-sans` | `font-medium` / `font-semibold` | `text-sm` | Default | Inconsistent — see below |
| Badge text | `font-sans` | `font-semibold` / `font-medium` | `text-xs` | Default | Inconsistent |
| Code/mono | Default monospace | `font-bold` | `text-lg` | Default | Invite code only |

### Typography Issues

**Issue D3: Body text `text-sm` (14px) as default** [MEDIUM]

Nearly all body text uses `text-sm` (14px). Tailwind's `text-sm` is 0.875rem = 14px. On mobile, this is below the recommended minimum of 16px (`text-base`).

Evidence — grep for `text-sm` returns 400+ occurrences across all templates. Examples:
- `login.html:33`: Form labels are `text-sm`
- `student/dashboard.html:30`: Class student count is `text-xs` (12px)
- `teacher/submission_review.html:76`: Submission metadata is `text-xs`

UI/UX Pro Max guideline `readable-font-size`: "Minimum 16px body text on mobile"

**Issue D4: Line height not explicitly set** [LOW]

No template uses explicit `leading-*` classes for body text. Tailwind's default line height for `text-sm` is `1.25rem` (1.43 ratio). The recommended range for body text is 1.5-1.75.

Evidence: grep for `leading-` returns only 3 occurrences:
- `base.html:78`: `leading-tight` on site name
- `base.html:426`: `leading-tight` on user display name
- `community/feed.html:44`: `leading-relaxed` on post content (good!)

Only `feed.html` applies proper line height for reading comfort.

**Issue D5: No max-width on content** [MEDIUM]

Most pages allow content to stretch to full viewport width. On a 1920px display, a teacher's submission review cards span nearly 1400px — far exceeding the recommended 65-75 characters per line.

Evidence:
- `submission_review.html:55`: `<div id="submissions-list" class="space-y-3">` — no `max-w-*`
- `student/dashboard.html:202`: `<div class="grid lg:grid-cols-3 gap-6">` — grid constrains somewhat but cards can still be very wide
- `community/feed.html:5`: `<div class="max-w-2xl mx-auto">` — **this is the only template that properly constrains width**
- `settings.html:37`: `<div class="max-w-2xl space-y-5">` — also good

Templates with proper `max-w-*`: `feed.html`, `settings.html`, `submit_task.html` (max-w-3xl)
Templates without: `submission_review.html`, `dashboard.html` (grid but no max), `templates_list.html`, `attendance_manage.html`, `points_manage.html`, all admin pages

---

## Component Consistency Audit

### Buttons

**Primary button pattern**:
```html
class="px-4 py-2 text-sm font-medium bg-brand-600 hover:bg-brand-700 text-white rounded-lg
       transition-colors duration-150 cursor-pointer"
```

**Evidence of inconsistencies**:

| Variant | Evidence | Issue |
|---------|----------|-------|
| Standard primary | `login.html:47`, `settings.html:87` | `rounded-lg`, consistent |
| Check-in button | `dashboard.html:298` | `rounded-full` — different radius |
| Filter tab active | `submission_review.html:36` | `rounded-lg bg-brand-600` — same as primary CTA |
| Badge pill | `dashboard.html:292` | `rounded-full` — badge styling, OK |
| Secondary button | `dashboard.html:143` | Inconsistent: some use `border border-gray-300`, others `bg-gray-100` |

**Issue D6: Primary button vs active tab visual conflict** [MEDIUM]

Both primary buttons and active filter tabs use `bg-brand-600 text-white rounded-lg`. A teacher on the submission review page sees the "待審閱" tab styled identically to CTA buttons, making it unclear what's a tab and what's a button.

Evidence:
- `submission_review.html:36`: Active tab: `bg-brand-600 text-white`
- `submission_review.html` (in card): Approve button: `bg-brand-600 text-white`

### Cards

**Standard card pattern**:
```html
class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5"
```

**Consistency check**:

| Template | Rounded | Border | Padding | Assessment |
|----------|---------|--------|---------|------------|
| `dashboard.html` stat cards | `rounded-xl` | `border` | `p-4` | Slightly different padding |
| `class_hub.html` stat cards | `rounded-xl` | `border` | `p-5` | Standard |
| `submit_task.html` form card | `rounded-xl` | `border` | `p-6` | Slightly different padding |
| `login.html` card | `rounded-2xl shadow-lg` | `border` | `p-8` | Different radius AND has shadow |
| `settings.html` cards | `rounded-xl` | `border` | `p-5` | Standard |
| `feed.html` post cards | `rounded-xl` | `border` | `p-5` | Standard |
| Empty state cards | `rounded-xl` | `border-dashed` | `p-10`/`p-12` | Different border style |

**Issue D7: Card padding inconsistency** [LOW]

Cards use `p-4`, `p-5`, `p-6`, or `p-8` depending on the template. The login card uses `rounded-2xl` and `shadow-lg` while all other cards use `rounded-xl` with no shadow.

### Modals

**Issue D8: No shared modal component** [HIGH]

Each template implements modals independently:

| Template | Modal Type | Implementation |
|----------|-----------|---------------|
| `dashboard.html` | Create class | Inline hidden div, `onclick` toggle |
| `dashboard.html` | Join class | Inline hidden div, `onclick` toggle |
| `badges_manage.html` | Badge form | Inline hidden div, JS function toggle |
| `submission_review.html` | Reject panel | Inline expandable section (not modal) |
| `base.html` | Global Modal class | JS class with `createElement` |

The `base.html` global `Modal` class (confirm/alert) is defined but **not used** by any of the specific modals. Each template reinvents modal behavior: open, close, overlay, z-index, positioning.

Consequence: Inconsistent behavior — some modals close on backdrop click, others don't. Some have animation, others appear instantly. None have focus traps (see Chapter 01).

### Toast Notifications

**Issue D9: Toast system exists in only 1 template** [HIGH]

`submission_review.html:21`:
```html
<div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2 pointer-events-none"></div>
```

Toast notification functionality (JS for creating/removing toasts) is implemented only in `submission_review.html`. All other templates use:
- Static alert boxes (login, settings, submit_task) — page-level banners
- `Modal.alert()` from base.html — blocking alert dialog
- No feedback at all — silent success/failure

### Empty States

**Issue D10: Inconsistent empty state design** [MEDIUM]

| Template | Empty State Style | Has Icon | Has CTA |
|----------|------------------|----------|---------|
| `dashboard.html` | Dashed border card, text only | No | No |
| `badges.html` | Solid card with icon + placeholder badges | Yes | No |
| `feed.html` | Dashed border card with icon | Yes (speech bubble) | No (but encouraging text) |
| `templates_list.html` | Card with icon + "新增模板" button | Yes | Yes |
| `learning_history.html` | Simple text | No | No |
| `submission_review.html` | (no explicit empty state) | — | — |

Only `templates_list.html` has a properly designed empty state with icon + CTA.

---

## Icon System

### Current State

All icons are inline SVG, Heroicons-style (24x24 viewBox, stroke-based):
- Consistent `stroke-width="1.8"` across most icons
- Some icons use `stroke-width="2"` (breadcrumb arrows, header icons)
- Sizing via Tailwind: `w-4 h-4`, `w-5 h-5`, `w-8 h-8`, `w-10 h-10`
- Color via `currentColor` inheritance

### Issue D11: No icon set reference [LOW]

Icons appear to be from Heroicons but are inlined individually in each template. There is no shared partial, no icon sprite, and no documentation of which icon is used where. Adding a new page requires copying SVG markup from existing templates or the Heroicons website.

Not a UX issue per se, but contributes to inconsistency — the same concept (e.g., "class") uses slightly different icons across templates because each was hand-picked.

---

## Dark Mode Assessment

### Implementation Quality

The dark mode implementation is **one of the strongest aspects** of the design system:

1. **FOUC prevention** (`base.html:9-20`): Inline script checks localStorage before first paint
2. **System preference respect** (`base.html:16`): Falls back to `prefers-color-scheme: dark`
3. **Toggle persistence** (`base.html:530`): Theme saved to localStorage
4. **Comprehensive coverage**: Every template has dark mode variants

### Dark Mode Issues

**Issue D12: Toast UI Editor dark mode re-creation** [MEDIUM]

`student/submit_task.html` (scripts section): When dark mode toggles, Toast UI Editor must be destroyed and recreated because the library doesn't support live theme switching. This causes:
- Brief content flash during recreation
- Potential loss of unsaved content if not properly synced
- MutationObserver on `<html>` class changes — works but is fragile

Evidence: The template includes a `MutationObserver` that watches for `dark` class changes on `<html>` and recreates all editor instances.

**Issue D13: CodeMirror 6 dark mode not implemented** [LOW]

`teacher/trigger-rules.html`: CodeMirror editor uses custom purple focus ring styling but no dark mode theme is applied to the editor content area. The editor background remains white in dark mode.

---

## Summary

| Issue ID | Title | Severity |
|----------|-------|----------|
| D1 | brand-600 semantic overload | LOW |
| D2 | Inconsistent emerald vs green | LOW |
| D3 | Body text too small (14px) on mobile | MEDIUM |
| D4 | Line height not explicitly set | LOW |
| D5 | No max-width on content | MEDIUM |
| D6 | Primary button vs active tab visual conflict | MEDIUM |
| D7 | Card padding inconsistency | LOW |
| D8 | No shared modal component | HIGH |
| D9 | Toast system in only 1 template | HIGH |
| D10 | Inconsistent empty state design | MEDIUM |
| D11 | No icon set reference | LOW |
| D12 | Toast UI Editor dark mode re-creation | MEDIUM |
| D13 | CodeMirror dark mode not implemented | LOW |
