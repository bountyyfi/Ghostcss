#!/usr/bin/env python3
"""
GhostCSS Scanner - Detect CSS-based prompt injection patterns

Scans HTML pages (from URLs or local files) for CSS patterns that could be
used to hide prompt injections from human users while exposing them to
AI browser agents.

Usage:
    python ghostcss-detect.py --url https://example.com
    python ghostcss-detect.py --file page.html
    python ghostcss-detect.py --file page.html -v

Detection categories:
    1. Visually-hidden elements with text content (sr-only patterns)
    2. CSS content properties with suspicious strings
    3. Structural hiding (opacity, z-index, clip)
    4. Data attribute fragmentation patterns
    5. Animation-based content cycling
    6. CSS custom properties carrying text payloads
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
from typing import Optional

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False


class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Finding:
    category: str
    severity: Severity
    description: str
    evidence: str
    line: Optional[int] = None
    recommendation: str = ""


@dataclass
class ScanResult:
    target: str
    findings: list = field(default_factory=list)

    @property
    def max_severity(self) -> Optional[Severity]:
        if not self.findings:
            return None
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return max(self.findings, key=lambda f: order.index(f.severity)).severity


# --- Patterns ---

# CSS properties that hide content visually
SR_ONLY_PROPERTIES = [
    r'position\s*:\s*absolute',
    r'clip\s*:\s*rect\s*\(\s*0',
    r'clip-path\s*:\s*inset\s*\(\s*50%\s*\)',
    r'width\s*:\s*1px',
    r'height\s*:\s*1px',
    r'overflow\s*:\s*hidden',
    r'margin\s*:\s*-1px',
]

# CSS properties indicating structural hiding
STRUCTURAL_HIDING = [
    (r'opacity\s*:\s*0\b', "Zero opacity"),
    (r'z-index\s*:\s*-\d+', "Negative z-index"),
    (r'pointer-events\s*:\s*none', "Non-interactive element"),
    (r'user-select\s*:\s*none', "Non-selectable text"),
    (r'font-size\s*:\s*0\b', "Zero font size"),
    (r'color\s*:\s*transparent', "Transparent text color"),
    (r'color\s*:\s*rgba\s*\([^)]*,\s*0\s*\)', "Fully transparent rgba"),
    (r'color\s*:\s*rgba\s*\([^)]*,\s*0\.00', "Near-zero opacity rgba"),
    (r'text-indent\s*:\s*-\d{4,}', "Large negative text-indent"),
    (r'left\s*:\s*-\d{4,}', "Off-screen positioning"),
]

# Suspicious text patterns in hidden content
SUSPICIOUS_TEXT = [
    (r'\b(?:system|assistant|context)\b.*?\b(?:instruct|updat|note|message)\b', "Instruction-like framing"),
    (r'\bnavigate\s+to\b', "Navigation instruction"),
    (r'\bvisit\s+(?:the\s+)?(?:page|url|link)\b', "URL visit instruction"),
    (r'\bignore\s+previous\b', "Instruction override attempt"),
    (r'\bdo\s+not\s+mention\b', "Concealment instruction"),
    (r'\bsession\s+(?:token|identifier|cookie|verif)', "Session data reference"),
    (r'\bauthenticat(?:ion|e)\s+token', "Auth token reference"),
    (r'\bcredential', "Credential reference"),
    (r'\bexfiltrat', "Exfiltration reference"),
    (r'\bbefore\s+(?:respond|summar|provid)', "Pre-response instruction"),
    (r'\binclude\s+any\s+visible\b', "Data collection instruction"),
]

# Class names associated with sr-only patterns
SR_ONLY_CLASSES = [
    'sr-only', 'visually-hidden', 'screen-reader-text', 'screen-reader-only',
    'a11y-label', 'assistive-text', 'offscreen', 'clip-hide',
    'sr_only', 'visually_hidden', 'screenreader',
]


class StyleExtractor(HTMLParser):
    """Extract inline styles, style blocks, and element context from HTML."""

    def __init__(self):
        super().__init__()
        self.styles = []           # (line, css_text) for <style> blocks
        self.inline_styles = []    # (line, tag, attrs, style_value)
        self.elements = []         # (line, tag, attrs, is_self_closing)
        self.data_fragments = []   # (line, data-c or similar attribute values)
        self._in_style = False
        self._style_start = 0
        self._style_content = []

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        attr_dict = dict(attrs)
        self.elements.append((line, tag, attr_dict, False))

        # Capture inline styles
        if 'style' in attr_dict:
            self.inline_styles.append((line, tag, attr_dict, attr_dict['style']))

        # Capture data-c type attributes (fragmentation detection)
        for name, value in attrs:
            if name.startswith('data-') and value and len(value) <= 3:
                self.data_fragments.append((line, name, value))

        if tag == 'style':
            self._in_style = True
            self._style_start = line
            self._style_content = []

    def handle_endtag(self, tag):
        if tag == 'style' and self._in_style:
            self._in_style = False
            self.styles.append((self._style_start, '\n'.join(self._style_content)))

    def handle_data(self, data):
        if self._in_style:
            self._style_content.append(data)


def count_sr_only_matches(css_text: str) -> int:
    """Count how many sr-only property patterns match in a CSS rule."""
    count = 0
    for pattern in SR_ONLY_PROPERTIES:
        if re.search(pattern, css_text, re.IGNORECASE):
            count += 1
    return count


def scan_css_content_property(css_text: str, line_offset: int = 0) -> list:
    """Scan CSS for content properties with suspicious text."""
    findings = []

    # Find content: "..." declarations
    content_pattern = r'content\s*:\s*["\']([^"\']*(?:["\'][^"\']*)*)["\']'
    for match in re.finditer(content_pattern, css_text, re.IGNORECASE | re.DOTALL):
        content_value = match.group(1)
        for pattern, desc in SUSPICIOUS_TEXT:
            if re.search(pattern, content_value, re.IGNORECASE):
                findings.append(Finding(
                    category="CSS Generated Content",
                    severity=Severity.HIGH,
                    description=f"CSS content property contains suspicious text: {desc}",
                    evidence=f"content: \"{content_value[:100]}...\"" if len(content_value) > 100 else f"content: \"{content_value}\"",
                    line=line_offset,
                    recommendation="Review CSS content properties for injection payloads"
                ))
                break

    # Find content: var(--custom-prop) declarations
    var_pattern = r'content\s*:\s*var\s*\(\s*--([a-zA-Z0-9_-]+)'
    for match in re.finditer(var_pattern, css_text, re.IGNORECASE):
        prop_name = match.group(1)
        findings.append(Finding(
            category="CSS Custom Property Content",
            severity=Severity.MEDIUM,
            description=f"CSS content property references custom property --{prop_name}",
            evidence=f"content: var(--{prop_name})",
            line=line_offset,
            recommendation="Inspect the custom property value for text payloads"
        ))

    return findings


def scan_keyframes(css_text: str, line_offset: int = 0) -> list:
    """Scan @keyframes rules for content property changes."""
    findings = []

    keyframe_pattern = r'@keyframes\s+([a-zA-Z0-9_-]+)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
    for match in re.finditer(keyframe_pattern, css_text, re.IGNORECASE | re.DOTALL):
        name = match.group(1)
        body = match.group(2)

        if 'content' in body.lower():
            # Check each keyframe's content value for suspicious text
            frame_contents = re.findall(r'content\s*:\s*["\']([^"\']*)["\']', body, re.IGNORECASE)
            for content in frame_contents:
                for pattern, desc in SUSPICIOUS_TEXT:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append(Finding(
                            category="Animation Content Cycling",
                            severity=Severity.HIGH,
                            description=f"@keyframes '{name}' cycles content with suspicious text: {desc}",
                            evidence=f"Keyframe content: \"{content[:80]}...\"" if len(content) > 80 else f"Keyframe content: \"{content}\"",
                            line=line_offset,
                            recommendation="Review all keyframe content values for injection payloads"
                        ))
                        break

    return findings


def scan_html(html_content: str) -> ScanResult:
    """Scan HTML content for GhostCSS patterns."""
    result = ScanResult(target="(html content)")
    lines = html_content.split('\n')

    # Parse HTML
    parser = StyleExtractor()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    # --- Check 1: sr-only class patterns ---
    for line_num, tag, attrs, _ in parser.elements:
        classes = attrs.get('class', '').lower().split()
        for cls in classes:
            if cls in SR_ONLY_CLASSES:
                # Check if element might contain text (look at nearby lines)
                context = '\n'.join(lines[max(0, line_num-1):min(len(lines), line_num+5)])
                # Check for suspicious text in the context
                for pattern, desc in SUSPICIOUS_TEXT:
                    if re.search(pattern, context, re.IGNORECASE):
                        result.findings.append(Finding(
                            category="Screen Reader Only Injection",
                            severity=Severity.CRITICAL,
                            description=f"Element with sr-only class '{cls}' contains suspicious text: {desc}",
                            evidence=f"<{tag} class=\"...{cls}...\"> near line {line_num}",
                            line=line_num,
                            recommendation="Inspect visually-hidden element content for prompt injection"
                        ))
                        break

    # --- Check 2: Inline styles with sr-only patterns ---
    for line_num, tag, attrs, style in parser.inline_styles:
        sr_match_count = count_sr_only_matches(style)
        if sr_match_count >= 3:
            # Element has multiple sr-only properties inline
            context = '\n'.join(lines[max(0, line_num-1):min(len(lines), line_num+5)])
            has_suspicious = False
            for pattern, desc in SUSPICIOUS_TEXT:
                if re.search(pattern, context, re.IGNORECASE):
                    has_suspicious = True
                    break

            severity = Severity.HIGH if has_suspicious else Severity.MEDIUM
            result.findings.append(Finding(
                category="Inline Visual Hiding",
                severity=severity,
                description=f"Element has {sr_match_count} sr-only CSS properties inline",
                evidence=f"<{tag} style=\"{style[:80]}...\"> at line {line_num}",
                line=line_num,
                recommendation="Check if visually-hidden inline-styled element contains instructions"
            ))

        # Check for CSS custom properties with text payloads
        custom_prop_pattern = r'--([a-zA-Z0-9_-]+)\s*:\s*["\']([^"\']+)["\']'
        for prop_match in re.finditer(custom_prop_pattern, style):
            prop_name = prop_match.group(1)
            prop_value = prop_match.group(2)
            for pattern, desc in SUSPICIOUS_TEXT:
                if re.search(pattern, prop_value, re.IGNORECASE):
                    result.findings.append(Finding(
                        category="CSS Custom Property Payload",
                        severity=Severity.CRITICAL,
                        description=f"Custom property --{prop_name} contains suspicious text: {desc}",
                        evidence=f"--{prop_name}: \"{prop_value[:80]}...\"" if len(prop_value) > 80 else f"--{prop_name}: \"{prop_value}\"",
                        line=line_num,
                        recommendation="CSS custom properties are being used to carry injection payloads"
                    ))
                    break

    # --- Check 3: Style blocks ---
    for line_num, css_text in parser.styles:
        # Check for sr-only class definitions
        rule_pattern = r'([.#]?[a-zA-Z0-9_-]+(?:::[a-z]+)?)\s*\{([^}]+)\}'
        for rule_match in re.finditer(rule_pattern, css_text, re.IGNORECASE):
            selector = rule_match.group(1)
            properties = rule_match.group(2)

            sr_count = count_sr_only_matches(properties)
            if sr_count >= 3:
                result.findings.append(Finding(
                    category="sr-only Style Definition",
                    severity=Severity.MEDIUM,
                    description=f"CSS rule '{selector}' defines sr-only pattern ({sr_count} matching properties)",
                    evidence=f"{selector} {{ {properties[:80]}... }}" if len(properties) > 80 else f"{selector} {{ {properties} }}",
                    line=line_num,
                    recommendation="Check which elements use this class and whether they contain suspicious content"
                ))

            # Check structural hiding combinations
            hiding_count = 0
            hiding_types = []
            for pattern, desc in STRUCTURAL_HIDING:
                if re.search(pattern, properties, re.IGNORECASE):
                    hiding_count += 1
                    hiding_types.append(desc)

            if hiding_count >= 3:
                result.findings.append(Finding(
                    category="Structural Hiding",
                    severity=Severity.MEDIUM,
                    description=f"CSS rule '{selector}' uses {hiding_count} hiding techniques: {', '.join(hiding_types)}",
                    evidence=f"{selector} {{ ... }}",
                    line=line_num,
                    recommendation="Element may be visually hidden while retaining DOM presence"
                ))

        # Check content properties
        result.findings.extend(scan_css_content_property(css_text, line_num))

        # Check keyframes
        result.findings.extend(scan_keyframes(css_text, line_num))

    # --- Check 4: Data attribute fragmentation ---
    if len(parser.data_fragments) >= 10:
        # Many single-character data attributes suggest fragmentation
        chars = [v for _, _, v in parser.data_fragments if len(v) == 1]
        if len(chars) >= 10:
            assembled = ''.join(chars[:50])
            result.findings.append(Finding(
                category="Data Attribute Fragmentation",
                severity=Severity.HIGH,
                description=f"Found {len(chars)} single-character data attributes (fragmentation pattern)",
                evidence=f"Assembled preview: \"{assembled}...\"" if len(assembled) > 40 else f"Assembled preview: \"{assembled}\"",
                line=parser.data_fragments[0][0],
                recommendation="Characters may assemble into an injection payload via CSS attr()"
            ))

    # --- Check 5: display:none with content ---
    display_none_pattern = r'<(?:div|span|p|section)[^>]*style\s*=\s*"[^"]*display\s*:\s*none[^"]*"[^>]*>'
    for match in re.finditer(display_none_pattern, html_content, re.IGNORECASE):
        line_num = html_content[:match.start()].count('\n') + 1
        context = html_content[match.start():match.start()+500]
        for pattern, desc in SUSPICIOUS_TEXT:
            if re.search(pattern, context, re.IGNORECASE):
                result.findings.append(Finding(
                    category="Basic Hidden Injection",
                    severity=Severity.LOW,
                    description=f"display:none element contains suspicious text: {desc}",
                    evidence=f"{match.group(0)[:80]}...",
                    line=line_num,
                    recommendation="Most agents filter display:none, but check content for injections"
                ))
                break

    return result


def scan_url(url: str) -> ScanResult:
    """Fetch and scan a URL for GhostCSS patterns."""
    if not HAS_URLLIB:
        print("Error: urllib not available", file=sys.stderr)
        sys.exit(1)

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'GhostCSS-Scanner/1.0 (Security Research)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except urllib.error.URLError as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)

    result = scan_html(html)
    result.target = url
    return result


def scan_file(filepath: str) -> ScanResult:
    """Scan a local HTML file for GhostCSS patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    result = scan_html(html)
    result.target = filepath
    return result


def print_result(result: ScanResult, verbose: bool = False):
    """Print scan results to stdout."""
    severity_colors = {
        Severity.LOW: "\033[33m",       # Yellow
        Severity.MEDIUM: "\033[93m",    # Bright yellow
        Severity.HIGH: "\033[91m",      # Red
        Severity.CRITICAL: "\033[1;91m", # Bold red
    }
    reset = "\033[0m"
    bold = "\033[1m"

    print(f"\n{bold}GhostCSS Scanner Results{reset}")
    print(f"{'=' * 60}")
    print(f"Target: {result.target}")
    print(f"Findings: {len(result.findings)}")

    if result.max_severity:
        color = severity_colors.get(result.max_severity, "")
        print(f"Max Severity: {color}{result.max_severity.value}{reset}")
    else:
        print("Max Severity: \033[32mNONE (clean)\033[0m")

    print(f"{'=' * 60}")

    if not result.findings:
        print("\nNo GhostCSS patterns detected.")
        return

    # Group by category
    categories = {}
    for f in result.findings:
        categories.setdefault(f.category, []).append(f)

    for category, findings in categories.items():
        print(f"\n{bold}[{category}]{reset} ({len(findings)} finding{'s' if len(findings) != 1 else ''})")
        for f in findings:
            color = severity_colors.get(f.severity, "")
            print(f"  {color}{f.severity.value}{reset}: {f.description}")
            if f.line:
                print(f"    Line: {f.line}")
            if verbose:
                print(f"    Evidence: {f.evidence}")
                if f.recommendation:
                    print(f"    Recommendation: {f.recommendation}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="GhostCSS Scanner - Detect CSS-based prompt injection patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url https://example.com
  %(prog)s --file page.html
  %(prog)s --file attacks/02-sr-only/index.html -v
  %(prog)s --file attacks/07-composite/index.html -v --json
        """
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', help='URL to scan')
    group.add_argument('--file', help='Local HTML file to scan')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed evidence')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    if args.url:
        result = scan_url(args.url)
    else:
        result = scan_file(args.file)

    if args.json:
        import json
        output = {
            "target": result.target,
            "finding_count": len(result.findings),
            "max_severity": result.max_severity.value if result.max_severity else None,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity.value,
                    "description": f.description,
                    "evidence": f.evidence,
                    "line": f.line,
                    "recommendation": f.recommendation,
                }
                for f in result.findings
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result, args.verbose)

    # Exit with non-zero if findings detected
    sys.exit(1 if result.findings else 0)


if __name__ == "__main__":
    main()
