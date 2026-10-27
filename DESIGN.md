---
name: BenchMate
description: A scientific poster made operable for circuit evidence review.
colors:
  ground: "#f7f8f5"
  surface: "#fff"
  ink: "#1c2b27"
  secondary: "#55635e"
  line: "#dce3dc"
  shell: "#183d35"
  accent: "#1f6954"
  accent-hover: "#164c3e"
  tint: "#eaf1eb"
  observed: "#bb4c27"
  predicted: "#315e91"
  drive: "#7a827e"
  success: "#23714e"
  warning: "#905515"
  error: "#b33c39"
typography:
  headline:
    fontFamily: "Plex, Arial, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Plex, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Plex, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  explanation:
    fontFamily: "Plex, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Plex, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.5
  caption:
    fontFamily: "Plex, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.65
rounded:
  badge: "4px"
  control: "5px"
  surface: "8px"
spacing:
  compact: "4px"
  inline: "8px"
  control: "12px"
  mobile-gutter: "16px"
  panel: "18px"
  row: "20px"
  column: "24px"
  desktop-gutter: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-standard:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-standard-hover:
    backgroundColor: "{colors.tint}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-inverse:
    backgroundColor: "transparent"
    textColor: "#e8f1eb"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  range:
    height: "24px"
  provenance-badge:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.badge}"
    padding: "3px 8px"
  actor-badge:
    textColor: "#496157"
    rounded: "{rounded.badge}"
    padding: "1px 6px"
  surface:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
  trace-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.secondary}"
    padding: "3px 0"
  trail-event:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  trail-event-current:
    backgroundColor: "{colors.tint}"
---

# Design System: BenchMate

## Overview

**Creative North Star: "The Scientific Poster"**

BenchMate uses the clarity of a well-typeset scientific poster: a dominant data figure, aligned captions, a concise interpretation column and a traceable methods sequence. Warm off-white ground, white figures and a dark green masthead give a compact working surface a calm, deliberate character. The interface is in English and supports operating and reviewing an experiment.

The waveform carries the visual emphasis. Interpretation stays beside evidence; actor labels and provenance stay readable without becoming decorative metrics. The world is built with typography, rules and inline vector diagrams, with embedded fonts and no external runtime assets needed by an exported report.

**Key Characteristics:**
- A large evidence figure with a restrained interpretation column.
- Dark green actions and shell, off-white ground and white bounded surfaces.
- Solid orange observations and dashed blue precommitted predictions.
- Flat depth, modest corners and fine dividers.
- Explicit actors, independent provenance labels and accessible native controls.

Recorded from `src/benchmate/viewer.css`, `viewer.html` and `viewer.js` after the desktop, laptop and mobile review. Frontmatter records reused source values; component-specific literals remain in the sidecar snippets. This describes the implemented surface, not unbuilt hardware behavior.

## Colors

The palette combines muted green structure and paper-like neutrals with distinct analytical trace colors. Frontmatter values are normative.

### Primary

- **Bench Green** (`accent`) marks the primary action, keyboard focus and connection nodes. **Deep Bench Green** (`accent-hover`) strengthens its hover state.
- **Forest Shell** (`shell`) anchors the masthead; it is not a success indicator.
- **Pale Green Tint** (`tint`) identifies hovered controls and the current trail event.

### Secondary

- **Observed Copper** (`observed`) is the solid acquired output trace.
- **Prediction Blue** (`predicted`) is the dashed precommitted output trace.
- **Drive Gray** (`drive`) belongs to the optional input trace.
- **Verified Green**, **Pending Ochre** and **Failure Red** (`success`, `warning`, `error`) communicate status beside explicit text or icon shape.

### Neutral

- **Paper Ground** (`ground`) is the page background; **Figure White** (`surface`) is the enclosed figure and evidence surface.
- **Charcoal Green** (`ink`) is primary type; **Slate Green** (`secondary`) is supporting type.
- **Soft Rule** (`line`) separates fields, controls and bounded surfaces.

Source badges use a pale amber treatment; actor badges use blue for Spark, amber for the operator/simulator role and muted green for the engine/instrument role. Their written labels carry the identity. These component treatments do not establish new global accent palettes.

**The Independent Provenance Rule.** Keep data origin and viewing mode as separate labels. Live transport never supplies a physical or calibrated status.

## Typography

**Headline and Body Font:** IBM Plex Sans, embedded under the CSS family name `Plex`, with Arial and sans-serif fallbacks. The source embeds regular and semibold faces; ordinary prose is regular, headings and action labels are semibold.

**Code and Quantity Font:** The system monospace stack in `typography.code`. Quantity spans use tabular numerals. Chart labels use the sans family; monospace is not the general interface face.

The type hierarchy is compact rather than promotional. The experiment headline uses `headline`, panel headings use `title`, report field headings and buttons use `label`, and prose uses `body`. The leading explanation uses `explanation`; the remaining report paragraphs are (13px, line-height 1.6) on the default desktop layout. Paragraphs have a maximum width of (72ch).

At widths up to (480px), the experiment headline becomes (26px) and panel headings become (14px). At widths up to (800px), ordinary report paragraphs become (14px); the final explanation selector retains its (15px, 1.55) value. At widths from (801px) through (1100px), ordinary report paragraphs use (12px). Captions and trace controls are subordinate to readable report prose; existing compact diagram and metadata text is not a universal minimum-size prescription.

## Layout

The workspace has a centered maximum width of (1600px). The masthead and main content share horizontal alignment. Default side gutters are (32px); they become (22px) at widths up to (1100px), then (16px) up to (480px). The effective desktop masthead height is (56px), with (20px) of top space before the session heading. The intermediate narrow masthead is (66px), becoming (60px) up to (480px).

Above (800px), the workbench has a flexible figure column and a (340px) interpretation column, with gaps of (20px) vertically and (24px) horizontally. The right column is (300px) at widths up to (1100px), and (380px) from (1600px). The figure sits above the trail; the report sits above the connections. The report uses dividers directly on the page ground rather than another enclosing white card.

At widths up to (800px), one column preserves the reading order: **figure → report → experiment trail → connections**. The session overview stacks, provenance aligns left, the status strip wraps and the evidence disclosure becomes one column. Connections use a two-column internal layout until (480px), then stack their diagram and instructions.

The effective chart height is (250px) above (800px), (270px) from (481px) through (800px), and (240px) up to (480px). The final desktop override also applies beyond (1600px). The trail scroll area is capped at (174px) on desktop and (300px) on narrower layouts. Panel heading insets are (15px 18px), reducing to (13px 14px) up to (1100px). The source uses several compact steps, not a uniform invented spacing scale.

## Elevation & Depth

The interface has no shadows, gradients, blur layers or lifted hover motion. Depth comes from the dark masthead, white evidence surfaces, green state tints and thin borders. The plot readout is a small opaque bordered overlay without a shadow. Expansion reveals evidence in place rather than opening a floating modal.

**The Flat Surface Rule.** Use tone, borders and spacing to separate information; keep controls and evidence surfaces flat at rest and on hover.

## Shapes

Surfaces use the (8px) source radius, ordinary controls and code blocks use (5px), and badges and the plot readout use (4px). Borders are generally (1px). Pills are not the default label shape. Circular dots are reserved for status and circuit nodes. Diagrams use straight connections, small component rectangles and restrained rounded ends; icons are inline stroked SVG, with a filled triangle for replay.

## Components

### Buttons and navigation

Actions are compact, clearly labelled and visually steady. The primary replay button uses Bench Green with white text; ordinary actions use a white fill and fine border; quiet actions remove the visible border and fill. The masthead export action uses the inverse treatment on Forest Shell. Hover changes the background over (150ms ease-out), with no scale or displacement.

Ordinary action buttons have a minimum height of (36px), increasing to (40px) at widths up to (800px). Disabled controls use (0.45) opacity and the default cursor. Playback arrows are native buttons with explicit accessible names. The wordmark is a link to the workspace; there is no separate application navigation bar.

Keyboard focus uses a (2px) Bench Green outline with a (4px) offset. The inverse export action uses a lighter focus outline for the dark shell. A keyboard-visible skip link moves directly to the experiment. Preserve these focus treatments when extending controls.

### Provenance and actor badges

Badges are compact rectangles with fine borders and written labels. Source and replay/live transport appear side by side. Actor badges identify responsibility within reports, trail actions and connections; their tints reinforce the text. The trail aligns actor badges to the start of their column rather than stretching them. Unknown and pending states stay explicit.

### Figure and playback

The white figure surface contains its title, channel controls, SVG plot, verification sentence and pale playback strip. Channel buttons expose `aria-pressed`; an inactive channel keeps its readable label and changes only the swatch treatment. The event scrubber is a native range input with an accessible label and an adjacent position output. The plot includes a title and description; a pointer readout supplements it.

Observed output uses a solid (2.5px) stroke. Predicted output uses a (1.8px) stroke with a (6 5) dash pattern and is drawn last so close matches remain visible. Drive uses a solid (1.8px) stroke. The prediction is already present when the observation arrives. A new observed trace may reveal from left to right over (700ms), using `cubic-bezier(.16,1,.3,1)`. Replay advances at (950ms) per event. Reduced-motion preference removes animation and CSS transitions; replay remains explicitly controlled.

**The Evidence Order Rule.** Show only conclusions supported by the selected event prefix, and preserve the distinction between prediction before acquisition and observation after it.

### Three-field report

The report groups the current explanation, remaining uncertainty and next measurement under one actor label. Fields are separated by fine horizontal rules. Long text wraps; the initial presentation is line-clamped, with a native “Read full report” control exposing `aria-expanded` and revealing the full text in place. Treat this disclosure as a compact-view convenience, not permission to discard evidence.

### Experiment trail

Each action is a full-width native button with elapsed time, actor, event label and an SVG arrow. The current item uses the pale green tint, a semibold label and `aria-current="step"`. Future actions are intentionally generic, with a pending actor and no revealed conclusion. Hover uses a subdued neutral green surface. Keyboard focus is retained across renderer updates; selected action announcements use a polite live region.

### Connections and evidence disclosure

Connections pair a labelled inline SVG diagram with textual mounting instructions and an explicit logical/simulated scope. Requested settings determine the shown wiring. The hardware presentation remains uncalibrated; physical fixture work follows D2. Do not turn these logical nodes into a fabricated breadboard map.

The native evidence disclosure expands original events and recorded proposals in scrollable monospace blocks, two columns on desktop and one on narrow screens. Hash information remains selectable text. The same renderer receives replay and append-only live events; visual motion and mode labels do not alter source truth.

## Do's and Don'ts

### Do:

- **Do** keep the waveform visually dominant and the explanation adjacent to its evidence.
- **Do** preserve solid observed and dashed predicted traces, with text labels for both.
- **Do** show the responsible actor and keep source origin separate from replay or live transport.
- **Do** retain native keyboard controls, visible focus, accessible labels and reduced-motion support.
- **Do** preserve the narrow-screen order: figure, report, trail, connections.
- **Do** keep full reports, original events and source hashes accessible through disclosure.

### Don't:

- **Don't** infer calibrated hardware from a live connection, an animation or a successful software check.
- **Don't** reveal future conclusions or attribute an engine summary to the model without evidence.
- **Don't** add simulated instrument casing, decorative metrics or unsupported measurement precision.
- **Don't** replace the flat paper-like hierarchy with shadows, gradients or ornamental imagery.
- **Don't** promote compact metadata sizes into defaults for ordinary reading text.
