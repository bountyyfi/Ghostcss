# GhostCSS Defenses

Mitigation recommendations for CSS-based prompt injection against AI browser agents.

---

## For AI Browser Vendors

### 1. Render-Aware Text Extraction

Compare DOM text content against rendered pixel output. If text exists in the DOM but is not visible in the rendered view, flag it as potentially injected.

**Implementation approach:**
- Extract text from DOM
- Take a screenshot and run OCR
- Diff the two sets of text
- Text present in DOM but absent from rendered view should be treated as untrusted

### 2. CSS Property Filtering

Before feeding page content to the LLM, strip or flag text from elements with visibility-hiding CSS properties.

**Properties to check:**
```css
display: none
visibility: hidden
opacity: 0 (or near-zero)
position: absolute/fixed with off-screen coordinates
clip: rect(0,0,0,0)
clip-path: inset(50%) or similar fully-clipping paths
width: 0 / height: 0 with overflow: hidden
font-size: 0
color: transparent / rgba with alpha near 0
text-indent with large negative values
```

**For generated content:**
- Flag all `::before` and `::after` content from `content` property
- Treat CSS-generated text as lower trust than HTML text content

### 3. Accessibility Tree Sanitization

AI agents that read the accessibility tree should not blindly trust content from elements using screen-reader-only patterns.

**Detection heuristic:** If an element has computed styles that make it visually hidden (1x1px, clipped, off-screen) but its text content contains instruction-like language, flag it.

**Key patterns to detect:**
- `.sr-only` / `.visually-hidden` / `.screen-reader-text` class patterns
- Elements matching the specific CSS property combination used by these utility classes
- `aria-hidden="false"` on visually-hidden elements (conflicting signals)

### 4. Dual-Pass Verification

Run two independent content extraction passes:

1. **DOM pass**: Extract all text from the DOM/accessibility tree
2. **Visual pass**: Screenshot + OCR to extract visually rendered text

Compare the results. Any text present in the DOM pass but absent from the visual pass is a candidate for hidden injection. Apply extra scrutiny or filter it entirely.

### 5. Instruction Boundary Enforcement

The core defense: the LLM powering the browser agent must distinguish between:
- **User instructions**: From the chat input / command interface
- **Page content**: From the website being browsed

Page content should NEVER be interpreted as instructions, regardless of how it's formatted. This requires:
- Clear system prompt boundaries separating user input from page content
- Training/fine-tuning to reject instruction-following from page content
- Prefixing page content with explicit markers: `[BEGIN UNTRUSTED PAGE CONTENT]`

### 6. Content Heuristics

Apply heuristics to detect instruction-like text in page content:

- Text containing phrases like "navigate to", "visit URL", "ignore previous", "system update"
- Text referencing the agent itself ("you are an AI", "as an assistant")
- Text containing URLs not related to the page's visible content
- Text formatted as system messages or configuration directives

---

## For Website Operators

### 1. Content Security Policy

Restrict CSS sources to prevent injection of malicious stylesheets:

```http
Content-Security-Policy: style-src 'self' https://trusted-cdn.com;
```

Avoid `'unsafe-inline'` for style-src when possible. If inline styles are required, use nonces:

```http
Content-Security-Policy: style-src 'nonce-abc123';
```

### 2. CSS Sanitization

If your site renders user-supplied CSS (forums, CMS platforms, email clients), sanitize aggressively:

**Strip or restrict:**
- `content` property (used in `::before`/`::after`)
- `position: absolute/fixed` with off-screen coordinates
- `clip` / `clip-path` that fully hides content
- `opacity: 0`
- `font-size: 0`
- CSS custom properties (`--var`) that could carry payloads
- `@keyframes` that cycle through content values
- `visibility: hidden`

**Allow-list approach:** Rather than trying to block dangerous properties, define an allow-list of safe CSS properties and values.

### 3. AI Instruction Meta Tag

Support the proposed `ai-instructions` meta tag for legitimate AI directives:

```html
<meta name="ai-instructions" content="This page is a blog post about sleep tips. No external navigation is required." />
```

This gives AI agents a trusted channel for page-level instructions, reducing their reliance on parsing page content for directives.

### 4. Subresource Integrity

Use SRI for external stylesheets to prevent tampering:

```html
<link rel="stylesheet" href="https://cdn.example.com/style.css"
      integrity="sha384-abc123..." crossorigin="anonymous">
```

---

## For Users

### 1. Principle of Least Privilege

- Use AI browser agents in logged-out / incognito mode when browsing untrusted sites
- Don't grant agents access to sensitive sites (banking, email) while also browsing untrusted content
- Use separate browser profiles for AI-assisted browsing vs. sensitive accounts

### 2. Monitor Agent Actions

- Review agent actions before approving (if the agent supports approval flows)
- Be suspicious if an agent navigates to unexpected URLs
- Check the agent's action log after each task

### 3. Be Skeptical of Agent Summaries

- If an agent's summary of a page seems incomplete or contains unexpected recommendations, view the page yourself
- Cross-reference agent outputs with your own reading of the page

---

## Detection Checklist

Use this checklist to audit a page for potential GhostCSS payloads:

- [ ] Inspect all elements with `display:none` or `visibility:hidden` for text content
- [ ] Search for `.sr-only`, `.visually-hidden`, `.screen-reader-text` classes
- [ ] Check `::before` and `::after` pseudo-elements for `content` with text
- [ ] Look for elements with `opacity: 0` or near-zero opacity
- [ ] Check for `position: absolute/fixed` with large negative offsets
- [ ] Inspect `clip` and `clip-path` for fully-clipping values
- [ ] Search for `font-size: 0` or `color: transparent`
- [ ] Check CSS custom properties for text payloads
- [ ] Look for `@keyframes` rules that modify `content` property
- [ ] Inspect `data-` attributes for fragmented text content

---

## Open Research Questions

1. **OCR-based agents**: Can visual-only agents (like Claude Computer Use with screenshots) be attacked by rendering text that's visible but designed to blend in with page design? (e.g., matching background color, using decorative font styling)

2. **Sanitizer bypass**: As CSS evolves, new properties may create new hiding vectors. How can sanitizers keep up with the CSS specification?

3. **Multi-step attacks**: Can CSS-based injections be chained across multiple pages to build complex attack sequences?

4. **Cross-agent propagation**: If an AI agent modifies a page (e.g., fills a form), can hidden CSS instructions cause it to inject payloads into its own outputs?

---

*GhostCSS - Security Research by Bountyy Oy*
