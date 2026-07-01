## ADDED Requirements

### Requirement: Static CSS generation

The system SHALL generate a static CSS file from Tailwind configuration at build time. The base template SHALL reference this static CSS file instead of the Tailwind Play CDN script. The Tailwind configuration (colors, fonts, dark mode strategy) SHALL produce identical styling to the current Play CDN configuration.

#### Scenario: Page loads in production

- **WHEN** any page loads in the production environment
- **THEN** the page SHALL load a static CSS file (not the Tailwind Play CDN script)
- **THEN** the page SHALL render identically to the current CDN-based rendering

#### Scenario: Developer adds new Tailwind classes

- **WHEN** a developer adds new Tailwind CSS classes to a template file
- **THEN** the build process SHALL detect the new classes and regenerate the CSS file
- **THEN** the new classes SHALL be included in the output CSS

### Requirement: Tailwind configuration extraction

The Tailwind configuration (custom colors, font families, dark mode class strategy) currently inline in `base.html` SHALL be extracted to a standalone `tailwind.config.js` file. The `base.html` inline configuration script SHALL be removed.

#### Scenario: Tailwind config file is created

- **WHEN** the build system processes templates
- **THEN** the `tailwind.config.js` file SHALL contain the brand color palette, font family definitions, and `darkMode: 'class'` setting
- **THEN** the `base.html` SHALL NOT contain an inline Tailwind config script

### Requirement: Touch target minimum size

All interactive elements (buttons, links, form controls) SHALL have a minimum touch target size of 44x44 CSS pixels. Elements that are currently smaller SHALL have their padding increased to meet this minimum.

#### Scenario: Feed post delete button renders on mobile

- **WHEN** the feed post delete button renders on a touch device
- **THEN** the button's clickable area SHALL be at least 44x44 CSS pixels

#### Scenario: Reaction button renders on mobile

- **WHEN** the feed reaction ("讚") button renders on a touch device
- **THEN** the button's clickable area SHALL be at least 44x44 CSS pixels

### Requirement: Toast UI Editor mobile preview mode

On viewports narrower than 640px, the Toast UI Editor SHALL use `tab` preview style (write/preview toggle) instead of `vertical` (side-by-side split).

#### Scenario: Student opens task submission form on mobile

- **WHEN** a student opens the task submission form on a viewport narrower than 640px
- **THEN** the markdown editor SHALL render in tab mode (write/preview toggle)
- **THEN** each panel SHALL occupy the full editor width

#### Scenario: Student opens task submission form on desktop

- **WHEN** a student opens the task submission form on a viewport 640px or wider
- **THEN** the markdown editor SHALL render in vertical (side-by-side) mode
