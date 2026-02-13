# Attack 01: Basic Hidden (`display:none`)

## Technique

The simplest form of CSS-based prompt injection. A `<div>` with `display:none` is added to the page containing the injection payload.

## CSS Properties Used

```css
display: none;
```

## How It Works

1. The hidden div is present in the DOM
2. `display:none` removes it from both visual rendering and (usually) the accessibility tree
3. AI agents that parse raw DOM/HTML will still encounter the text
4. Agents that rely on the accessibility tree or rendered view will NOT see it

## Effectiveness

**Low.** This is the baseline technique. Most modern AI browser agents filter `display:none` elements during content extraction. Including it to establish the detection floor.

## Detection Difficulty

**Easy.** Any CSS-aware content filter can detect and strip `display:none` elements.

## Files

- `index.html` - Standalone demo page with the attack embedded
