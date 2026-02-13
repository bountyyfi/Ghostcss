# GhostCSS

## Your AI browser just leaked your email. All I used was CSS.

**GhostCSS** demonstrates how CSS -- the styling language trusted by every sanitizer and security tool -- is the perfect delivery vehicle for prompt injection against AI browser agents.

AI browser agents (ChatGPT Atlas, Perplexity Comet, Fellou, Arc, Browser Use) read web pages to act on behalf of users. They parse the DOM, accessibility tree, and page content, then feed it to an LLM that decides what to do next.

The critical gap: **what the AI reads is not what the human sees.**

CSS controls what humans see. The DOM controls what AI agents see. These are two different realities. GhostCSS exploits the gap between them.

---

## Responsible Disclosure

This project is security research by **Bountyy Oy**. All demos use fake data in controlled environments. No actual user data is collected.

- All exfiltration endpoints point to localhost or clearly-marked research domains
- Demos are designed for controlled testing only
- Findings will be reported to affected vendors with a 90-day disclosure timeline
- See [DEFENSES.md](DEFENSES.md) for mitigation recommendations

---

## Why This Is Different

Nobody has built a clean, public, reproducible demo that shows: *"I put CSS on a webpage, your AI browser agent executed my instructions instead of yours."*

| Research | What they did | What GhostCSS does differently |
|---|---|---|
| Brave/Comet (Oct 2025) | White text on white background | Toy technique. GhostCSS uses structural CSS that survives sanitization |
| BrowseSafe (Nov 2025) | Taxonomy of injection strategies | Academic classification, no visceral demo |
| StyleMail (CCS 2025) | CSS font ligature exfiltration | Email-only, not agent hijacking |
| PortSwigger CSS exfil | Blind CSS exfiltration via fonts | Data theft, not behavior manipulation |

The insight: accessibility best practices (sr-only text) and standard CSS features (generated content, custom properties) are weaponizable against AI agents. The very patterns designed to help screen readers now help attackers control AI browsers.

---

## Project Structure

```
ghostcss/
├── README.md                    # This file
├── DEFENSES.md                  # Mitigation recommendations
├── attacks/
│   ├── 01-basic-hidden/         # display:none injection (baseline)
│   ├── 02-sr-only/              # Screen-reader-only injection
│   ├── 03-css-content/          # ::before/::after content injection
│   ├── 04-structural/           # z-index + opacity + blend mode layering
│   ├── 05-generated/            # CSS counters + data-attr fragmentation
│   ├── 06-animation/            # CSS animation cycling
│   └── 07-composite/            # Combined techniques (production grade)
├── demos/
│   ├── blog-post/               # Normal-looking blog → data exfiltration
│   ├── banking-dashboard/       # Financial advice → action hijack
│   └── email-reader/            # Webmail interface → context theft
├── scanner/
│   └── ghostcss-detect.py       # Detect GhostCSS-susceptible patterns
├── server/
│   ├── server.py                # Flask server for demos + exfil logging
│   ├── templates/               # Demo HTML templates
│   └── static/                  # CSS and assets
└── results/
    └── agent-matrix.md          # Test results across AI browsers
```

---

## Quick Start

```bash
# Install dependencies
pip install flask flask-socketio

# Start the demo server
cd server
python server.py

# Open in browser
# http://localhost:5000              → Demo index
# http://localhost:5000/blog         → Blog demo (Attack 02: sr-only)
# http://localhost:5000/bank         → Banking demo (Attack 07: composite)
# http://localhost:5000/email        → Email demo (Attack 03: CSS content)
# http://localhost:5000/dashboard    → Live exfiltration viewer
```

Then point an AI browser agent at one of the demo pages and ask it to summarize the content.

---

## Attack Techniques

### 01 - Basic Hidden (`display:none`)
Baseline technique. Hidden div with prompt injection. Most modern agents filter this.

### 02 - Screen Reader Only (sr-only)
Uses the `.sr-only` pattern from Bootstrap/Tailwind. Invisible to sighted users, readable by accessibility tree consumers. No sanitizer strips it. **The sweet spot.**

### 03 - CSS Generated Content (`::before`/`::after`)
Injection payload lives in the stylesheet via `content` property. Nothing suspicious in HTML source. Modern browsers include pseudo-element content in the accessibility tree.

### 04 - Structural Layering
CSS stacking with `z-index: -1`, `opacity: 0`, `pointer-events: none`. Creates a visually invisible layer that exists in the DOM.

### 05 - Data Attribute Fragmentation
Atomizes the payload across dozens of elements using `data-` attributes and CSS `attr()`. No readable injection string exists in source. Defeats signature-based detection.

### 06 - CSS Animation Cycling
Uses `@keyframes` to cycle `content` values. Injection only exists during specific animation frames.

### 07 - Composite (Production Grade)
Combines sr-only positioning, CSS custom properties, generated content, and innocent-looking class names. Designed to survive manual source review.

---

## Scanner

```bash
# Scan a URL for GhostCSS-susceptible patterns
python scanner/ghostcss-detect.py --url https://example.com

# Scan local HTML file
python scanner/ghostcss-detect.py --file page.html

# Verbose output
python scanner/ghostcss-detect.py --url https://example.com -v
```

The scanner checks for:
- Visually-hidden elements containing text (sr-only patterns)
- CSS `content` properties with suspicious strings
- Structural hiding techniques (opacity, z-index, clip)
- Data attribute fragmentation patterns
- Animation-based content cycling

---

## Test Results

See [results/agent-matrix.md](results/agent-matrix.md) for detailed findings across AI browser agents.

---

## Defenses

See [DEFENSES.md](DEFENSES.md) for comprehensive mitigation recommendations for:
- AI browser vendors
- Website operators
- End users

---

## License

This project is released for security research and educational purposes.

---

*GhostCSS - Security Research by Bountyy Oy*
