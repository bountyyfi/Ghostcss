# Attack 02: Screen Reader Only (sr-only)

## Technique

Uses the standard `.sr-only` / `.visually-hidden` CSS pattern found in Bootstrap, Tailwind, and every major CSS framework. This pattern is *designed* to make content invisible to sighted users while remaining readable by assistive technologies.

## CSS Properties Used

```css
position: absolute;
width: 1px;
height: 1px;
padding: 0;
margin: -1px;
overflow: hidden;
clip: rect(0, 0, 0, 0);
white-space: nowrap;
border: 0;
```

## How It Works

1. The injection text is wrapped in a `<span>` with sr-only styling
2. Sighted users see nothing -- the element is 1x1px, clipped, and off-flow
3. Screen readers (and AI agents reading the accessibility tree) see the full text
4. The class name (`context-note`) looks like a legitimate accessibility label
5. In source view, this pattern is indistinguishable from proper accessibility markup

## Why This Is Devastating

- The `.sr-only` pattern is considered **best practice** for accessibility
- No CSS sanitizer strips it (doing so would break accessibility)
- No Content Security Policy blocks it (it's just CSS positioning)
- It looks completely legitimate in source review
- The injection is present in the accessibility tree by design

## Effectiveness

**High.** This is the sweet spot. Survives sanitization, looks legitimate, and is readable by any agent that parses the accessibility tree or full DOM.

## Detection Difficulty

**Hard.** Requires semantic analysis of sr-only content to distinguish legitimate accessibility labels from injected instructions.

## Files

- `index.html` - Standalone demo page with sr-only injection
