## MODIFIED Requirements

### Requirement: Unified empty state component

The system SHALL provide a Jinja2 macro for rendering empty states. The macro SHALL accept parameters for icon (SVG markup), title, description, and optional CTA button (text + href). All pages that can display an empty list SHALL use this macro.

The macro SHALL render the `icon` argument as raw, un-escaped HTML so that SVG markup is displayed as a vector image and NOT as escaped source text. Because the rendering environment has Jinja2 autoescape enabled, the macro MUST apply the `| safe` filter to the `icon` argument to bypass escaping.

The `icon` argument MUST be restricted to trusted, static markup (such as an SVG string literal hard-coded in a template). Callers MUST NOT pass user-controlled or otherwise untrusted data as `icon`, because raw rendering of untrusted input would cause cross-site scripting (XSS). The macro SHALL document this restriction in an inline comment.

All other text parameters (`title`, `description`, `cta_text`, `cta_href`) SHALL remain HTML-escaped by autoescape and MUST NOT use the `| safe` filter.

#### Scenario: Icon SVG markup renders as a vector image

- **WHEN** a caller invokes the macro with `icon` set to a static SVG string literal and the page is rendered
- **THEN** the rendered HTML SHALL contain the SVG element as live markup and SHALL NOT contain escaped `&lt;svg&gt;` source text

#### Scenario: Icon argument is trusted static markup only

- **WHEN** any of the macro's callers supplies the `icon` argument
- **THEN** the supplied value SHALL be a hard-coded static SVG literal defined in the template and SHALL NOT be user-controlled input

#### Scenario: Non-icon text parameters stay escaped

- **WHEN** the macro renders `title`, `description`, `cta_text`, or `cta_href`
- **THEN** those values SHALL be HTML-escaped by autoescape and SHALL NOT be passed through the `| safe` filter

#### Scenario: Dashboard renders with no classes (student)

- **WHEN** a student with no class memberships views the dashboard
- **THEN** the empty state SHALL display an icon, the title "尚未加入任何班級", a description "向老師索取邀請碼，或搜尋公開班級", and a "加入班級" CTA button

#### Scenario: Dashboard renders with no classes (teacher)

- **WHEN** a teacher with no classes views the dashboard
- **THEN** the empty state SHALL display an icon, the title "尚未建立任何班級", a description "建立您的第一個班級，開始管理學生每日練習", and a "建立班級" CTA button

#### Scenario: Submission review page has no submissions

- **WHEN** a teacher views the submission review page and there are no submissions for the selected date
- **THEN** the empty state SHALL display an icon and the message "今天沒有待審作業，學生提交後會顯示在這裡"
