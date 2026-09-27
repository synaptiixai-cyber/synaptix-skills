#!/usr/bin/env python3
"""
Synaptix Diagram Architect - Mermaid AST & Syntax Validator

A zero-dependency, deterministic validator and auto-fixer for Mermaid diagrams.
Designed to catch syntax errors, reserved word conflicts, and security violations
before diagrams are rendered in client runtimes.

Usage:
  # Validate inline code
  python3 validate_mermaid.py --code "flowchart TD\n  A[Start] --> B[End]"

  # Validate a file
  python3 validate_mermaid.py --file diagram.mmd

  # Return JSON output (ideal for AI tool calls)
  python3 validate_mermaid.py --code "flowchart TD..." --json

  # Attempt auto-fix for common LLM mistakes
  python3 validate_mermaid.py --code "flowchart TD\n  A[Step (1)] --> end --> B" --fix
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Tuple

# Recognised Mermaid diagram keywords (must be first non-comment line)
MERMAID_KEYWORDS = (
    "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram",
    "stateDiagram-v2", "erDiagram", "gantt", "pie", "gitGraph",
    "mindmap", "timeline", "quadrantChart", "sankey-beta", "block-beta",
    "packet-beta", "xychart-beta", "requirementDiagram", "journey", "graph"
)

# Reserved words that cause parser conflicts when used as bare node IDs
RESERVED_NODE_IDS = {
    "end": "Conflicts with subgraph 'end' delimiter",
    "default": "Conflicts with theme / class 'default' keyword",
    "style": "Reserved directive keyword",
    "linkStyle": "Reserved styling directive",
    "classDef": "Reserved class definition keyword",
    "class": "Reserved class assignment keyword",
    "call": "Reserved interaction directive",
    "href": "Reserved hyperlink directive",
    "click": "Reserved click handler directive",
    "subgraph": "Reserved structural keyword",
    "interpolate": "Reserved interpolation keyword",
}

# Dangerous constructs (XSS / policy violations)
SECURITY_POLICIES = [
    (re.compile(r'\bclick\s+\S+\s+(href|call)\b', re.I), "click+href/call interaction handler"),
    (re.compile(r'\bhref\s*["\']?https?:', re.I), "External URL hyperlink"),
    (re.compile(r'javascript\s*:', re.I), "javascript: pseudo-protocol"),
    (re.compile(r'\bcallback\b', re.I), "Unsafe callback directive"),
    (re.compile(r'<\s*script\b', re.I), "Inline <script> tag"),
    (re.compile(r'<\s*iframe\b', re.I), "Embedded <iframe> tag"),
    (re.compile(r'<\s*object\b', re.I), "Embedded <object> tag"),
    (re.compile(r'<\s*embed\b', re.I), "Embedded <embed> tag"),
]


def strip_directives(src: str) -> str:
    """Removes frontmatter and %%{init}%% directives before syntax checking."""
    # Remove frontmatter --- ... ---
    clean = re.sub(r"\A\s*---\s*\r?\n[\s\S]*?\r?\n---\s*\r?\n", "", src)
    # Remove %%{init}%% directives
    clean = re.sub(r"%%\{[\s\S]*?\}%%[ \t]*\r?\n?", "", clean)
    return clean.strip()


def validate_mermaid(src: str, strict: bool = False) -> Dict[str, Any]:
    """
    Validates Mermaid diagram source code.
    Returns:
      {
        "valid": bool,
        "diagram_type": str,
        "errors": list[dict],
        "warnings": list[dict],
        "line_count": int
      }
    """
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if not src or not src.strip():
        return {
            "valid": False,
            "diagram_type": "unknown",
            "errors": [{"line": 1, "message": "Source code is empty"}],
            "warnings": [],
            "line_count": 0,
        }

    raw_lines = src.splitlines()
    clean_src = strip_directives(src)
    lines = clean_src.splitlines()

    # 1. Security & Policy Violations
    for line_idx, line in enumerate(raw_lines, 1):
        for pattern, label in SECURITY_POLICIES:
            if pattern.search(line):
                errors.append({
                    "line": line_idx,
                    "type": "security_violation",
                    "message": f"Forbidden construct: {label}",
                    "snippet": line.strip()
                })

    # 2. Extract First Meaningful Line (Keyword)
    content_lines = [
        (idx + 1, l) for idx, l in enumerate(lines)
        if l.strip() and not l.strip().startswith("%%")
    ]

    if not content_lines:
        return {
            "valid": False,
            "diagram_type": "unknown",
            "errors": [{"line": 1, "message": "No diagram definition found (only comments or empty lines)"}],
            "warnings": warnings,
            "line_count": len(raw_lines),
        }

    first_line_num, first_line = content_lines[0]
    first_token = first_line.strip().split()[0]
    normalized_token = first_token.replace("-beta", "").replace("-v2", "")

    diagram_type = "unknown"
    for kw in MERMAID_KEYWORDS:
        if first_line.strip().startswith(kw):
            diagram_type = kw
            break

    if diagram_type == "unknown":
        errors.append({
            "line": first_line_num,
            "type": "invalid_header",
            "message": f"First line '{first_line.strip()}' does not start with a recognized Mermaid diagram keyword.",
            "expected": list(MERMAID_KEYWORDS[:8])
        })

    # Warn if deprecated 'graph' is used instead of 'flowchart'
    if diagram_type == "graph":
        warnings.append({
            "line": first_line_num,
            "type": "deprecation",
            "message": "'graph' is legacy syntax; prefer 'flowchart' for modern features and curve control."
        })

    # 3. Structural & Line-by-Line Checks
    subgraph_depth = 0

    for line_num, line in content_lines:
        s_line = line.strip()

        # Track subgraph nesting
        if re.match(r"^subgraph\b", s_line):
            subgraph_depth += 1
        elif s_line == "end" and subgraph_depth > 0:
            subgraph_depth -= 1

        # Check: Single '%' comment error (Must be '%%')
        if s_line.startswith("%") and not s_line.startswith("%%"):
            errors.append({
                "line": line_num,
                "type": "invalid_comment",
                "message": "Invalid comment syntax. Mermaid comments must start with '%%' (not a single '%').",
                "snippet": s_line
            })

        # Check: Reserved Node IDs as source or target
        for reserved_id, reason in RESERVED_NODE_IDS.items():
            # Match bare word used with an arrow, e.g. "end --> B" or "A --> end"
            pattern_src = rf'\b{reserved_id}\b\s*(-{1,3}>?|==>|\.-+>)'
            pattern_tgt = rf'(-{1,3}>?|==>|\.-+>)\s*\b{reserved_id}\b'
            
            # Allow "end" if it's closing a subgraph
            if reserved_id == "end" and s_line == "end":
                continue

            if re.search(pattern_src, s_line) or re.search(pattern_tgt, s_line):
                # Check if it was quoted, like id["end"]
                if not re.search(rf'\[\s*["\'].*?\b{reserved_id}\b.*?["\']\s*\]', s_line):
                    errors.append({
                        "line": line_num,
                        "type": "reserved_identifier",
                        "message": f"Identifier '{reserved_id}' is a reserved keyword ({reason}). Rename to '{reserved_id}_node' or wrap label in quotes: id[\"{reserved_id}\"].",
                        "snippet": s_line
                    })

        # Check: Unquoted parentheses or brackets in flowchart node labels
        # e.g., A[Step (1) Run] breaks parsing unless wrapped in double quotes A["Step (1) Run"]
        if diagram_type in ("flowchart", "graph"):
            label_match = re.search(r'^\s*(\w+)\s*\[([^"\'\]]*)\]', s_line)
            if label_match:
                inner = label_match.group(2)
                if any(c in inner for c in "(){}[]:;"):
                    errors.append({
                        "line": line_num,
                        "type": "unquoted_special_char",
                        "message": f"Node label '{inner}' contains special characters '()[]{{}}:;'. Always wrap labels in double quotes, e.g., [\"{inner}\"].",
                        "snippet": s_line
                    })

            # Check for illegal node ID starting characters (e.g., single 'o' or 'x' forming circle/cross arrows)
            bad_id_match = re.search(r'^\s*([oxOX])(\s*\[|\s*\(|\s*-->)', s_line)
            if bad_id_match:
                warnings.append({
                    "line": line_num,
                    "type": "ambiguous_identifier",
                    "message": f"Single character node ID '{bad_id_match.group(1)}' can conflict with Mermaid circle/cross arrow heads. Use descriptive IDs.",
                    "snippet": s_line
                })

    # Subgraph balance check
    if subgraph_depth != 0:
        errors.append({
            "line": len(raw_lines),
            "type": "unbalanced_subgraph",
            "message": f"Unbalanced subgraphs: {subgraph_depth} unclosed 'subgraph' blocks. Ensure every 'subgraph' has a matching 'end'."
        })

    is_valid = len(errors) == 0 if not strict else (len(errors) == 0 and len(warnings) == 0)

    return {
        "valid": is_valid,
        "diagram_type": diagram_type,
        "errors": errors,
        "warnings": warnings,
        "line_count": len(raw_lines),
    }


def auto_fix_mermaid(src: str) -> Tuple[str, List[str]]:
    """
    Attempts deterministic auto-fixes for the most common LLM syntax bugs:
      1. Converts single '%' comments to '%%'.
      2. Renames bare 'end' node identifiers to 'end_node'.
      3. Wraps unquoted flowchart node labels containing special chars in double quotes.
      4. Strips dangerous script / iframe / javascript tags.
    """
    fixes: List[str] = []
    lines = src.splitlines()
    fixed_lines: List[str] = []

    for line in lines:
        new_line = line

        # Fix 1: Single % comment to %%
        if new_line.strip().startswith("%") and not new_line.strip().startswith("%%"):
            new_line = re.sub(r"^\s*%(?!%)", "%% ", new_line)
            fixes.append("Converted single '%' comment to '%%'")

        # Fix 2: Bare 'end' identifier in edge
        if not new_line.strip() == "end":
            if re.search(r'\bend\b\s*(-{1,3}>?|==>|\.-+>)', new_line) or re.search(r'(-{1,3}>?|==>|\.-+>)\s*\bend\b', new_line):
                new_line = re.sub(r'\bend\b', 'end_node', new_line)
                fixes.append("Renamed conflicting reserved ID 'end' to 'end_node'")

        # Fix 3: Unquoted parentheses or brackets in node label
        def quote_label(m: re.Match) -> str:
            node_id = m.group(1)
            content = m.group(2)
            if any(c in content for c in "(){}[]:;/") and not (content.startswith('"') and content.endswith('"')):
                safe = content.replace('"', "'")
                fixes.append(f"Auto-quoted special characters in node label for '{node_id}'")
                return f'{node_id}["{safe}"]'
            return m.group(0)

        new_line = re.sub(r'(\b\w+\b)\s*\[([^\]]+)\]', quote_label, new_line)

        # Fix 4: Strip XSS / script
        for pattern, label in SECURITY_POLICIES:
            if pattern.search(new_line):
                new_line = f"%% [SECURITY STRIPPED] {label}"
                fixes.append(f"Stripped security violation: {label}")

        fixed_lines.append(new_line)

    return "\n".join(fixed_lines), fixes


def main():
    parser = argparse.ArgumentParser(description="Synaptix Mermaid AST & Syntax Validator")
    parser.add_argument("--code", type=str, help="Inline Mermaid code string")
    parser.add_argument("--file", type=str, help="Path to Mermaid file (.mmd or .txt)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--fix", action="store_true", help="Auto-repair common syntax errors")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")

    args = parser.parse_args()

    content = ""
    if args.code:
        content = args.code
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            if args.json:
                print(json.dumps({"valid": False, "errors": [{"message": str(e)}]}))
            else:
                print(f"Error reading file {args.file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin if piped
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            parser.print_help()
            sys.exit(1)

    if args.fix:
        repaired, applied_fixes = auto_fix_mermaid(content)
        verdict = validate_mermaid(repaired, strict=args.strict)
        if args.json:
            print(json.dumps({
                "repaired_code": repaired,
                "applied_fixes": applied_fixes,
                "validation": verdict
            }, indent=2))
        else:
            if applied_fixes:
                print(f"Applied {len(applied_fixes)} fix(es):", file=sys.stderr)
                for f in applied_fixes:
                    print(f"  ✓ {f}", file=sys.stderr)
            print(repaired)
        sys.exit(0 if verdict["valid"] else 1)

    verdict = validate_mermaid(content, strict=args.strict)

    if args.json:
        print(json.dumps(verdict, indent=2))
    else:
        status_symbol = "✓" if verdict["valid"] else "✗"
        status_text = "VALID" if verdict["valid"] else "INVALID"
        print(f"\n{status_symbol} Diagram Status: {status_text} (Type: {verdict['diagram_type']})")
        
        if verdict["errors"]:
            print(f"\nErrors ({len(verdict['errors'])}):")
            for err in verdict["errors"]:
                line_str = f" [Line {err['line']}]" if "line" in err else ""
                print(f"  •{line_str} {err['message']}")
                if "snippet" in err:
                    print(f"      Code: {err['snippet']}")

        if verdict["warnings"]:
            print(f"\nWarnings ({len(verdict['warnings'])}):")
            for w in verdict["warnings"]:
                line_str = f" [Line {w['line']}]" if "line" in w else ""
                print(f"  •{line_str} {w['message']}")

        print(f"\nTotal Lines: {verdict['line_count']}")

    sys.exit(0 if verdict["valid"] else 1)


if __name__ == "__main__":
    main()
