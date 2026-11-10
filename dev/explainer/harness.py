"""Offline execution & verification harness for skills/synaptix-explainer.

Loads the real SkillScriptRunner (from synaptix_agent_framework) and real
CompatibilityValidator (from Synaptix_mcp) via spec_from_file_location so
verification runs cleanly on plain stdlib Python without external daemons.
"""

import argparse
import asyncio
import importlib.util
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[1]
WORKSPACES_ROOT = REPO_ROOT.parent
SKILL_DIR = REPO_ROOT / "skills" / "synaptix-explainer"
GOLDEN_DIR = DEV_DIR / "golden"


def _load_module_from_file(mod_name: str, file_path: Path) -> Any:
    if not file_path.is_file():
        raise FileNotFoundError(f"Required module not found at: {file_path}")
    spec = importlib.util.spec_from_file_location(mod_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create module spec for {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_skill_script_runner_mod() -> Any:
    fw_root = Path(
        os.environ.get("SYNAPTIX_FRAMEWORK_PATH")
        or str(WORKSPACES_ROOT / "synaptix_agent_framework")
    )
    runner_file = fw_root / "common" / "skills" / "skill_script_runner.py"
    return _load_module_from_file("_synaptix_skill_script_runner", runner_file)


def load_compatibility_validator_mod() -> Any:
    mcp_root = Path(
        os.environ.get("SYNAPTIX_MCP_PATH")
        or str(WORKSPACES_ROOT / "Synaptix_mcp")
    )
    val_file = mcp_root / "app" / "skills" / "compatibility_validator.py"
    return _load_module_from_file("_synaptix_compat_validator", val_file)


def load_skill_files() -> Dict[str, str]:
    files: Dict[str, str] = {}
    for path in sorted(SKILL_DIR.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and not path.name.startswith("."):
            rel = path.relative_to(SKILL_DIR).as_posix()
            files[rel] = path.read_text(encoding="utf-8")
    return files


def load_siblings_and_entry(shuffle_seed: Optional[int] = None) -> Tuple[str, Dict[str, str]]:
    all_files = load_skill_files()
    entry_code = all_files["scripts/illustrate.py"]
    sib_items: List[Tuple[str, str]] = [
        (rel, content)
        for rel, content in all_files.items()
        if rel.endswith(".py") and rel != "scripts/illustrate.py"
    ]
    if shuffle_seed is not None:
        rng = random.Random(shuffle_seed)
        rng.shuffle(sib_items)
    return entry_code, dict(sib_items)


_RUNNER_INSTANCE: Any = None


def get_runner() -> Any:
    global _RUNNER_INSTANCE
    if _RUNNER_INSTANCE is None:
        ssr_mod = load_skill_script_runner_mod()
        backend = ssr_mod.InProcessBackend()
        ssr_mod.SkillScriptRunner.set_backend(backend)
        _RUNNER_INSTANCE = backend
    return _RUNNER_INSTANCE


def run_sandboxed(
    inputs: Dict[str, Any],
    shuffle_seed: Optional[int] = None,
) -> Dict[str, Any]:
    runner = get_runner()
    entry_code, siblings = load_siblings_and_entry(shuffle_seed=shuffle_seed)
    return asyncio.run(runner.run(entry_code, inputs, sibling_modules=siblings))


def run_native(inputs: Dict[str, Any]) -> Dict[str, Any]:
    if str(SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(SKILL_DIR))
    entry_path = SKILL_DIR / "scripts" / "illustrate.py"
    ns: Dict[str, Any] = {"inputs": inputs}
    code = compile(entry_path.read_text(encoding="utf-8"), str(entry_path), "exec")
    exec(code, ns, ns)
    return ns["result"]


def canonical_specs() -> Dict[str, Dict[str, Any]]:
    """Canonical valid specs for all 10 templates."""
    return {
        "title": {
            "template": "title",
            "eyebrow": "ARCHITECTURE BRIEFING",
            "title": "Zero-Trust Identity at the Edge",
            "footer": "Synaptix Engineering · Q4",
            "data_kind": "illustrative",
            "content": {
                "subtitle": "Replacing perimeter firewalls with cryptographic workload attestation across every request.",
                "icon": "shield",
            },
        },
        "bar-chart": {
            "template": "bar-chart",
            "eyebrow": "WEEKLY POS SUMMARY",
            "title": "Espresso Drinks Sold by Day",
            "data_kind": "sourced",
            "source": "Store #14 POS export, Week 12",
            "content": {
                "y_label": "Cups",
                "items": [
                    {"label": "Mon", "value": "120+15"},
                    {"label": "Tue", "value": 142},
                    {"label": "Wed", "value": 158},
                    {"label": "Thu", "value": 164},
                    {"label": "Fri", "value": 210},
                ],
            },
        },
        "line-chart": {
            "template": "line-chart",
            "eyebrow": "ADOPTION CURVE",
            "title": "Active Workspaces Across Tiers",
            "data_kind": "sourced",
            "source": "Product analytics warehouse, FY25",
            "content": {
                "y_label": "Workspaces",
                "series": [
                    {
                        "name": "Enterprise",
                        "points": [
                            {"x": "Q1", "y": 120},
                            {"x": "Q2", "y": 165},
                            {"x": "Q3", "y": 218},
                            {"x": "Q4", "y": 290},
                        ],
                    },
                    {
                        "name": "Self-Serve",
                        "points": [
                            {"x": "Q1", "y": 95},
                            {"x": "Q2", "y": 118},
                            {"x": "Q3", "y": 144},
                            {"x": "Q4", "y": 176},
                        ],
                    },
                ],
            },
        },
        "donut-chart": {
            "template": "donut-chart",
            "eyebrow": "CLOUD FINOPS",
            "title": "Monthly Infrastructure Spend Share",
            "data_kind": "sourced",
            "source": "AWS Cost Explorer, March close",
            "content": {
                "center_label": "USD $84K",
                "items": [
                    {"label": "GPU Inference", "value": 38},
                    {"label": "Managed Postgres", "value": 22},
                    {"label": "Kubernetes", "value": 15},
                    {"label": "Object Storage", "value": 9},
                ],
            },
        },
        "comparison": {
            "template": "comparison",
            "eyebrow": "RETRIEVAL DESIGN",
            "title": "BM25 Lexical vs Hybrid Vector RAG",
            "data_kind": "illustrative",
            "content": {
                "columns": [
                    {
                        "title": "BM25 Lexical Only",
                        "icon": "database",
                        "points": [
                            "Sub-10ms lookup with zero embedding cost",
                            "Exact SKU, code symbol, and acronym precision",
                            "Misses paraphrases and cross-lingual synonyms",
                        ],
                    },
                    {
                        "title": "Hybrid + Reranker",
                        "icon": "bolt",
                        "points": [
                            "Combines dense recall with exact term matching",
                            "Handles natural-language questions reliably",
                            "Adds ~45ms embedding + reranker latency",
                        ],
                    },
                ],
                "verdict": "Use Hybrid + Reranker for user Q&A; keep BM25 for exact identifier lookup.",
            },
        },
        "process": {
            "template": "process",
            "eyebrow": "RELEASE PIPELINE",
            "title": "How Canary Deployments Reach Production",
            "data_kind": "illustrative",
            "content": {
                "steps": [
                    {"title": "Build & Sign", "detail": "Compile immutable image and attach SBOM provenance.", "icon": "lock"},
                    {"title": "5% Canary", "detail": "Route live traffic slice while watching error budgets.", "icon": "chart"},
                    {"title": "Automated Gate", "detail": "Compare P99 latency and 5xx rate over 15 minutes.", "icon": "shield"},
                    {"title": "Full Rollout", "detail": "Shift 100% traffic or instant-rollback on breach.", "icon": "check"},
                ],
            },
        },
        "cycle": {
            "template": "cycle",
            "eyebrow": "FLYWHEEL",
            "title": "RLHF Model Quality Improvement Loop",
            "data_kind": "illustrative",
            "content": {
                "center": "Continuous Eval",
                "stages": [
                    {"title": "Sample Prompts", "detail": "Collect hard production edge cases."},
                    {"title": "Rank Outputs", "detail": "Annotators score pairwise responses."},
                    {"title": "Train Reward", "detail": "Fit preference model on deltas."},
                    {"title": "Policy Update", "detail": "Fine-tune and ship gated checkpoint."},
                ],
            },
        },
        "timeline": {
            "template": "timeline",
            "eyebrow": "MIGRATION ROADMAP",
            "title": "Monolith to Event-Driven Cutover",
            "data_kind": "illustrative",
            "content": {
                "events": [
                    {"when": "Weeks 1-2", "title": "Outbox Dual-Write", "detail": "Publish domain events from existing transactions."},
                    {"when": "Weeks 3-4", "title": "Shadow Consumers", "detail": "Verify projection parity without serving reads."},
                    {"when": "Week 6", "title": "Read Cutover", "detail": "Switch API queries to materialized views."},
                    {"when": "Week 8", "title": "Retire Legacy", "detail": "Drop monolith write paths after 14-day soak."},
                ],
            },
        },
        "hub": {
            "template": "hub",
            "eyebrow": "PLATFORM ARCHITECTURE",
            "title": "Four Pillars of Observable Services",
            "data_kind": "illustrative",
            "content": {
                "center": {
                    "title": "OpenTelemetry Core",
                    "detail": "Unified SDK correlating signals via shared trace context.",
                },
                "spokes": [
                    {"title": "Metrics", "detail": "RED counters and SLO burn alerts.", "icon": "chart"},
                    {"title": "Distributed Traces", "detail": "End-to-end request waterfall spans.", "icon": "bolt"},
                    {"title": "Structured Logs", "detail": "JSON events indexed by trace_id.", "icon": "database"},
                    {"title": "Profiles", "detail": "CPU and heap flamegraphs in prod.", "icon": "gear"},
                ],
            },
        },
        "recap": {
            "template": "recap",
            "eyebrow": "EXECUTIVE SUMMARY",
            "title": "Three Rules for Reliable Agent Tooling",
            "footer": "Synaptix Architecture Guidelines",
            "data_kind": "illustrative",
            "content": {
                "points": [
                    {
                        "title": "Validate All Errors in One Pass",
                        "detail": "Return every broken field path together so the model repairs specs in one retry.",
                    },
                    {
                        "title": "Keep Layout Math Deterministic",
                        "detail": "Let code compute coordinates, wrapping, and WCAG contrast instead of freehand SVG.",
                    },
                    {
                        "title": "Mark Unsourced Numbers Clearly",
                        "detail": "Separate real cited figures from illustrative examples to preserve user trust.",
                    },
                ],
            },
        },
    }


def generate_goldens(out_dir: Path = GOLDEN_DIR) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = canonical_specs()
    written: List[Path] = []
    for tpl_name, base_spec in specs.items():
        for theme_name in ("paper", "ink"):
            spec_copy = json.loads(json.dumps(base_spec))
            spec_copy["theme"] = theme_name
            spec_copy["aspect"] = "wide"
            res = run_sandboxed({"spec": spec_copy, "include_svg": True})
            if "errors" in res:
                raise RuntimeError(f"Golden failed for {tpl_name}/{theme_name}: {res['errors']}")
            svg_path = out_dir / f"{tpl_name}__{theme_name}.svg"
            svg_path.write_text(res["svg"], encoding="utf-8")
            written.append(svg_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="synaptix-explainer offline harness")
    parser.add_argument("--generate-goldens", action="store_true", help="Write 20 golden SVGs")
    parser.add_argument("--spec", type=str, help="Path to JSON spec file")
    parser.add_argument("--out", type=str, help="Output HTML file path")
    args = parser.parse_args()

    if args.generate_goldens:
        paths = generate_goldens()
        print(f"Generated {len(paths)} golden SVGs in {GOLDEN_DIR}")
        return

    if args.spec:
        spec_obj = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        res = run_sandboxed({"spec": spec_obj})
        if args.out and "html_app" in res:
            Path(args.out).write_text(res["html_app"], encoding="utf-8")
            print(f"Wrote {args.out} ({len(res['html_app'])} chars)")
        else:
            print(json.dumps(res, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
