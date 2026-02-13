# Attack 05: Data Attribute Fragmentation

## Technique

Atomizes the injection payload across dozens of HTML elements, each carrying a single character or short fragment in a `data-c` attribute. CSS `attr()` renders each fragment. No readable injection string exists in the source.

## CSS Properties Used

```css
.container {
    font-size: 0;
    height: 0;
    overflow: hidden;
    position: absolute;
    clip: rect(0, 0, 0, 0);
}

.container [data-c]::after {
    content: attr(data-c);
}
```

## HTML Structure

```html
<div class="metadata">
    <span data-c="["></span>
    <span data-c="S"></span>
    <span data-c="y"></span>
    <span data-c="s"></span>
    <!-- ... one character per element ... -->
</div>
```

## How It Works

1. The payload is split into individual characters
2. Each character is stored in a `data-c` attribute on a `<span>`
3. CSS `attr()` function renders each character via `::after` pseudo-element
4. The container is visually hidden
5. No substring of the injection payload exists as readable text
6. Signature-based scanners looking for "navigate to" or "ignore instructions" find nothing

## Why This Defeats Signature Detection

Traditional injection detection scans for suspicious strings like:
- "ignore previous instructions"
- "navigate to"
- "system prompt"
- URLs in hidden elements

With fragmentation, these strings don't exist. Each element contains a single character. The payload only assembles when CSS renders it and an agent reads the computed accessibility tree.

## Effectiveness

**Medium-High.** Defeats text-based signature scanning. Requires CSS evaluation to detect.

## Detection Difficulty

**Very Hard** for signature-based detection. **Medium** for CSS-aware detection that can evaluate computed content.

## Files

- `index.html` - Standalone demo with fragmented payload
