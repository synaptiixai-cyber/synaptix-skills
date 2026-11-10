"""Comprehensive offline test suite for skills/synaptix-explainer."""

import ast
import json
import random
import re
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict

TESTS_DIR = Path(__file__).resolve().parent
DEV_EXPL_DIR = TESTS_DIR.parent
if str(DEV_EXPL_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_EXPL_DIR))

import harness  # noqa: E402

if str(harness.SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(harness.SKILL_DIR))

from illus import calc, icons, layout, text, themes  # noqa: E402


def max_stress_specs() -> Dict[str, Dict[str, Any]]:
    """Max-item, near-max-character stress specs for all 10 templates."""
    return {
        "title": {
            "template": "title",
            "eyebrow": "STRATEGIC PLATFORM ARCHITECTURE 2026",
            "title": "Deterministic Visual Explainers Without Freehand SVG Drift",
            "footer": "Verified across wide and square viewports with strict WCAG AA tokens",
            "data_kind": "sourced",
            "source": "Synaptix Engineering Design Review Board, Q4 Architecture Benchmark",
            "content": {
                "subtitle": "Every coordinate, line wrap, contrast check, and animation delay is computed by pure Python rules.",
                "icon": "globe",
            },
        },
        "bar-chart": {
            "template": "bar-chart",
            "eyebrow": "EIGHT-BUCKET THROUGHPUT BENCHMARK",
            "title": "Sustained Requests per Second Across Eight Storage Engines",
            "footer": "Measured on identical 16-vCPU arm64 instances under p99 < 25ms SLO",
            "data_kind": "sourced",
            "source": "Internal Storage Benchmark Suite v4.2, Run #912",
            "content": {
                "y_label": "Throughput (k req/s)",
                "items": [
                    {"label": "Memory KV", "value": 184.5, "unit": "k"},
                    {"label": "Local NVMe", "value": 142.0, "unit": "k"},
                    {"label": "Redis Shard", "value": 119.4, "unit": "k"},
                    {"label": "Scylla Cluster", "value": 96.8, "unit": "k"},
                    {"label": "Postgres Read", "value": 64.2, "unit": "k"},
                    {"label": "Postgres Write", "value": 38.9, "unit": "k"},
                    {"label": "Cloud Spanner", "value": 31.5, "unit": "k"},
                    {"label": "Cold Parquet", "value": 12.4, "unit": "k"},
                ],
            },
        },
        "line-chart": {
            "template": "line-chart",
            "eyebrow": "TWELVE-MONTH MULTI-SERIES COHORT TREND",
            "title": "Monthly Net Retention Across Three Customer Segments",
            "footer": "Trailing 30-day rolling net dollar retention indexed at 100",
            "data_kind": "sourced",
            "source": "Finance & RevOps Data Warehouse, FY25 Close",
            "content": {
                "y_label": "Net retention (%)",
                "series": [
                    {
                        "name": "Enterprise Global",
                        "points": [
                            {"x": "Jan", "y": 108}, {"x": "Feb", "y": 111}, {"x": "Mar", "y": 114},
                            {"x": "Apr", "y": 116}, {"x": "May", "y": 119}, {"x": "Jun", "y": 122},
                            {"x": "Jul", "y": 124}, {"x": "Aug", "y": 127}, {"x": "Sep", "y": 129},
                            {"x": "Oct", "y": 131}, {"x": "Nov", "y": 134}, {"x": "Dec", "y": 138},
                        ],
                    },
                    {
                        "name": "Mid-Market Teams",
                        "points": [
                            {"x": "Jan", "y": 101}, {"x": "Feb", "y": 103}, {"x": "Mar", "y": 104},
                            {"x": "Apr", "y": 106}, {"x": "May", "y": 108}, {"x": "Jun", "y": 109},
                            {"x": "Jul", "y": 111}, {"x": "Aug", "y": 112}, {"x": "Sep", "y": 114},
                            {"x": "Oct", "y": 115}, {"x": "Nov", "y": 117}, {"x": "Dec", "y": 119},
                        ],
                    },
                    {
                        "name": "Self-Serve Builders",
                        "points": [
                            {"x": "Jan", "y": 94}, {"x": "Feb", "y": 95}, {"x": "Mar", "y": 96},
                            {"x": "Apr", "y": 98}, {"x": "May", "y": 99}, {"x": "Jun", "y": 101},
                            {"x": "Jul", "y": 100}, {"x": "Aug", "y": 102}, {"x": "Sep", "y": 103},
                            {"x": "Oct", "y": 104}, {"x": "Nov", "y": 105}, {"x": "Dec", "y": 107},
                        ],
                    },
                ],
            },
        },
        "donut-chart": {
            "template": "donut-chart",
            "eyebrow": "SIX-SLICE COMPUTE ALLOCATION",
            "title": "Production Cluster GPU Hours by Workload Category",
            "footer": "Excludes spot-preempted staging jobs",
            "data_kind": "sourced",
            "source": "Kubernetes Kubecost Telemetry, Q4",
            "content": {
                "center_label": "142K GPU-HR",
                "items": [
                    {"label": "Realtime Serving", "value": 52},
                    {"label": "Batch Embeddings", "value": 29},
                    {"label": "Reranker Fleet", "value": 21},
                    {"label": "Fine-Tune Runs", "value": 18},
                    {"label": "Safety Guardrails", "value": 13},
                    {"label": "Eval Harness", "value": 9},
                ],
            },
        },
        "comparison": {
            "template": "comparison",
            "eyebrow": "THREE-WAY RUNTIME EVALUATION",
            "title": "Choosing an Execution Sandbox for Untrusted Agent Code",
            "footer": "Evaluated across startup latency, memory overhead, and isolation",
            "data_kind": "illustrative",
            "content": {
                "columns": [
                    {
                        "title": "AST In-Process Guard",
                        "icon": "bolt",
                        "points": [
                            "Sub-5ms warm execution inside worker memory space",
                            "Strict stdlib facade blocks I/O and imports statically",
                            "Zero container cold-start or network serialization cost",
                            "Best fit for deterministic pure-Python data compilers",
                            "Cannot load native C extensions or external binaries",
                        ],
                    },
                    {
                        "title": "Subprocess Jail",
                        "icon": "lock",
                        "points": [
                            "Separate OS process enforces wall-clock kill and RLIMIT",
                            "Survives runaway CPU loops cleanly via SIGKILL",
                            "Adds 35-80ms process spawn overhead per invocation",
                            "Strong default when running user-supplied regexes",
                            "Still shares host kernel syscall surface without seccomp",
                        ],
                    },
                    {
                        "title": "MicroVM Boundary",
                        "icon": "shield",
                        "points": [
                            "Dedicated guest kernel isolates untrusted native libs",
                            "Supports full third-party wheels and filesystem scratch",
                            "120-300ms snapshot restore plus higher RAM footprint",
                            "Ideal for arbitrary multi-language code interpreter tools",
                            "Requires dedicated host KVM orchestration fleet",
                        ],
                    },
                ],
                "verdict": "Use AST + subprocess for pure-Python skills; reserve MicroVMs for native code.",
            },
        },
        "process": {
            "template": "process",
            "eyebrow": "SIX-STAGE INCIDENT WORKFLOW",
            "title": "End-to-End Automated Sev-1 Mitigation Lifecycle",
            "footer": "Target median time-to-mitigate under 8 minutes",
            "data_kind": "illustrative",
            "content": {
                "steps": [
                    {"title": "Burn Alert Fires", "detail": "Multi-window SLO alert detects fast error-budget burn.", "icon": "bolt"},
                    {"title": "Triage Context", "detail": "Correlate recent deploys, flags, and top failing traces.", "icon": "chart"},
                    {"title": "Page On-Call", "detail": "Assemble incident channel with pre-filled runbook links.", "icon": "user"},
                    {"title": "Safe Rollback", "detail": "Drain canary or revert feature flag in one atomic step.", "icon": "shield"},
                    {"title": "Verify Recovery", "detail": "Confirm P99 latency and synthetic probes stabilize.", "icon": "check"},
                    {"title": "Action Review", "detail": "Capture root cause and add regression guardrail test.", "icon": "lock"},
                ],
            },
        },
        "cycle": {
            "template": "cycle",
            "eyebrow": "SIX-STAGE PRODUCT FLYWHEEL",
            "title": "Closed-Loop Retrieval Quality Optimization Cycle",
            "footer": "Runs continuously every weekly release train",
            "data_kind": "illustrative",
            "content": {
                "center": "Eval Flywheel",
                "stages": [
                    {"title": "Log Queries", "detail": "Sample anonymized low-confidence retrieval traces."},
                    {"title": "Mine Hard Negatives", "detail": "Cluster near-miss chunks that confused reranking."},
                    {"title": "Curate Gold Set", "detail": "Domain reviewers verify ground-truth citations."},
                    {"title": "Tune Hybrid Weights", "detail": "Sweep BM25 vs dense alpha on held-out slices."},
                    {"title": "Shadow Replay", "detail": "Score candidate index against live traffic offline."},
                    {"title": "Promote Index", "detail": "Swap alias atomically with zero query downtime."},
                ],
            },
        },
        "timeline": {
            "template": "timeline",
            "eyebrow": "SEVEN-MILESTONE SECURITY ROADMAP",
            "title": "Enterprise SOC2 Type II Readiness Schedule",
            "footer": "Tracked weekly with executive security steering committee",
            "data_kind": "illustrative",
            "content": {
                "events": [
                    {"when": "Month 1", "title": "Scope & Gap Audit", "detail": "Map trust service criteria across all production systems."},
                    {"when": "Month 2", "title": "IAM Hardening", "detail": "Enforce hardware SSO keys and short-lived workload JWTs."},
                    {"when": "Month 3", "title": "Audit Logging", "detail": "Stream immutable admin and data-access events to SIEM."},
                    {"when": "Month 4", "title": "DR Game Day", "detail": "Execute full regional failover drill within RPO/RTO."},
                    {"when": "Month 5", "title": "Penetration Test", "detail": "Remediate external third-party red-team findings."},
                    {"when": "Month 6", "title": "Observation Window", "detail": "Collect automated continuous control evidence daily."},
                    {"when": "Month 9", "title": "Auditor Sign-Off", "detail": "Receive final unqualified SOC2 Type II attestation."},
                ],
            },
        },
        "hub": {
            "template": "hub",
            "eyebrow": "SIX-SPOKE GOVERNANCE MODEL",
            "title": "Core Capabilities of the Synaptix Control Plane",
            "footer": "Shared foundation across chat, workflows, and background agents",
            "data_kind": "illustrative",
            "content": {
                "center": {
                    "title": "Agent Control Plane",
                    "detail": "Policy, identity, and execution router for every tenant tool call.",
                },
                "spokes": [
                    {"title": "Tenant Auth", "detail": "Scoped service JWTs with strict tenant isolation.", "icon": "lock"},
                    {"title": "Skill Sandbox", "detail": "Deterministic AST validation and resource caps.", "icon": "shield"},
                    {"title": "Artifact Store", "detail": "Out-of-band HTML and media streaming to Canvas.", "icon": "cloud"},
                    {"title": "Tool Registry", "detail": "Versioned schemas and opt-in agent capabilities.", "icon": "gear"},
                    {"title": "Cost Metering", "detail": "Per-turn token, search, and compute attribution.", "icon": "chart"},
                    {"title": "Audit Trail", "detail": "Structured provenance logs for every action.", "icon": "database"},
                ],
            },
        },
        "recap": {
            "template": "recap",
            "eyebrow": "FIVE KEY ARCHITECTURAL DECISIONS",
            "title": "Why Declarative Explainer Specs Beat Raw LLM SVG",
            "footer": "Adopted across Synaptix visual skill packages",
            "data_kind": "illustrative",
            "content": {
                "points": [
                    {
                        "title": "Zero Coordinate Hallucination",
                        "detail": "Models pick structure and copy while deterministic Python owns pixel geometry.",
                    },
                    {
                        "title": "Single-Pass Multi-Error Feedback",
                        "detail": "Every invalid field path returns at once with an actionable fix hint.",
                    },
                    {
                        "title": "Guaranteed WCAG AA Contrast",
                        "detail": "Theme tokens are checked and auto-adjusted to 4.5:1 relative luminance.",
                    },
                    {
                        "title": "Honest Data Provenance",
                        "detail": "Unsourced illustrative numbers automatically display a clear disclosure badge.",
                    },
                    {
                        "title": "Self-Contained Offline HTML",
                        "detail": "Strict CSP with zero external fonts, CDNs, or network dependencies.",
                    },
                ],
            },
        },
    }


class TestSynaptixExplainer(unittest.TestCase):
    """End-to-end verification of registration, sandbox, math, layout, security, and goldens."""

    def test_01_compatibility_validator_and_budgets(self) -> None:
        files = harness.load_skill_files()
        self.assertIn("SKILL.md", files)
        self.assertIn("scripts/illustrate.py", files)

        # SKILL.md < 6 KB + required frontmatter & negative routing rules
        skill_md = files["SKILL.md"]
        self.assertLess(len(skill_md.encode("utf-8")), 6144, "SKILL.md must stay under 6 KB")
        for neg_tool in (
            "generate_illustration",
            "generate_diagram",
            "generate_chart",
            "create_app",
            "motionsites_web_builder",
        ):
            self.assertIn(neg_tool, skill_md)

        # Real Synaptix CompatibilityValidator check
        compat_mod = harness.load_compatibility_validator_mod()
        validator = compat_mod.CompatibilityValidator()
        validator.validate(None, files)

        # Per-module byte (< 25 KB) and AST (< 10,000 nodes) budgets + individual AST compile check
        runner = harness.get_runner()
        entry_code, siblings = harness.load_siblings_and_entry()
        compiled_siblings, combined_modules = runner._prepare_siblings(siblings)
        self.assertEqual(
            len(compiled_siblings),
            len(siblings),
            "Every sibling module in illus/ must pass SkillScriptRunner._compile without being skipped!",
        )
        for rel_path, content in files.items():
            if rel_path.endswith(".py"):
                byte_len = len(content.encode("utf-8"))
                self.assertLess(byte_len, 25600, f"{rel_path} exceeds 25 KB budget ({byte_len}B)")
                node_count = sum(1 for _ in ast.walk(ast.parse(content)))
                self.assertLess(node_count, 10000, f"{rel_path} exceeds 10,000 AST nodes")
                runner._compile(content, module_attrs=combined_modules)

    def test_02_sibling_import_order_independence(self) -> None:
        spec = harness.canonical_specs()["hub"]
        baseline = harness.run_sandboxed({"spec": spec}, shuffle_seed=0)
        self.assertIn("html_app", baseline)
        for seed in (1, 2, 3, 4, 5):
            shuffled = harness.run_sandboxed({"spec": spec}, shuffle_seed=seed)
            self.assertEqual(baseline["html_app"], shuffled["html_app"])

    def test_03_calculator_allowlist_denylist_and_fuzz(self) -> None:
        # Exact Decimal arithmetic
        self.assertEqual(calc.eval_value("0.1 + 0.2"), 0.3)
        self.assertEqual(calc.eval_value("120 + 15"), 135)
        self.assertEqual(calc.eval_value("round(100 / 3, 2)"), 33.33)
        self.assertEqual(calc.eval_value("sum(10, 20, min(5, 8), max(1, 4), abs(-3))"), 42)
        self.assertEqual(calc.eval_value("50% * 200"), 100)
        self.assertEqual(calc.eval_value("2^5"), 32)
        self.assertEqual(calc.eval_value(42), 42)

        # Denylist -> E_CALC_DENIED
        for denied_expr in ("__import__('os')", "os.system('ls')", "2**8", ".5e", "[1,2]", "open('x')"):
            with self.assertRaises(calc.CalcError) as ctx:
                calc.eval_value(denied_expr)
            if denied_expr != ".5e":
                self.assertEqual(ctx.exception.code, "E_CALC_DENIED", f"Expected E_CALC_DENIED for {denied_expr}")

        # Range -> E_CALC_RANGE
        for range_expr in ("1/0", "2^7", "0^-1", "1e16", "(((((((1)))))))", "1+" * 31 + "1"):
            with self.assertRaises(calc.CalcError) as ctx:
                calc.eval_value(range_expr)
            self.assertEqual(ctx.exception.code, "E_CALC_RANGE", f"Expected E_CALC_RANGE for {range_expr}")

        # Syntax -> E_CALC_SYNTAX
        for syn_expr in ("", "12 +", "(1 + 2", "round()", "12 34", "1.2.3"):
            with self.assertRaises(calc.CalcError) as ctx:
                calc.eval_value(syn_expr)
            self.assertEqual(ctx.exception.code, "E_CALC_SYNTAX", f"Expected E_CALC_SYNTAX for {syn_expr}")

        # 200-case deterministic fuzz test
        rng = random.Random(20261110)
        alphabet = "0123456789+-*/^%().,_abcdefghijklmnopqrstuvwxyz[]{}!@#$\\'\""
        t0 = time.perf_counter()
        for _ in range(200):
            ln = rng.randint(0, 75)
            sample = "".join(rng.choice(alphabet) for _ in range(ln))
            try:
                val = calc.eval_value(sample)
                self.assertIsInstance(val, (int, float))
            except calc.CalcError as cerr:
                self.assertIn(cerr.code, ("E_CALC_SYNTAX", "E_CALC_DENIED", "E_CALC_RANGE", "E_TYPE"))
        self.assertLess(time.perf_counter() - t0, 0.5, "200 fuzz expressions must finish in < 0.5s")

    def test_04_every_error_and_warning_code(self) -> None:
        # 1. Multi-error single-pass collection: E_UNKNOWN_KEY + E_TEXT_TOO_LONG + E_SOURCE_REQUIRED + E_UNKNOWN_ICON + E_CALC_DENIED
        bad_multi = {
            "template": "bar-chart",
            "title": "X" * 65,
            "bogus_root": 1,
            "data_kind": "sourced",
            "content": {
                "items": [
                    {"label": "A", "value": "__import__('os')"},
                    {"label": "B", "value": "1/0"},
                    {"label": "C", "value": "12+"},
                ]
            },
        }
        res_multi = harness.run_sandboxed({"spec": bad_multi})
        self.assertNotIn("html_app", res_multi)
        codes_multi = {e["code"] for e in res_multi["errors"]}
        self.assertIn("E_UNKNOWN_KEY", codes_multi)
        self.assertIn("E_TEXT_TOO_LONG", codes_multi)
        self.assertIn("E_SOURCE_REQUIRED", codes_multi)
        self.assertIn("E_CALC_DENIED", codes_multi)
        self.assertIn("E_CALC_RANGE", codes_multi)
        self.assertIn("E_CALC_SYNTAX", codes_multi)

        # 2. E_UNKNOWN_TEMPLATE
        res_tpl = harness.run_sandboxed({"spec": {"template": "radar-3d", "title": "Hi", "content": {}}})
        self.assertIn("E_UNKNOWN_TEMPLATE", {e["code"] for e in res_tpl["errors"]})

        # 3. E_MISSING + E_TYPE + E_LIMIT_ITEMS + E_UNKNOWN_ICON
        res_proc = harness.run_sandboxed({
            "spec": {
                "template": "process",
                "theme": 123,
                "content": {
                    "steps": [
                        {"title": "Only one", "icon": "unicorn"},
                    ]
                },
            }
        })
        codes_proc = {e["code"] for e in res_proc["errors"]}
        self.assertIn("E_MISSING", codes_proc)       # missing title
        self.assertIn("E_TYPE", codes_proc)          # theme=123
        self.assertIn("E_LIMIT_ITEMS", codes_proc)   # 1 step < 3
        self.assertIn("E_UNKNOWN_ICON", codes_proc)  # unicorn

        # 4. E_SIZE (> 20 KB)
        huge_spec = {
            "template": "title",
            "title": "Valid Title",
            "content": {"subtitle": "ok"},
            "pad": "A" * 21000,
        }
        res_size = harness.run_sandboxed({"spec": huge_spec})
        self.assertEqual(res_size["errors"][0]["code"], "E_SIZE")

        # 5. W_ILLUSTRATIVE_BADGE on numeric chart without source
        bar_illus = harness.canonical_specs()["bar-chart"]
        bar_illus["data_kind"] = "illustrative"
        bar_illus.pop("source", None)
        res_badge = harness.run_sandboxed({"spec": bar_illus})
        self.assertIn("html_app", res_badge)
        self.assertIn("W_ILLUSTRATIVE_BADGE", {w["code"] for w in res_badge["warnings"]})
        self.assertIn("ILLUSTRATIVE DATA", res_badge["html_app"])

        # 6. W_CONTRAST_FIXED via theme_overrides
        res_contrast = harness.run_sandboxed({
            "spec": harness.canonical_specs()["title"],
            "theme_overrides": {"ink": "#EBE8E0"},  # low contrast on #FAF7F2 paper bg
        })
        self.assertIn("html_app", res_contrast)
        self.assertIn("W_CONTRAST_FIXED", {w["code"] for w in res_contrast["warnings"]})

    def test_05_collision_detector_autofit_and_e_no_fit(self) -> None:
        # Unit test check_collisions: text-vs-text, text-vs-icon, text-vs-shape, out-of-frame, parent-child ok
        b1 = layout.make_box("t1", "text", 100, 100, 120, 30, "g1")
        b2 = layout.make_box("t2", "text", 150, 110, 120, 30, "g2")
        self.assertEqual(len(layout.check_collisions([b1, b2], 1280, 720)), 1)

        ic = layout.make_box("ic1", "icon", 110, 105, 24, 24, "g3")
        self.assertEqual(len(layout.check_collisions([b1, ic], 1280, 720)), 1)

        sh = layout.make_box("sh1", "shape", 90, 90, 200, 80, "g4")
        self.assertEqual(len(layout.check_collisions([b1, sh], 1280, 720)), 1)

        # Parent-child containment is NOT a collision
        child = layout.make_box("child", "text", 105, 105, 80, 20, "g_child", parent="sh1")
        self.assertEqual(len(layout.check_collisions([sh, child], 1280, 720)), 0)

        # Out of frame
        oob = layout.make_box("oob", "shape", 5, 100, 100, 50, "g_oob")
        self.assertEqual(layout.check_collisions([oob], 1280, 720)[0]["reason"], "out_of_frame")

        # Trigger W_AUTOFIT on dense wide uppercase strings
        dense_spec = {
            "template": "comparison",
            "eyebrow": "MAXIMUM DENSITY AUTOFIT CHECK",
            "title": "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
            "aspect": "square",
            "content": {
                "columns": [
                    {
                        "title": "WWWWWWWWWWWWWWWWWWWWWWWWWW",
                        "icon": "shield",
                        "points": [
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                        ],
                    },
                    {
                        "title": "MMMMMMMMMMMMMMMMMMMMMMMMMM",
                        "icon": "bolt",
                        "points": [
                            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
                            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
                            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
                            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
                            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
                        ],
                    },
                    {
                        "title": "WWWWWWWWWWWWWWWWWWWWWWWWWW",
                        "icon": "lock",
                        "points": [
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
                        ],
                    },
                ],
                "verdict": "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
            },
        }
        dense_res = harness.run_sandboxed({"spec": dense_spec})
        # Either autofit succeeds cleanly with W_AUTOFIT or cleanly refuses with E_NO_FIT (never overlaps!)
        if "html_app" in dense_res:
            self.assertIn("W_AUTOFIT", {w["code"] for w in dense_res["warnings"]})
        else:
            self.assertEqual(dense_res["errors"][0]["code"], "E_NO_FIT")

        # Guaranteed E_NO_FIT via solve_layout when builder never fits
        tk = themes.resolve_theme("paper", [])
        norm_title = {
            "template": "title",
            "title": "Test",
            "eyebrow": "",
            "footer": "",
            "theme": "paper",
            "aspect": "wide",
            "data_kind": "illustrative",
            "source": "",
            "content": {"subtitle": "", "icon": None},
        }
        no_fit = layout.solve_layout(
            norm_title,
            tk,
            text,
            lambda s, c, th, tx, p: {"fits": False, "overflow_path": "content.items[2]", "overflow_reason": "Card overflow"},
        )
        self.assertFalse(no_fit["ok"])
        self.assertEqual(no_fit["error"]["code"], "E_NO_FIT")
        self.assertEqual(no_fit["error"]["path"], "content.items[2]")

    def test_06_full_matrix_canonical_and_max_stress_and_unicode(self) -> None:
        canon = harness.canonical_specs()
        stress = max_stress_specs()

        # 10 templates x 2 aspects x 4 themes = 80 canonical runs (native speed check + full layout validation)
        for tpl_name, base_spec in canon.items():
            for aspect in ("wide", "square"):
                for theme_name in ("paper", "ink", "light", "dark"):
                    sp = json.loads(json.dumps(base_spec))
                    sp["aspect"] = aspect
                    sp["theme"] = theme_name
                    t0 = time.perf_counter()
                    res = harness.run_native({"spec": sp})
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    self.assertNotIn("errors", res, f"Canonical {tpl_name}/{aspect}/{theme_name} failed: {res.get('errors')}")
                    self.assertIn("html_app", res)
                    self.assertNotIn("svg", res, "Live result must omit duplicate 'svg' field unless include_svg=True")
                    self.assertLessEqual(res["meta"]["duration_s"], 8.0)
                    self.assertLess(elapsed_ms, 150.0, f"Native render took {elapsed_ms:.1f}ms (> 150ms)")

        # 10 templates x 2 aspects max-item stress runs inside real SkillScriptRunner sandbox
        for tpl_name, st_spec in stress.items():
            for aspect in ("wide", "square"):
                sp = json.loads(json.dumps(st_spec))
                sp["aspect"] = aspect
                sp["theme"] = "ink" if aspect == "square" else "paper"
                t0 = time.perf_counter()
                res = harness.run_sandboxed({"spec": sp})
                elapsed_s = time.perf_counter() - t0
                self.assertNotIn("errors", res, f"Max-stress {tpl_name}/{aspect} failed: {res.get('errors')}")
                self.assertIn("html_app", res)
                self.assertLess(elapsed_s, 1.5, f"Sandboxed render took {elapsed_s:.2f}s (> 1.5s)")

        # CJK & RTL Unicode rendering check
        unicode_spec = {
            "template": "hub",
            "eyebrow": "国際化対応 · تخطيط متعدد اللغات",
            "title": "日本語とالعربيةのレイアウト検証カード",
            "theme": "light",
            "aspect": "wide",
            "data_kind": "illustrative",
            "content": {
                "center": {"title": "コアエンジン", "detail": "文字幅クラスによる安全な折り返し計算"},
                "spokes": [
                    {"title": "日本語テキスト", "detail": "全角文字を1.0em幅で保守的に計測します", "icon": "globe"},
                    {"title": "تحليل البيانات", "detail": "دعم النصوص العربية بدون تداخل العناصر", "icon": "chart"},
                    {"title": "WCAG AA Contrast", "detail": "Automatic 4.5:1 luminance verification", "icon": "check"},
                ],
            },
        }
        uni_res = harness.run_sandboxed({"spec": unicode_spec})
        self.assertNotIn("errors", uni_res, f"Unicode spec failed: {uni_res.get('errors')}")
        self.assertIn("日本語とالعربيةのレイアウト検証カード", uni_res["html_app"])

    def test_07_determinism_security_lint_and_xss(self) -> None:
        xss_spec = {
            "template": "recap",
            "eyebrow": "<img src=x onerror=alert(1)>",
            "title": "<script>alert('xss')</script> & \"Quotes\"",
            "footer": "https://evil.example/leak?cookie=1",
            "theme": "dark",
            "aspect": "wide",
            "data_kind": "illustrative",
            "content": {
                "points": [
                    {"title": "<b>Bold Tag</b>", "detail": "Ensure </style><script>evil()</script> is escaped."},
                    {"title": "Normal Point", "detail": "Deterministic output byte-for-byte check."},
                ]
            },
        }
        r1 = harness.run_sandboxed({"spec": xss_spec})
        r2 = harness.run_sandboxed({"spec": xss_spec})
        self.assertIn("html_app", r1)
        self.assertEqual(r1["html_app"], r2["html_app"], "Identical specs must produce byte-identical HTML")

        html_doc = r1["html_app"]
        self.assertLess(len(html_doc.encode("utf-8")), 122880, "HTML output must stay < 120 KB")
        self.assertIn("default-src 'none'", html_doc)
        self.assertIn("html.static", html_doc)
        self.assertIn("svg#scene{display:block;width:100%;height:auto}", html_doc)

        # Exactly one <script> tag (the Replay handler), zero unescaped injected tags
        self.assertEqual(len(re.findall(r"<script\b", html_doc, flags=re.I)), 1)
        self.assertNotIn("<script>alert", html_doc)
        self.assertNotIn("<script>evil", html_doc)
        self.assertNotIn("<img src=x", html_doc)
        self.assertNotIn("</style><script>", html_doc)

        # Forbidden runtime JS / external network patterns (strip escaped text first to verify markup/JS)
        for forbidden in ("<script src", "eval(", "Function(", "import(", "fetch(", "XMLHttpRequest", "WebSocket"):
            self.assertNotIn(forbidden, html_doc)

        # Verify zero external URLs in raw canon HTML (only xmlns="http://www.w3.org/2000/svg" allowed)
        canon_html = harness.run_sandboxed({"spec": harness.canonical_specs()["line-chart"]})["html_app"]
        urls = re.findall(r"https?://[^\s\"'<>]+", canon_html)
        self.assertEqual(urls, ["http://www.w3.org/2000/svg"])

    def test_08_golden_svg_lock(self) -> None:
        self.assertTrue(harness.GOLDEN_DIR.is_dir(), "Golden SVG directory must exist")
        specs = harness.canonical_specs()
        checked = 0
        for tpl_name, base_spec in specs.items():
            for theme_name in ("paper", "ink"):
                golden_file = harness.GOLDEN_DIR / f"{tpl_name}__{theme_name}.svg"
                self.assertTrue(golden_file.is_file(), f"Missing golden file: {golden_file.name}")
                sp = json.loads(json.dumps(base_spec))
                sp["theme"] = theme_name
                sp["aspect"] = "wide"
                res = harness.run_sandboxed({"spec": sp, "include_svg": True})
                self.assertEqual(
                    res["svg"],
                    golden_file.read_text(encoding="utf-8"),
                    f"Golden SVG drift detected in {golden_file.name}",
                )
                checked = checked + 1
        self.assertEqual(checked, 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
