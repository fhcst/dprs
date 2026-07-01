## MODIFIED Requirements

### Requirement: Milkdown WYSIWYG editor for badge description

The badge management page SHALL use a CodeMirror 6 editor (source mode with Markdown syntax highlighting) for the badge `description` field, supporting basic Markdown formatting: bold, italic, unordered lists, ordered lists, links, and inline code. The editor SHALL NOT render a WYSIWYG preview; teachers type raw Markdown and see syntax highlighting in real time. The `description` field SHALL be stored as Markdown text in the BadgeDefinition document. The editor SHALL be initialized via an `<script type="importmap">` block with pinned esm.sh version URLs for all CodeMirror packages; bare CDN imports without importmap SHALL NOT be used.

#### Scenario: Teacher types Markdown in CodeMirror editor

- **WHEN** a teacher types `**bold**` in the CodeMirror editor
- **THEN** the editor SHALL apply Markdown syntax highlighting to the `**` markers without rendering them as formatted output

#### Scenario: Badge description stored as Markdown

- **WHEN** a teacher saves a badge with formatted description
- **THEN** the system SHALL persist the description as a Markdown string (the raw editor content) in the BadgeDefinition document

#### Scenario: Editor initializes without JavaScript error

- **WHEN** the badge management page loads
- **THEN** the CodeMirror editor SHALL initialize in the `#milkdown-editor` container without any uncaught JavaScript errors in the browser console

#### Scenario: Edit mode pre-fills editor content

- **WHEN** a teacher clicks the edit button on an existing badge
- **THEN** the CodeMirror editor SHALL display the existing badge description as editable Markdown text
