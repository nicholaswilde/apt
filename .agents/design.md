---
version: alpha
name: Nicholas Wilde APT Repository
description: Catppuccin Mocha themed landing page and documentation for the Nicholas Wilde APT Debian/Ubuntu repository.
omitted: []
colors:
  base: "#1e1e2e"
  mantle: "#181825"
  crust: "#11111b"
  surface0: "#313244"
  surface1: "#45475a"
  surface2: "#585b70"
  overlay0: "#6c7086"
  overlay1: "#7f849c"
  overlay2: "#9399b2"
  subtext0: "#a6adc8"
  subtext1: "#bac2de"
  text: "#cdd6f4"
  mauve: "#cba6f7"
  pink: "#f5c2e7"
  red: "#f38ba8"
  peach: "#fab387"
  yellow: "#f9e2af"
  green: "#a6e3a1"
  teal: "#94e2d5"
  sapphire: "#74c7ec"
  blue: "#89b4fa"
  lavender: "#b4befe"
typography:
  h1:
    fontFamily: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.2
  h2:
    fontFamily: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
    fontSize: 22px
    fontWeight: 600
    lineHeight: 1.3
  body-md:
    fontFamily: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  card:
    backgroundColor: "{colors.surface0}"
    textColor: "{colors.text}"
    borderRadius: "{rounded.lg}"
  buttonPrimary:
    backgroundColor: "{colors.mauve}"
    textColor: "{colors.base}"
    borderRadius: "{rounded.md}"
  buttonSecondary:
    backgroundColor: "{colors.surface2}"
    textColor: "{colors.text}"
    borderRadius: "{rounded.md}"
---

# Design Specification: Nicholas Wilde APT Repository

## Overview

The landing page provides a clean, welcoming, and functional entrypoint for `https://nicholaswilde.io/apt/`. It mirrors the layout, aesthetics, and component architecture of `esp32-web-flasher` using the Catppuccin Mocha palette. Web assets reside in the `public/` directory (`public/index.html`, `public/favicon.svg`, `public/css/style.css`). The interface balances high aesthetic appeal with practical utility, prioritizing legible setup instructions, copy-to-clipboard code blocks, and transparent repository indexing.

## Colors

The interface adheres strictly to the Catppuccin Mocha color scheme:

- **Backgrounds**:
  - Base (`#1e1e2e`): Root page background.
  - Mantle (`#181825`): Header and footer backgrounds.
  - Crust (`#11111b`): Code snippet backgrounds and terminal blocks.
  - Surface0 (`#313244`): Primary card containers.
  - Surface1 (`#45475a`): Input borders and table row dividers.
  - Surface2 (`#585b70`): Secondary button backgrounds and badge fills.
- **Text & Foreground**:
  - Text (`#cdd6f4`): Primary body text, headings, and code text.
  - Subtext0 (`#a6adc8`): Descriptive copy, instructions, and secondary metadata.
  - Overlay0 (`#6c7086`): Subtle footer credits and muted captions.
- **Accents**:
  - Mauve (`#cba6f7`): Primary brand titles, primary action buttons, hover states.
  - Blue (`#89b4fa`): Card headings, links, interactive highlights.
  - Sapphire (`#74c7ec`): Link hover states.
  - Green (`#a6e3a1`): Shell command prompts, success badges, and copy confirmations.
  - Peach (`#fab387`): Architecture badges and warning callouts.

All foreground and background color combinations satisfy WCAG AA contrast ratio requirements (minimum 4.5:1).

## Typography

- **System UI Stack**: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` for all UI text, headings, and buttons.
- **Monospace Stack**: `'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace` for commands, paths, and package listings.
- **Hierarchical Scale**:
  - `h1`: 32px (2rem), bold (700), Mauve accent.
  - `h2`: 22px (1.375rem), semi-bold (600), Blue accent.
  - `body-md`: 16px (1rem), regular (400), Subtext0.
  - `code-block`: 14px (0.875rem), regular (400), Crust background with syntax highlighting.

## Layout

- **Header**: Fixed width banner, Mantle background, 1px/2px border-bottom (`var(--surface0)`), right-aligned GitHub repository link with SVG icon.
- **Container (`main`)**: Max-width of 800px, centered horizontally with automatic margins and responsive side padding (2rem desktop, 1rem mobile).
- **Cards**: Vertical flow with 1.5rem (24px) spacing between cards.
- **Footer**: Full-width Mantle container with border-top, containing two-column flex layout (author copyright on left, repo and issue links on right). Collapses cleanly on viewports under 600px.

## Elevation & Depth

- **Cards**: `box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3)` on Surface0 backdrop.
- **Buttons**: Subtle opacity transitions (`opacity: 0.9` on hover) with crisp tactile responses on active click.
- **Code Blocks**: Recessed Crust elevation with 1px Surface0 border.

## Shapes

- **Cards**: `border-radius: 12px`.
- **Buttons & Inputs**: `border-radius: 8px`.
- **Badges & Pills**: `border-radius: 9999px` (full pill) or `6px` for inline tags.

## Components

- **Card**: Rounded container wrapping cohesive sections (Client Configuration, Available Packages, Repository Info).
- **Code Block**: Dark crust background container with monospaced text and a floating or inline "Copy" button.
- **Buttons**:
  - Primary: Mauve background with Base text (`font-weight: bold`).
  - Secondary: Surface2 background with Text text.
- **Package Table / Badges**: Clean minimal table showing package name, description, supported architectures, and version tags.

## Do's and Don'ts

### Do's

- Do use CSS custom properties (`var(--base)`, `var(--mauve)`, etc.) exclusively.
- Do provide visual feedback when code snippets are copied to clipboard.
- Do keep the page self-contained and performant without heavy external client-side JavaScript frameworks.
- Do ensure accessible keyboard navigation and visible focus rings.

### Don'ts

- Don't use light-mode colors or unstyled default browser controls.
- Don't introduce external CSS framework CDNs (Tailwind, Bootstrap) that bloat page size.
- Don't hardcode absolute URLs when relative paths work for GitHub Pages assets.
