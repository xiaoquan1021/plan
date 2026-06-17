#!/usr/bin/env python3
"""Audit the public XQ plan snapshot.

This public version scopes itself to this repository. It does not read private
source workspaces, private agent session logs, raw record, or execution
records.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from lease_manager import LeaseManager
from ledger_models import LEDGER_DIR, ROOT, TASK_GRAPH_FILE, TREE_ROOT
from task_event_store import EventStore, event_type_counts, failure_count_by_type, status_counts
from task_selector import build_task_graph, dependency_violations


PLAN_ROOT = ROOT / "plans"
MAIN_PLAN = PLAN_ROOT / "2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md"
ENTRY_DOC = TREE_ROOT / "00-execution-entry.md"
README_DOC = TREE_ROOT / "README.md"
SESSION_ID = "public-snapshot"
SESSION_FILE = None
EXEC_DIR = LEDGER_DIR / "private-execution-records"
SESSION_OUT = EXEC_DIR / "sessions" / SESSION_ID
EVIDENCE_DIR = LEDGER_DIR / "private-evidence"
DEFERRED_ARCHIVE = LEDGER_DIR / "deferred-archive.jsonl"

ACTIVE_EXECUTION_RECORD_RE = re.compile(r"^## Execution Record\s*$")
ACTIVE_EXECUTION_POINTER_RE = re.compile(
    r"(Historical source-pass|Full archive:|Index: `ledger/private-execution-records|Historical verification claims archive)",
    re.IGNORECASE,
)
ACTIVE_DEFERRED_DETAIL_RE = re.compile(
    r"^(Deferred|Still deferred|Deferred source files|Deferred coverage|Deferred solver fidelity):\s*$",
    re.IGNORECASE,
)
ACTIVE_STATUS_LANGUAGE_RE = re.compile(
    r"\b(now supports|now decodes|currently|current implementation|first-pass supports|"
    r"initial implementation|tests passed|source pass)\b",
    re.IGNORECASE,
)
TEST_PLAN_EXPECTED_ZERO_MATCH_RE = re.compile(
    r"\b(no matches|no match|0 matches|zero matches|"
    r"no output|empty output|should be empty|"
    r"without matches|without a match)\b|"
    r"\b(state-source|status-source|matching|matched|match|matches|lines?)\b"
    r".{0,40}\b(remains?|stays?|is)\s+0\b",
    re.IGNORECASE,
)
RG_COMMAND_RE = re.compile(r"^\s*(?:bash\s+-lc\s+['\"]?!?\s*)?rg\b")
RG_NEGATION_WRAPPER_RE = re.compile(r"^\s*(?:bash\s+-lc\s+['\"]?!\s+rg\b|!\s+rg\b)")

REQUIRED_SECTIONS = [
    "Purpose",
    "Owns",
    "Rules",
    "Implementation Contract",
    "Step Plan",
    "Test Plan",
    "Acceptance",
    "Failure Repair",
]

STATE_PATTERNS = {
    "current_cursor": re.compile(r"\bCurrent cursor\b", re.IGNORECASE),
    "next_implementation": re.compile(r"\bNext implementation document\b", re.IGNORECASE),
    "next_hardening": re.compile(r"\bNext planning-hardening document\b", re.IGNORECASE),
    "completed_hardening_batch": re.compile(r"\bCompleted hardening batch\b", re.IGNORECASE),
    "completed_source_batch": re.compile(r"\bCompleted source batch\b", re.IGNORECASE),
    "implementation_status": re.compile(r"\bImplementation status\b", re.IGNORECASE),
}

TEST_CLAIM_RE = re.compile(
    r"(\b\d+\s*/\s*\d+\b|tests?\s+passed|full\s+suite\s+passed|"
    r"focused\s+[^:\n]*\s+passed|build\s+completed\s+successfully)",
    re.IGNORECASE,
)
COUNT_RE = re.compile(r"\b\d+\s*/\s*\d+\b")
DEFERRED_RE = re.compile(
    r"\b(Deferred|Still deferred|remain deferred|remains deferred|not complete|not yet complete)\b",
    re.IGNORECASE,
)
FLOW_RE = re.compile(
    r"\b(Current Source Pass|Verified command|Verified commands|Verified result|latest source pass|"
    r"latest hardening|Result after first source pass|Current behavior)\b",
    re.IGNORECASE,
)
COMPLETION_RE = re.compile(
    r"\b(completed|complete|source pass|first source pass|implemented|verified result)\b",
    re.IGNORECASE,
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(text: str) -> str:
    return sha256(text.encode("utf-8", errors="replace")).hexdigest()


def excerpt(text: str, limit: int = 240) -> str:
    one_line = re.sub(r"\s+", " ", text.strip())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 3] + "..."


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def state_source_classification(line: str) -> tuple[str, str]:
    stripped = line.strip()
    if stripped.startswith("rg ") or stripped.startswith("rg\t") or "rg -n" in stripped:
        return "diagnostic-command-reference", "ignore-as-status-source"
    return "status-source", "migrate-or-link-to-ledger"


def classify_claim_triage(line: str, kind: str) -> dict[str, Any]:
    stripped = line.strip()
    lower = stripped.lower()
    counts = COUNT_RE.findall(line)

    if stripped.startswith("##"):
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "execution-heading",
            "next_action": "migrate-to-execution-records-if-section-holds-session-details",
            "reason": "Section heading or source-pass label, not standalone record.",
        }
    if stripped.startswith("|") and (
        "deferred" in lower
        or "not implemented" in lower
        or "not complete" in lower
        or "remain deferred" in lower
        or "remains deferred" in lower
    ):
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "deferred-boundary-row",
            "next_action": "preserve-in-deferred-ledger",
            "reason": "Deferred boundary text should be tracked as scope, not treated as completion record.",
        }
    if (
        "does not mean" in lower
        or lower.startswith("`first-pass structure complete` means")
        or lower.startswith("`first source pass` means")
    ):
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "definition-text",
            "next_action": "keep-as-policy-text",
            "reason": "Definition text explains plan vocabulary and does not claim verified execution.",
        }
    if "not an record source" in lower or "future place" in lower:
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "source-boundary-policy",
            "next_action": "keep-as-policy-text",
            "reason": "Source-boundary policy constrains record sources and does not claim implementation completion.",
        }
    if "architecture first" in lower or "runtime later" in lower:
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "architecture-policy",
            "next_action": "keep-as-policy-text",
            "reason": "Architecture policy describes allowed incomplete states and does not claim verified execution.",
        }
    if "this file tracks where the plan currently stands" in lower:
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "entry-document-purpose",
            "next_action": "keep-as-purpose-text-or-reword-away-from-status-mirroring",
            "reason": "Entry-document purpose text describes navigation and does not prove implementation completion.",
        }
    if kind == "completion-or-source-pass-claim" and "source pass" in lower:
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "plan-contract-source-pass",
            "next_action": "rewrite-to-stable-contract-language-or-move-to-execution-records-if-historical",
            "reason": "Source-pass wording in plan text is contract or scope language, not fresh verification record.",
        }
    if (
        "not implemented" in lower
        or "not complete" in lower
        or "not yet complete" in lower
        or "remain deferred" in lower
        or "remains deferred" in lower
        or " are deferred" in lower
        or " is deferred" in lower
    ):
        return {
            "claim_status": "not-a-verification-claim",
            "triage_bucket": "deferred-boundary",
            "next_action": "preserve-in-deferred-ledger",
            "reason": "Deferred or incomplete scope boundary, not proof of completion.",
        }
    if kind == "test-or-build-claim" or counts:
        bucket = "test-count-claim" if counts else "build-claim"
        if "xqactorfactory tests passed 56/56" in lower or "actorfactory tests passed 56/56" in lower:
            bucket = "high-risk-mechanical-test-count"
        return {
            "claim_status": "needs-rerun",
            "triage_bucket": bucket,
            "next_action": "attach-fresh-command-evidence-or-mark-unsupported",
            "reason": "Historical test/build text is not record without a linked command output captured after ledger repair.",
        }
    if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
        return {
            "claim_status": "unsupported",
            "triage_bucket": "checked-plan-step",
            "next_action": "link-evidence-or-reset-plan-step-before-automation",
            "reason": "Checked Markdown task is not proof that the claimed work remains valid.",
        }
    if "current source pass" in lower or "first source pass" in lower or "source pass" in lower:
        return {
            "claim_status": "unsupported",
            "triage_bucket": "source-pass-claim",
            "next_action": "move-to-execution-records-and-link-evidence-or-mark-unsupported",
            "reason": "Source-pass narrative needs command/source record before it can drive task state.",
        }
    return {
        "claim_status": "unsupported",
        "triage_bucket": "completion-or-behavior-claim",
        "next_action": "link-evidence-or-mark-unsupported",
        "reason": "Completion or behavior claim without attached record.",
    }


def owner_hint_for(path: str, line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("|"):
        cells = [cell.strip(" `") for cell in stripped.strip("|").split("|")]
        if len(cells) >= 3 and cells[1] and cells[1].lower() not in {
            "area",
            "primary owning document",
        }:
            return cells[1]

    if path == rel(MAIN_PLAN):
        return "main-plan-index"
    if path == rel(ENTRY_DOC):
        return "execution-entry"
    if path == rel(README_DOC):
        return "readme-index"

    parts = Path(path).parts
    if "xq-integrated-rebuild" in parts:
        index = parts.index("xq-integrated-rebuild")
        if index + 1 < len(parts):
            folder = parts[index + 1]
            owner_map = {
                "00-governance": "governance",
                "01-foundation": "foundation",
                "02-core-data": "core data",
                "03-native-project-io": "native project IO",
                "04-medical-image-io": "medical image IO",
                "05-workbench-visualization": "workbench visualization",
                "06-workflow": "workflow",
                "07-domain-features": "domain features",
                "08-xq-zip-selection": "zip source selection",
                "09-acceptance-repair": "acceptance repair",
            }
            return owner_map.get(folder, folder)
    return "unknown"


def classify_deferred_item(path: str, line: str) -> dict[str, Any]:
    stripped = line.strip()
    lower = stripped.lower()

    if stripped == "Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.":
        return {
            "ledger_status": "not-a-deferred-boundary",
            "deferred_bucket": "ledger-pointer",
            "next_action": "keep-as-ledger-pointer",
            "reason": "Standard pointer to the deferred ledger, not an implementation boundary.",
        }
    if stripped.startswith("rg ") or stripped.startswith("rg\t") or "rg -n" in stripped:
        return {
            "ledger_status": "not-a-deferred-boundary",
            "deferred_bucket": "diagnostic-command-reference",
            "next_action": "ignore-for-deferred-ledger",
            "reason": "Diagnostic command text contains deferred keywords but is not a scope item.",
        }
    if "authoritative task state" in lower and "deferred boundaries live in" in lower:
        return {
            "ledger_status": "not-a-deferred-boundary",
            "deferred_bucket": "ledger-pointer",
            "next_action": "keep-as-ledger-pointer",
            "reason": "Pointer to ledger location, not an implementation boundary.",
        }
    if "policy notes" in lower and "deferred issue register" in lower:
        return {
            "ledger_status": "not-a-deferred-boundary",
            "deferred_bucket": "ledger-pointer",
            "next_action": "keep-as-ledger-pointer",
            "reason": "README navigation text, not an implementation boundary.",
        }
    if TEST_CLAIM_RE.search(line):
        return {
            "ledger_status": "not-a-deferred-boundary",
            "deferred_bucket": "test-claim-with-deferred-word",
            "next_action": "track-through-claims-triage",
            "reason": "Historical test text contains deferred wording; claim handling belongs to claims triage.",
        }
    if stripped.startswith("- [") and "deferred" in lower:
        return {
            "ledger_status": "not-a-deferred-boundary",
            "deferred_bucket": "checked-routing-or-plan-step",
            "next_action": "track-through-claims-triage-if-it-claims-completion",
            "reason": "Checked Markdown task is not itself a deferred implementation boundary.",
        }
    if stripped.startswith("|") and (
        "deferred issue | primary owning document" in lower
        or "deferred issue" in lower and "primary owning" in lower
    ):
        return {
            "ledger_status": "section-marker",
            "deferred_bucket": "deferred-route-table-header",
            "next_action": "keep-as-routing-structure",
            "reason": "Routing table header, not a deferred item.",
        }
    if re.match(r"^#+\s+.*deferred", stripped, re.IGNORECASE):
        return {
            "ledger_status": "section-marker",
            "deferred_bucket": "deferred-section-heading",
            "next_action": "keep-only-if-section-remains-useful",
            "reason": "Section heading for deferred content, not a standalone boundary.",
        }
    if re.match(
        r"^(deferred|still deferred|deferred coverage|deferred source files|deferred solver fidelity|deferred domain-specific commands):\s*$",
        stripped,
        re.IGNORECASE,
    ):
        return {
            "ledger_status": "section-marker",
            "deferred_bucket": "deferred-section-label",
            "next_action": "keep-only-if-following-items-remain-in-plan-kernel",
            "reason": "Section label needs surrounding bullets for meaning.",
        }
    if (
        "deferred issue register" in lower
        or "post-acceptance deferred issue routing" in lower
        or "route the current known deferred work" in lower
        or "post-acceptance deferred issue route table" in lower
        or "remaining deferred fidelity work" in lower
        or "post-acceptance deferred work ownership" in lower
        or "deferred fidelity work has a primary owner" in lower
        or "current deferred fidelity work has a primary owner" in lower
    ):
        return {
            "ledger_status": "routing-policy",
            "deferred_bucket": "deferred-routing-policy",
            "next_action": "keep-as-routing-policy-or-link-to-deferred-register",
            "reason": "Policy/routing text about deferred handling, not the deferred work itself.",
        }
    if stripped.startswith("|") and (
        "deferred" in lower
        or "not implemented" in lower
        or "not complete" in lower
        or "remain deferred" in lower
        or "remains deferred" in lower
    ):
        return {
            "ledger_status": "registered-boundary",
            "deferred_bucket": "deferred-register-row",
            "next_action": "preserve-boundary-and-link-owner",
            "reason": "Table row describes deferred or incomplete implementation scope.",
        }
    if (
        "not implemented" in lower
        or "not complete" in lower
        or "not yet complete" in lower
        or "remain deferred" in lower
        or "remains deferred" in lower
        or " is deferred" in lower
        or " are deferred" in lower
        or "deferred until" in lower
        or "deferred to " in lower
    ):
        return {
            "ledger_status": "registered-boundary",
            "deferred_bucket": "deferred-scope-boundary",
            "next_action": "preserve-boundary-and-confirm-smallest-owner",
            "reason": "Line states implementation scope that remains outside the current source pass.",
        }
    if lower.startswith("expanded ") and " beyond " in lower:
        return {
            "ledger_status": "registered-boundary",
            "deferred_bucket": "deferred-expanded-scope-boundary",
            "next_action": "preserve-boundary-and-confirm-smallest-owner",
            "reason": "Line describes expanded scope beyond the current contract, so it is a deferred implementation boundary.",
        }

    return {
        "ledger_status": "needs-owner-confirmation",
        "deferred_bucket": "ambiguous-deferred-reference",
        "next_action": "inspect-nearby-section-before-cleanup",
        "reason": "Deferred keyword is present, but scanner cannot determine whether this is scope or policy.",
    }


def classify_execution_flow_item(line: str) -> dict[str, Any]:
    stripped = line.strip()
    lower = stripped.lower()

    if stripped.startswith("##"):
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "execution-section-heading",
            "next_action": "archive-section-then-replace-with-ledger-link",
            "reason": "Heading introduces historical execution status rather than plan kernel content.",
        }
    if lower.startswith("verified commands"):
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "verified-command-block",
            "next_action": "move-command-list-to-execution-records-and-evidence",
            "reason": "Historical command list belongs in execution records, not an executable plan document.",
        }
    if lower.startswith("verified result"):
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "verified-result-block",
            "next_action": "move-result-text-to-execution-records-and-downgrade-claims-until-evidenced",
            "reason": "Historical result text is a claim stream, not fresh verification record.",
        }
    if lower.startswith("current behavior"):
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "current-behavior-block",
            "next_action": "move-current-behavior-narrative-to-execution-records",
            "reason": "Current-behavior narrative is execution status and may become stale.",
        }
    if lower.startswith("result after first source pass"):
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "first-source-pass-result-block",
            "next_action": "move-first-pass-result-to-execution-records",
            "reason": "First-pass result text is historical execution narrative.",
        }
    if lower.startswith("current source pass owns") or lower.startswith("current source pass covers") or lower.startswith("current source pass:"):
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "current-source-pass-scope-label",
            "next_action": "rewrite-as-plan-contract-or-move-to-execution-records",
            "reason": "Current-source-pass labels blur plan contract with completed execution status.",
        }
    if "latest source pass" in lower or "latest hardening" in lower:
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "latest-pass-narrative",
            "next_action": "move-latest-pass-narrative-to-execution-records",
            "reason": "Latest-pass text is chronological session narrative.",
        }
    if "current source pass" in lower or "first source pass" in lower:
        return {
            "flow_status": "archive-before-markdown-cleanup",
            "flow_bucket": "source-pass-narrative",
            "next_action": "rewrite-as-plan-contract-or-move-to-execution-records",
            "reason": "Source-pass text can mislead future automated execution if left as plan state.",
        }
    return {
        "flow_status": "archive-before-markdown-cleanup",
        "flow_bucket": "execution-flow-reference",
        "next_action": "archive-before-cleanup",
        "reason": "Line matches execution-flow scanner.",
    }


def plan_files() -> list[Path]:
    files = [MAIN_PLAN]
    for path in sorted(TREE_ROOT.rglob("*.md")):
        if any(part.startswith("_") for part in path.relative_to(TREE_ROOT).parts):
            continue
        files.append(path)
    return files


def active_plan_kernel_violations(path: Path, lines: list[str]) -> list[dict[str, Any]]:
    violations = []
    path_rel = rel(path)
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if ACTIVE_EXECUTION_RECORD_RE.match(stripped):
            kind = "active_execution_record_section"
        elif ACTIVE_EXECUTION_POINTER_RE.search(line):
            kind = "active_execution_record_pointer"
        elif ACTIVE_DEFERRED_DETAIL_RE.match(stripped):
            kind = "active_deferred_detail_block"
        elif ACTIVE_STATUS_LANGUAGE_RE.search(line):
            kind = "active_status_language_line"
        else:
            continue
        violations.append(
            {
                "kind": kind,
                "path": path_rel,
                "line": lineno,
                "excerpt": excerpt(line),
                "sha256": digest(line),
            }
        )
    return violations


def _test_plan_command_blocks(lines: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current_block: dict[str, Any] | None = None
    in_test_plan = False
    in_fence = False
    section_level = 0
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if in_test_plan and level <= section_level:
                in_test_plan = False
                in_fence = False
            if title == "Test Plan":
                in_test_plan = True
                in_fence = False
                current_block = None
                section_level = level
            continue
        if not in_test_plan:
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not in_fence:
                current_block = {"commands": [], "prose": []}
                blocks.append(current_block)
                in_fence = True
            else:
                in_fence = False
            continue
        if not in_fence:
            if stripped and current_block is not None:
                current_block["prose"].append(stripped)
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if current_block is not None:
            current_block["commands"].append((lineno, stripped))
    return blocks


def test_plan_exit_semantics_violations(path: str | Path, lines: list[str]) -> list[dict[str, Any]]:
    path_rel = rel(Path(path))
    violations: list[dict[str, Any]] = []
    for block in _test_plan_command_blocks(lines):
        prose = "\n".join(block["prose"])
        if not TEST_PLAN_EXPECTED_ZERO_MATCH_RE.search(prose):
            continue
        for lineno, line in block["commands"]:
            if not RG_COMMAND_RE.match(line):
                continue
            if RG_NEGATION_WRAPPER_RE.match(line):
                continue
            violations.append(
                {
                    "kind": "test_plan_negative_rg_without_exit_zero_wrapper",
                    "path": path_rel,
                    "line": lineno,
                    "excerpt": excerpt(line),
                    "repair": "wrap the command as `bash -lc '! rg ...'` or an equivalent exit-0 negation wrapper",
                }
            )
    return violations


def archived_deferred_items(start_id: int) -> list[dict[str, Any]]:
    if not DEFERRED_ARCHIVE.exists():
        return []
    items = []
    for line in DEFERRED_ARCHIVE.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = str(row.get("text_excerpt", "")).strip()
        if not text:
            continue
        archive_path = str(row.get("archive_source", "ledger/deferred-archive.jsonl"))
        source_path = str(row.get("source_path", "unknown"))
        archive_line = int(row.get("item_index", 0) or 0)
        triage = classify_deferred_item(source_path, text)
        if triage.get("ledger_status") == "needs-owner-confirmation":
            triage = {
                "ledger_status": "registered-boundary",
                "deferred_bucket": "archived-deferred-boundary",
                "next_action": "preserve-boundary-and-link-owner",
                "reason": "Archived deferred scope moved out of active plan Markdown.",
            }
        items.append(
            {
                "deferred_id": f"deferred-{start_id + len(items):05d}",
                "archive_id": row.get("archive_id"),
                "path": source_path,
                "archive_source": archive_path,
                "line": archive_line,
                "text_excerpt": excerpt(text),
                "text_sha256": row.get("text_sha256", digest(text)),
                "owner_hint": owner_hint_for(source_path, text),
                "source": "deferred-archive",
                **triage,
            }
        )
    return items


def classify_doc(path: Path) -> str:
    if path == MAIN_PLAN:
        return "main-plan"
    if path == ENTRY_DOC:
        return "execution-entry"
    if path == README_DOC:
        return "readme-mirror"
    parts = path.relative_to(TREE_ROOT).parts
    if parts and parts[0] == "00-governance":
        return "governance"
    if parts and parts[0] in {"08-xq-zip-selection", "09-acceptance-repair"}:
        return "supporting-plan"
    return "child-plan"


def sections_for(lines: list[str]) -> set[str]:
    sections: set[str] = set()
    for line in lines:
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            sections.add(match.group(1).strip())
    return sections


def has_required_section(required: str, sections: set[str]) -> bool:
    if required == "Owns":
        return any(s in sections for s in ["Owns", "Code Ownership"])
    if required == "Test Plan":
        return "Test Plan" in sections
    return required in sections


def scan_plans() -> dict[str, Any]:
    docs = []
    state_sources = []
    claims = []
    deferred_items = []
    flow_items = []
    plan_kernel_violations = []
    tasks = []
    claim_id = 1
    deferred_id = 1
    flow_id = 1

    for path in plan_files():
        lines = read_lines(path)
        plan_kernel_violations.extend(active_plan_kernel_violations(path, lines))
        plan_kernel_violations.extend(test_plan_exit_semantics_violations(path, lines))
        role = classify_doc(path)
        sections = sections_for(lines)
        missing = [
            required
            for required in REQUIRED_SECTIONS
            if not has_required_section(required, sections)
        ]
        execution_doc = role in {"child-plan", "supporting-plan", "governance"}
        execution_missing = missing if execution_doc else []
        unchecked = sum(1 for line in lines if re.search(r"^\s*-\s+\[\s\]", line))
        checked = sum(1 for line in lines if re.search(r"^\s*-\s+\[[xX]\]", line))
        has_verification_commands = "First-Pass Verification Commands" in sections

        docs.append(
            {
                "path": rel(path),
                "role": role,
                "line_count": len(lines),
                "sections": sorted(sections),
                "missing_required_sections": missing,
                "execution_required_section_gaps": execution_missing,
                "has_first_pass_verification_commands": has_verification_commands,
                "checked_steps": checked,
                "unchecked_steps": unchecked,
            }
        )

        task_status = "not-executable-index"
        if execution_doc:
            task_status = "needs-hardening" if execution_missing else "ready-for-ledger-review"
        tasks.append(
            {
                "id": task_id_for(path),
                "source_md": rel(path),
                "role": role,
                "status": task_status,
                "missing_required_sections": execution_missing,
                "unchecked_step_count": unchecked,
                "checked_step_count": checked,
                "verification_source": (
                    "Test Plan"
                    if "Test Plan" in sections
                    else "First-Pass Verification Commands"
                    if has_verification_commands
                    else None
                ),
                "evidence_status": "unverified",
            }
        )

        for lineno, line in enumerate(lines, start=1):
            for name, pattern in STATE_PATTERNS.items():
                if pattern.search(line):
                    classification, action = state_source_classification(line)
                    state_sources.append(
                        {
                            "kind": name,
                            "classification": classification,
                            "suggested_action": action,
                            "path": rel(path),
                            "line": lineno,
                            "excerpt": excerpt(line),
                            "sha256": digest(line),
                        }
                    )

            if TEST_CLAIM_RE.search(line):
                triage = classify_claim_triage(line, "test-or-build-claim")
                claims.append(
                    {
                        "claim_id": f"plan-claim-{claim_id:05d}",
                        "source": "plan",
                        "kind": "test-or-build-claim",
                        "path": rel(path),
                        "line": lineno,
                        "counts": COUNT_RE.findall(line),
                        "text_excerpt": excerpt(line),
                        "text_sha256": digest(line),
                        "evidence_status": "unverified",
                        **triage,
                        "notes": "Needs fresh command record or linked archived output before being treated as true.",
                    }
                )
                claim_id += 1

            if COMPLETION_RE.search(line) and not TEST_CLAIM_RE.search(line):
                if role in {"main-plan", "execution-entry", "readme-mirror"} or "source pass" in line.lower():
                    triage = classify_claim_triage(line, "completion-or-source-pass-claim")
                    claims.append(
                        {
                            "claim_id": f"plan-claim-{claim_id:05d}",
                            "source": "plan",
                            "kind": "completion-or-source-pass-claim",
                            "path": rel(path),
                            "line": lineno,
                            "counts": COUNT_RE.findall(line),
                            "text_excerpt": excerpt(line),
                            "text_sha256": digest(line),
                            "evidence_status": "unverified",
                            **triage,
                            "notes": "Completion claims require source/test record before ledger can mark done.",
                        }
                    )
                    claim_id += 1

            if DEFERRED_RE.search(line):
                deferred_triage = classify_deferred_item(rel(path), line)
                deferred_items.append(
                    {
                        "deferred_id": f"deferred-{deferred_id:05d}",
                        "path": rel(path),
                        "line": lineno,
                        "text_excerpt": excerpt(line),
                        "text_sha256": digest(line),
                        "owner_hint": owner_hint_for(rel(path), line),
                        **deferred_triage,
                    }
                )
                deferred_id += 1

            if FLOW_RE.search(line):
                flow_triage = classify_execution_flow_item(line)
                flow_items.append(
                    {
                        "flow_id": f"flow-{flow_id:05d}",
                        "path": rel(path),
                        "line": lineno,
                        "text_excerpt": excerpt(line),
                        "text_sha256": digest(line),
                        **flow_triage,
                        "suggested_action": "move-to-execution-records",
                    }
                )
                flow_id += 1

    deferred_items.extend(archived_deferred_items(deferred_id))

    add_intra_phase_task_dependencies(tasks)
    return {
        "docs": docs,
        "state_sources": state_sources,
        "claims": claims,
        "deferred_items": deferred_items,
        "flow_items": flow_items,
        "plan_kernel_violations": plan_kernel_violations,
        "tasks": tasks,
    }


def add_intra_phase_task_dependencies(tasks: list[dict[str, Any]]) -> None:
    """Add conservative task-level dependencies within each execution phase.

    The source documents already encode a stable numeric order in their file
    names. This chain is deliberately conservative: it prevents parallel
    execution within a phase until a more explicit DAG is authored.
    """

    previous_by_phase: dict[str, str] = {}
    for task in tasks:
        if task.get("status") == "not-executable-index":
            continue
        source_md = str(task.get("source_md", ""))
        phase = source_md.split("/")[2] if source_md.startswith("plans/xq-integrated-rebuild/") and len(source_md.split("/")) > 2 else ""
        if not phase:
            continue
        previous = previous_by_phase.get(phase)
        if previous:
            task["task_dependencies"] = [previous]
        else:
            task["task_dependencies"] = []
        previous_by_phase[phase] = str(task.get("id"))


def scope_violations_for_docs(docs: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return scanned documents that fall outside the active audit boundary."""
    allowed_main = rel(MAIN_PLAN)
    violations = []
    for doc in docs:
        path = doc["path"]
        reason = None
        if path.startswith("<xq-implementation-workspace>/"):
            reason = "excluded-xq-source-tree"
        elif "<agent-plan-dir>" in path:
            reason = "excluded-agent-xq-plan"
        elif "<agent-session-state>" in path:
            reason = "excluded-agent-session-state"
        elif path.startswith("plans/xq-integrated-rebuild/_"):
            reason = "generated-ledger-or-execution-record"
        elif not (
            path == allowed_main
            or path.startswith("plans/xq-integrated-rebuild/")
        ):
            reason = "outside-xq-zip-analysis-active-plan-scope"
        if reason:
            violations.append({"path": path, "reason": reason})
    return violations


def task_id_for(path: Path) -> str:
    if path == MAIN_PLAN:
        return "main-plan"
    if path == ENTRY_DOC:
        return "execution-entry"
    if path == README_DOC:
        return "readme"
    base = path.relative_to(TREE_ROOT).with_suffix("")
    return re.sub(r"[^A-Za-z0-9]+", "-", str(base)).strip("-").lower()


def parse_json_line(line: str) -> dict[str, Any] | None:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def payload_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        if payload.get("type") == "message":
            pieces = []
            for item in payload.get("content", []) or []:
                if isinstance(item, dict):
                    pieces.append(str(item.get("text") or item.get("input_text") or item.get("output_text") or ""))
            return "\n".join(pieces)
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def scan_session() -> dict[str, Any]:
    return {
        "session_id": SESSION_ID,
        "session_file": None,
        "exists": False,
        "line_count": 0,
        "event_counts": {},
        "function_call_counts": {},
        "test_commands": [],
        "goal_updates": [],
        "red_flags": [],
        "session_usage_max_total": None,
        "compaction_markers": 0,
        "public_snapshot_note": "Private agent session logs are intentionally not included.",
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_by_document_index(plan: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    docs_by_path = {doc["path"]: dict(doc) for doc in plan["docs"]}
    counters: dict[str, Counter[str]] = defaultdict(Counter)

    for item in plan["state_sources"]:
        counters[item["path"]]["state_sources"] += 1
        counters[item["path"]][f"state_{item.get('classification', 'unknown')}"] += 1
    for item in plan["claims"]:
        counters[item["path"]]["claims"] += 1
    for item in plan["deferred_items"]:
        counters[item["path"]]["deferred_items"] += 1
    for item in plan["flow_items"]:
        counters[item["path"]]["execution_flow_items"] += 1

    documents = []
    for doc in plan["docs"]:
        path = doc["path"]
        counts = counters[path]
        blocked_reasons = []
        execution_gaps = doc.get("execution_required_section_gaps", doc["missing_required_sections"])
        if execution_gaps:
            blocked_reasons.append("missing-required-sections")
        if counts["claims"]:
            blocked_reasons.append("unverified-claims")
        if counts["deferred_items"]:
            blocked_reasons.append("deferred-scope-needs-owner-confirmation")
        if counts["execution_flow_items"]:
            blocked_reasons.append("execution-flow-content-still-in-plan")
        if counts["state_status-source"]:
            blocked_reasons.append("markdown-status-mirror")

        documents.append(
            {
                "path": path,
                "role": doc["role"],
                "line_count": doc["line_count"],
                "missing_required_sections": execution_gaps,
                "unchecked_step_count": doc["unchecked_steps"],
                "checked_step_count": doc["checked_steps"],
                "state_source_count": counts["state_sources"],
                "status_source_count": counts["state_status-source"],
                "diagnostic_reference_count": counts["state_diagnostic-command-reference"],
                "claim_count": counts["claims"],
                "deferred_count": counts["deferred_items"],
                "execution_flow_count": counts["execution_flow_items"],
                "flow_command_block_count": sum(
                    1
                    for item in plan["flow_items"]
                    if item["path"] == path and item.get("flow_bucket") == "verified-command-block"
                ),
                "flow_result_block_count": sum(
                    1
                    for item in plan["flow_items"]
                    if item["path"] == path and item.get("flow_bucket") == "verified-result-block"
                ),
                "flow_behavior_block_count": sum(
                    1
                    for item in plan["flow_items"]
                    if item["path"] == path and item.get("flow_bucket") == "current-behavior-block"
                ),
                "flow_source_pass_narrative_count": sum(
                    1
                    for item in plan["flow_items"]
                    if item["path"] == path
                    and item.get("flow_bucket") in {"source-pass-narrative", "latest-pass-narrative"}
                ),
                "execution_ready": not blocked_reasons,
                "blocked_reasons": blocked_reasons,
            }
        )

    documents.sort(
        key=lambda row: (
            row["execution_ready"],
            -row["claim_count"],
            -row["execution_flow_count"],
            -row["deferred_count"],
            row["path"],
        )
    )
    return {"metadata": metadata, "documents": documents}


def build_claim_triage(plan: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    claims = plan["claims"]
    by_status: Counter[str] = Counter()
    by_bucket: Counter[str] = Counter()
    by_path: dict[str, Counter[str]] = defaultdict(Counter)

    for claim in claims:
        status = claim.get("claim_status", "unknown")
        bucket = claim.get("triage_bucket", "unknown")
        by_status[status] += 1
        by_bucket[bucket] += 1
        by_path[claim["path"]][status] += 1
        by_path[claim["path"]][f"bucket:{bucket}"] += 1
        by_path[claim["path"]]["total"] += 1

    documents = []
    for path, counts in by_path.items():
        actionable = counts["needs-rerun"] + counts["unsupported"]
        documents.append(
            {
                "path": path,
                "total_claims": counts["total"],
                "needs_rerun": counts["needs-rerun"],
                "unsupported": counts["unsupported"],
                "not_a_verification_claim": counts["not-a-verification-claim"],
                "actionable_claims": actionable,
            }
        )
    documents.sort(key=lambda row: (-row["actionable_claims"], -row["total_claims"], row["path"]))

    return {
        "metadata": metadata,
        "summary": {
            "total_claims": len(claims),
            "by_status": dict(sorted(by_status.items())),
            "by_bucket": dict(sorted(by_bucket.items())),
            "actionable_claims": by_status["needs-rerun"] + by_status["unsupported"],
            "needs_rerun": by_status["needs-rerun"],
            "unsupported": by_status["unsupported"],
            "not_a_verification_claim": by_status["not-a-verification-claim"],
        },
        "documents": documents,
    }


def build_deferred_register(plan: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    deferred_items = plan["deferred_items"]
    by_status: Counter[str] = Counter()
    by_bucket: Counter[str] = Counter()
    by_owner: Counter[str] = Counter()
    by_path: dict[str, Counter[str]] = defaultdict(Counter)

    for item in deferred_items:
        status = item.get("ledger_status", "unknown")
        bucket = item.get("deferred_bucket", "unknown")
        owner = item.get("owner_hint", "unknown")
        by_status[status] += 1
        by_bucket[bucket] += 1
        by_owner[owner] += 1
        by_path[item["path"]][status] += 1
        by_path[item["path"]][f"bucket:{bucket}"] += 1
        by_path[item["path"]]["total"] += 1

    documents = []
    for path, counts in by_path.items():
        documents.append(
            {
                "path": path,
                "total_deferred": counts["total"],
                "registered_boundaries": counts["registered-boundary"],
                "section_markers": counts["section-marker"],
                "routing_policy": counts["routing-policy"],
                "not_a_deferred_boundary": counts["not-a-deferred-boundary"],
                "needs_owner_confirmation": counts["needs-owner-confirmation"],
            }
        )
    documents.sort(key=lambda row: (-row["registered_boundaries"], -row["total_deferred"], row["path"]))

    return {
        "metadata": metadata,
        "summary": {
            "total_deferred": len(deferred_items),
            "by_status": dict(sorted(by_status.items())),
            "by_bucket": dict(sorted(by_bucket.items())),
            "by_owner": dict(sorted(by_owner.items())),
            "registered_boundaries": by_status["registered-boundary"],
            "section_markers": by_status["section-marker"],
            "routing_policy": by_status["routing-policy"],
            "not_a_deferred_boundary": by_status["not-a-deferred-boundary"],
            "needs_owner_confirmation": by_status["needs-owner-confirmation"],
        },
        "documents": documents,
    }


def build_execution_flow_register(plan: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    flow_items = plan["flow_items"]
    by_status: Counter[str] = Counter()
    by_bucket: Counter[str] = Counter()
    by_path: dict[str, Counter[str]] = defaultdict(Counter)

    for item in flow_items:
        status = item.get("flow_status", "unknown")
        bucket = item.get("flow_bucket", "unknown")
        by_status[status] += 1
        by_bucket[bucket] += 1
        by_path[item["path"]][status] += 1
        by_path[item["path"]][f"bucket:{bucket}"] += 1
        by_path[item["path"]]["total"] += 1

    documents = []
    for path, counts in by_path.items():
        documents.append(
            {
                "path": path,
                "total_flow_items": counts["total"],
                "command_blocks": counts["bucket:verified-command-block"],
                "result_blocks": counts["bucket:verified-result-block"],
                "behavior_blocks": counts["bucket:current-behavior-block"],
                "section_headings": counts["bucket:execution-section-heading"],
                "source_pass_labels": counts["bucket:current-source-pass-scope-label"],
                "source_pass_narrative": counts["bucket:source-pass-narrative"]
                + counts["bucket:latest-pass-narrative"],
            }
        )
    documents.sort(key=lambda row: (-row["total_flow_items"], row["path"]))

    return {
        "metadata": metadata,
        "summary": {
            "total_flow_items": len(flow_items),
            "by_status": dict(sorted(by_status.items())),
            "by_bucket": dict(sorted(by_bucket.items())),
            "documents_with_flow": len(documents),
        },
        "documents": documents,
    }


def render_claims_triage(triage: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    summary = triage["summary"]
    by_bucket = summary["by_bucket"]
    by_status = summary["by_status"]
    docs = triage["documents"]

    lines = [
        "# Claims Triage",
        "",
        f"Generated: {triage['metadata']['generated_at']}",
        "",
        "This report classifies historical test/build/completion text. It does not upgrade any historical claim to verified record.",
        "",
        "## Summary",
        "",
        f"- Total detected claims: {summary['total_claims']}",
        f"- Needs rerun: {summary['needs_rerun']}",
        f"- Unsupported without linked record: {summary['unsupported']}",
        f"- Not verification claims: {summary['not_a_verification_claim']}",
        f"- Actionable claims: {summary['actionable_claims']}",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in by_status.items():
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## Bucket Counts",
            "",
            "| Bucket | Count |",
            "| --- | ---: |",
        ]
    )
    for bucket, count in by_bucket.items():
        lines.append(f"| {bucket} | {count} |")

    lines.extend(
        [
            "",
            "## Highest-Action Documents",
            "",
            "| File | Actionable | Needs rerun | Unsupported | Not verification | Total |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for doc in docs[:80]:
        lines.append(
            f"| `{doc['path']}` | {doc['actionable_claims']} | {doc['needs_rerun']} | {doc['unsupported']} | {doc['not_a_verification_claim']} | {doc['total_claims']} |"
        )
    if len(docs) > 80:
        lines.append(f"| ... | ... | ... | ... | ... | {len(docs) - 80} more omitted; see `claim-triage.json`. |")

    lines.extend(
        [
            "",
            "## High-Risk Test Count Claims",
            "",
            "| Claim | File | Line | Status | Excerpt |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    high_risk = [
        claim
        for claim in claims
        if claim.get("triage_bucket") == "high-risk-mechanical-test-count"
        or "xqactorfactory tests passed 56/56" in claim.get("text_excerpt", "").lower()
    ]
    for claim in high_risk[:80]:
        lines.append(
            f"| {claim['claim_id']} | `{claim['path']}` | {claim['line']} | {claim.get('claim_status')} | {claim['text_excerpt']} |"
        )
    if not high_risk:
        lines.append("| - | - | - | - | No high-risk mechanical test-count claim currently detected in plan files. |")

    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- `needs-rerun` means the historical test/build statement must receive fresh command record before it can affect task state.",
            "- `unsupported` means the claim should not drive automation until record is linked or the claim is explicitly downgraded.",
            "- `not-a-verification-claim` means the scanner preserved the line but it is policy, heading, or deferred-scope text rather than proof.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_deferred_register(register: dict[str, Any], deferred_items: list[dict[str, Any]]) -> str:
    summary = register["summary"]
    by_bucket = summary["by_bucket"]
    by_status = summary["by_status"]
    by_owner = summary["by_owner"]
    docs = register["documents"]

    lines = [
        "# Deferred Register",
        "",
        f"Generated: {register['metadata']['generated_at']}",
        "",
        "This register classifies lines that mention deferred scope so they cannot be lost inside completed-source summaries.",
        "",
        "## Summary",
        "",
        f"- Total deferred-related lines: {summary['total_deferred']}",
        f"- Registered boundaries: {summary['registered_boundaries']}",
        f"- Section markers: {summary['section_markers']}",
        f"- Routing policy text: {summary['routing_policy']}",
        f"- Not deferred boundaries: {summary['not_a_deferred_boundary']}",
        f"- Needs owner confirmation: {summary['needs_owner_confirmation']}",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in by_status.items():
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## Bucket Counts",
            "",
            "| Bucket | Count |",
            "| --- | ---: |",
        ]
    )
    for bucket, count in by_bucket.items():
        lines.append(f"| {bucket} | {count} |")

    lines.extend(
        [
            "",
            "## Owner Hints",
            "",
            "| Owner | Count |",
            "| --- | ---: |",
        ]
    )
    for owner, count in by_owner.items():
        lines.append(f"| {owner} | {count} |")

    lines.extend(
        [
            "",
            "## Highest-Action Documents",
            "",
            "| File | Deferred | Registered | Section markers | Routing policy | Not boundary | Needs owner |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for doc in docs[:80]:
        lines.append(
            f"| `{doc['path']}` | {doc['total_deferred']} | {doc['registered_boundaries']} | {doc['section_markers']} | {doc['routing_policy']} | {doc['not_a_deferred_boundary']} | {doc['needs_owner_confirmation']} |"
        )
    if len(docs) > 80:
        lines.append(f"| ... | ... | ... | ... | ... | ... | {len(docs) - 80} more omitted; see `deferred-register.json`. |")

    lines.extend(
        [
            "",
            "## Registered Boundaries",
            "",
            "| ID | Owner hint | File | Line | Bucket | Excerpt |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    registered = [
        item
        for item in deferred_items
        if item.get("ledger_status") == "registered-boundary"
    ]
    for item in registered[:120]:
        lines.append(
            f"| {item['deferred_id']} | {item.get('owner_hint', '-')} | `{item['path']}` | {item['line']} | {item.get('deferred_bucket', '-')} | {item['text_excerpt']} |"
        )
    if len(registered) > 120:
        lines.append(f"| ... | ... | ... | ... | ... | {len(registered) - 120} more omitted; see `deferred-items.jsonl`. |")

    lines.extend(
        [
            "",
            "## Non-Boundary Deferred Mentions",
            "",
            "| ID | Status | Bucket | File | Line | Excerpt |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    non_boundaries = [
        item
        for item in deferred_items
        if item.get("ledger_status") != "registered-boundary"
    ]
    for item in non_boundaries[:80]:
        lines.append(
            f"| {item['deferred_id']} | {item.get('ledger_status', '-')} | {item.get('deferred_bucket', '-')} | `{item['path']}` | {item['line']} | {item['text_excerpt']} |"
        )
    if len(non_boundaries) > 80:
        lines.append(f"| ... | ... | ... | ... | ... | {len(non_boundaries) - 80} more omitted; see `deferred-items.jsonl`. |")

    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- `registered-boundary` means the line describes scope that still must remain visible in the ledger.",
            "- `section-marker` means the line is structural text, not a standalone deferred work item.",
            "- `routing-policy` means the line describes how deferred work should be routed, not the deferred work itself.",
            "- `not-a-deferred-boundary` means the line mentions deferred wording but belongs with another ledger stream.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_execution_flow_register(register: dict[str, Any], flow_items: list[dict[str, Any]]) -> str:
    summary = register["summary"]
    by_bucket = summary["by_bucket"]
    by_status = summary["by_status"]
    docs = register["documents"]

    lines = [
        "# Execution-Flow Register",
        "",
        f"Generated: {register['metadata']['generated_at']}",
        "",
        "This register tracks historical execution narrative that still lives in plan documents. It is not fresh record and must not drive task state directly.",
        "",
        "## Summary",
        "",
        f"- Execution-flow lines: {summary['total_flow_items']}",
        f"- Documents with execution-flow lines: {summary['documents_with_flow']}",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in by_status.items():
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## Bucket Counts",
            "",
            "| Bucket | Count |",
            "| --- | ---: |",
        ]
    )
    for bucket, count in by_bucket.items():
        lines.append(f"| {bucket} | {count} |")

    lines.extend(
        [
            "",
            "## Highest-Flow Documents",
            "",
            "| File | Flow lines | Commands | Results | Behavior | Headings | Source-pass labels | Source-pass narrative |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for doc in docs[:80]:
        lines.append(
            f"| `{doc['path']}` | {doc['total_flow_items']} | {doc['command_blocks']} | {doc['result_blocks']} | {doc['behavior_blocks']} | {doc['section_headings']} | {doc['source_pass_labels']} | {doc['source_pass_narrative']} |"
        )
    if len(docs) > 80:
        lines.append(f"| ... | ... | ... | ... | ... | ... | ... | {len(docs) - 80} more omitted; see `execution-flow-register.json`. |")

    lines.extend(
        [
            "",
            "## Flow Items",
            "",
            "| ID | Bucket | File | Line | Excerpt |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for item in flow_items[:160]:
        lines.append(
            f"| {item['flow_id']} | {item.get('flow_bucket', '-')} | `{item['path']}` | {item['line']} | {item['text_excerpt']} |"
        )
    if len(flow_items) > 160:
        lines.append(f"| ... | ... | ... | ... | {len(flow_items) - 160} more omitted; see `execution-flow-items.jsonl`. |")

    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- `verified-command-block` and `verified-result-block` are historical records; claims inside them remain unverified until linked record exists.",
            "- `current-behavior-block` and source-pass narrative should be moved out of executable plan kernels or rewritten as future-facing contracts.",
            "- Source Markdown should eventually link to `<private-execution-records>/by-document/` instead of embedding long session history.",
        ]
    )
    return "\n".join(lines) + "\n"


def execution_record_slug(path: str) -> str:
    slug = Path(path).with_suffix("")
    return re.sub(r"[^A-Za-z0-9]+", "-", str(slug)).strip("-").lower()


def write_by_document_execution_records(
    by_document_dir: Path, plan: dict[str, Any], metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    for old_record in by_document_dir.glob("plans-*.md"):
        old_record.unlink()

    rows_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in plan["flow_items"]:
        rows_by_path[item["path"]].append(item)

    records = []
    for path, rows in sorted(rows_by_path.items()):
        slug = execution_record_slug(path)
        record_path = by_document_dir / f"{slug}.md"
        bucket_counts = Counter(row.get("flow_bucket", "unknown") for row in rows)
        lines = [
            f"# Execution Record: {path}",
            "",
            f"Generated: {metadata['generated_at']}",
            "",
            "This file archives execution-flow references detected in the source plan document. It does not prove that any command still passes.",
            "",
            "## Summary",
            "",
            f"- Source document: `{path}`",
            f"- Execution-flow lines archived: {len(rows)}",
            "",
            "## Bucket Counts",
            "",
            "| Bucket | Count |",
            "| --- | ---: |",
        ]
        for bucket, count in sorted(bucket_counts.items()):
            lines.append(f"| {bucket} | {count} |")
        lines.extend(
            [
                "",
                "## Archived Flow Items",
                "",
                "| ID | Line | Bucket | Action | Excerpt |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for row in rows:
            lines.append(
                f"| {row['flow_id']} | {row['line']} | {row.get('flow_bucket', '-')} | {row.get('next_action', row.get('suggested_action', '-'))} | {row['text_excerpt']} |"
            )
        lines.extend(
            [
                "",
                "## Use",
                "",
                "- Keep this file as the archive target before removing execution-flow narrative from the source Markdown.",
                "- Link fresh command record under `<private-evidence-dir>/` before using any historical result claim to update `tasks.json`.",
            ]
        )
        record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        records.append(
            {
                "path": path,
                "record": str(record_path.relative_to(TREE_ROOT)),
                "flow_count": len(rows),
                "bucket_counts": dict(sorted(bucket_counts.items())),
            }
        )
    return records


def authoritative_state(metadata: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    blocking_reasons = []
    if summary.get("status_source_lines", 0):
        blocking_reasons.append("markdown-status-mirrors")
    if summary.get("claim_actionable", 0):
        blocking_reasons.append("actionable-claims")
    if summary.get("execution_flow_items", 0):
        blocking_reasons.append("execution-flow-in-plan-docs")
    if summary.get("deferred_needs_owner_confirmation", 0):
        blocking_reasons.append("deferred-owner-confirmation")
    if summary.get("needs_hardening_documents", 0):
        blocking_reasons.append("needs-hardening-documents")
    if summary.get("scope_violations", 0):
        blocking_reasons.append("scope-violations")
    if summary.get("active_plan_kernel_violations", 0):
        blocking_reasons.append("active-plan-kernel-violations")
    if summary.get("task_event_errors", 0):
        blocking_reasons.append("task-event-errors")
    if summary.get("missing_private_evidence_links", 0):
        blocking_reasons.append("missing-evidence-links")
    if summary.get("invalid_private_evidence_files", 0):
        blocking_reasons.append("invalid-evidence-files")
    if summary.get("dependency_violations", 0):
        blocking_reasons.append("dependency-violations")
    task_blocking_reasons = []
    if summary.get("blocked_tasks", 0):
        task_blocking_reasons.append("blocked-tasks")
    if summary.get("lease_expired_tasks", 0) or summary.get("expired_task_leases", 0):
        task_blocking_reasons.append("lease-expired-tasks")
    if summary.get("stale_completion_tasks", 0) or summary.get("stale_completed_tasks", 0):
        task_blocking_reasons.append("stale-completion-tasks")
    implementation_resume_allowed = not blocking_reasons and not task_blocking_reasons
    claim_next_allowed = implementation_resume_allowed

    return {
        "state_schema": 1,
        "state_owner": {
            "history_truth_source": "ledger/task-events.jsonl",
            "task_selection_snapshot": "ledger/snapshots/tasks.json",
        },
        "generated_at": metadata["generated_at"],
        "plan_position": {
            "status": "ledger-reconciliation-in-progress",
            "current_cursor": None,
            "next_implementation_document": None,
            "next_planning_hardening_document": None,
            "cursor_source": "withheld-during-ledger-repair",
            "notes": [
                "Previous Markdown cursor/status mirrors were moved out of main-plan, README, and execution-entry.",
                "Claims and execution-flow narrative are reconciled in the ledger; do not resume implementation until remaining hardening and deferred-owner gates are cleared.",
            ],
        },
        "task_selection": {
            "allowed_source": "ledger/snapshots/tasks.json (derived task-selection snapshot)",
            "default_next_action": (
                "select-next-implementation-task-from-ledger"
                if claim_next_allowed
                else "harden-needs-hardening-documents-and-confirm-deferred-owners"
            ),
            "implementation_resume_allowed": implementation_resume_allowed,
            "claim_next_allowed": claim_next_allowed,
            "blocking_reasons": blocking_reasons,
            "task_blocking_reasons": task_blocking_reasons,
        },
        "migration": {
            "legacy_status_archive": "ledger/private-execution-records/by-document/legacy-status-mirrors.md",
            "status_mirror_policy": "Markdown entry documents may link to ledger state but must not duplicate cursor, completed batch, implementation status, or test-count claims.",
        },
        "audit_summary": summary,
    }


def gate_summary(summary: dict[str, Any]) -> dict[str, dict[str, int]]:
    hard_keys = [
        "scope_violations",
        "active_plan_kernel_violations",
        "claim_actionable",
        "deferred_needs_owner_confirmation",
        "execution_flow_items",
        "needs_hardening_documents",
        "task_event_errors",
        "missing_private_evidence_links",
        "invalid_private_evidence_files",
        "dependency_violations",
        "invalid_task_leases",
    ]
    task_blocking_keys = [
        "blocked_tasks",
        "lease_expired_tasks",
        "stale_completion_tasks",
        "expired_task_leases",
    ]
    informational_keys = [
        "ready_tasks",
        "failed_retry_ready_tasks",
        "not_executable_index_tasks",
        "completed_tasks",
        "claimed_tasks",
        "task_events",
        "active_task_leases",
        "override_events",
        "claims",
        "claim_not_verification",
        "deferred_items",
        "deferred_registered_boundaries",
        "deferred_section_markers",
        "deferred_routing_policy",
        "deferred_not_boundary",
    ]
    return {
        "hard_blocking_gates": {
            key: int(summary.get(key, 0))
            for key in hard_keys
        },
        "task_blocking_states": {
            key: int(summary.get(key, 0))
            for key in task_blocking_keys
        },
        "informational_counts": {
            key: int(summary.get(key, 0))
            for key in informational_keys
        },
    }


def render_by_document_readme(index: dict[str, Any]) -> str:
    docs = index["documents"]
    blocked = [doc for doc in docs if not doc["execution_ready"]]
    ready = [doc for doc in docs if doc["execution_ready"]]

    lines = [
        "# By-Document Execution Record Index",
        "",
        f"Generated: {index['metadata']['generated_at']}",
        "",
        "This index is derived from the current `XQ-zip-analysis` plan tree. It is a navigation aid for repair and audit work, not proof that any source task is complete.",
        "",
        "## Summary",
        "",
        f"- Documents indexed: {len(docs)}",
        f"- Blocked or needs repair before execution: {len(blocked)}",
        f"- Structurally clean according to this scanner: {len(ready)}",
        "",
        "## Highest-Risk Documents",
        "",
        "| File | Role | Claims | Deferred | Flow lines | Status mirrors | Missing sections | Blocked reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for doc in blocked[:80]:
        lines.append(
            "| `{path}` | {role} | {claims} | {deferred} | {flow} | {status} | {missing} | {reasons} |".format(
                path=doc["path"],
                role=doc["role"],
                claims=doc["claim_count"],
                deferred=doc["deferred_count"],
                flow=doc["execution_flow_count"],
                status=doc["status_source_count"],
                missing=", ".join(doc["missing_required_sections"]) or "-",
                reasons=", ".join(doc["blocked_reasons"]) or "-",
            )
        )
    if len(blocked) > 80:
        lines.append(f"| ... | ... | ... | ... | ... | ... | ... | {len(blocked) - 80} more omitted; see `index.json`. |")

    lines.extend(
        [
            "",
            "## Use",
            "",
            "1. Pick repair work from `ledger/snapshots/tasks.json`, not from long Markdown status blocks.",
            "2. Open `index.json` for the exact per-document counters.",
            "3. A document with claims or deferred lines should be reconciled before any implementation continues from it.",
            "4. Diagnostic command references are kept separate from true status mirrors so command examples do not become fake state sources.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_ledger_readme(plan: dict[str, Any], session: dict[str, Any], summary: dict[str, Any]) -> str:
    status_sources = sum(
        1
        for item in plan["state_sources"]
        if item.get("classification") == "status-source"
    )
    diagnostic_sources = sum(
        1
        for item in plan["state_sources"]
        if item.get("classification") == "diagnostic-command-reference"
    )
    missing_docs = [
        doc
        for doc in plan["docs"]
        if doc.get("execution_required_section_gaps", doc["missing_required_sections"])
    ]
    next_order = []
    if summary.get("status_source_lines", 0):
        next_order.append("Reconcile duplicated status mirrors in main plan, execution entry, and README against `ledger/snapshots/tasks.json`.")
    if summary.get("claim_actionable", 0):
        next_order.append("Work through `claims-triage.md`: attach record under `<private-evidence-dir>/`, rerun targeted commands, or keep unsupported.")
    if summary.get("deferred_needs_owner_confirmation", 0):
        next_order.append("Inspect deferred items marked `needs-owner-confirmation` and assign the smallest owning document.")
    if missing_docs:
        next_order.append("Harden documents listed as `needs-hardening` in `tasks.json` before any automated executor consumes them.")
    if summary.get("execution_flow_items", 0):
        next_order.append("Move execution-flow narrative into `<private-execution-records>/by-document/` before slimming source `.md` files.")
    if summary.get("task_event_errors", 0):
        next_order.append("Fix `ledger/private-task-events.jsonl` schema/hash-chain errors before claiming tasks.")
    if summary.get("missing_private_evidence_links", 0) or summary.get("invalid_private_evidence_files", 0):
        next_order.append("Repair completion record links before any completed state can be trusted.")
    if summary.get("expired_task_leases", 0):
        next_order.append("Resolve expired task leases with `ledger_task.py release-claim` or `record-block` before claiming more work.")
    if summary.get("blocked_tasks", 0) or summary.get("stale_completed_tasks", 0):
        next_order.append("Explain blocked or stale tasks before continuing automation.")
    next_order.append("Only after the gates above, select the next implementation task from the derived `tasks.json` snapshot.")

    lines = [
        "# XQ-zip-analysis Audit Ledger",
        "",
        f"Generated: {now_iso()}",
        "",
        "This directory is the current audit ledger for `XQ-zip-analysis`. It exists to stop future work from resuming directly out of long, mirrored Markdown status text.",
        "",
        "## Ground Rules",
        "",
        "- Scope is only `<public-or-private-plan-root>` plan state, plus the archived `<private-session-id>` session for forensic indexing.",
        "- Do not treat historical `tests passed`, `full suite passed`, or `x/y` text as true until a fresh record file is linked.",
        "- Do not continue implementation from old Markdown cursor text; choose work from the derived `ledger/snapshots/tasks.json` snapshot after reconciliation.",
        "- Do not edit source code as part of this audit pass.",
        "",
        "## Generated Files",
        "",
        "- `audit-summary.json`: compact machine summary.",
        "- `task-events.jsonl`: append-only historical truth source for task events.",
        "- `tasks.json`: derived task-selection snapshot and plan position during repair.",
        "- `claims.jsonl`: every detected test/build/completion claim with triage status.",
        "- `claim-triage.json` and `claims-triage.md`: grouped claim repair queues.",
        "- `deferred-items.jsonl`: deferred or not-complete boundaries with triage status.",
        "- `deferred-register.json` and `deferred-register.md`: grouped deferred repair queues and owner hints.",
        "- `execution-flow-items.jsonl`: plan lines that look like session流水账 and should move into execution records.",
        "- `execution-flow-register.json` and `execution-flow-register.md`: grouped execution-flow cleanup queues.",
        "- `plan-docs.json`: structural inventory of scanned plan documents.",
        "- `source-inventory.md`: human-readable source inventory and state mirror list.",
        "- `repair-backlog.md`: prioritized cleanup queue.",
        "- `../ledger/private-execution-records/by-document/index.json`: per-document counters for claims/deferred/flow/status risk.",
        "- `../ledger/private-execution-records/sessions/<private-session-id>/session-index.json`: structured session index.",
        "",
        "## Current Counts",
        "",
        f"- Plan documents scanned: {summary['plan_documents']}",
        f"- Scope violations: {summary.get('scope_violations', 0)}",
        f"- Active plan-kernel violations: {summary.get('active_plan_kernel_violations', 0)}",
        f"- Active execution-record sections: {summary.get('active_execution_record_sections', 0)}",
        f"- Active execution-record pointers: {summary.get('active_execution_record_pointers', 0)}",
        f"- Active deferred detail blocks: {summary.get('active_deferred_detail_blocks', 0)}",
        f"- Active status-language lines: {summary.get('active_status_language_lines', 0)}",
        f"- Active historical-record lines: {summary.get('active_historical_record_lines', 0)}",
        f"- True Markdown status-source lines: {status_sources}",
        f"- Diagnostic command references containing status keywords: {diagnostic_sources}",
        f"- Test/build/completion claims detected: {summary['claims']}",
        f"- Claim triage actionable items: {summary.get('claim_actionable', 0)}",
        f"- Claim triage needs rerun: {summary.get('claim_needs_rerun', 0)}",
        f"- Claim triage unsupported: {summary.get('claim_unsupported', 0)}",
        f"- Claim triage not verification text: {summary.get('claim_not_verification', 0)}",
        f"- Deferred/not-complete lines: {summary['deferred_items']}",
        f"- Deferred register registered boundaries: {summary.get('deferred_registered_boundaries', 0)}",
        f"- Deferred register needs owner confirmation: {summary.get('deferred_needs_owner_confirmation', 0)}",
        f"- Execution-flow lines to migrate: {summary['execution_flow_items']}",
        f"- Execution-flow documents with generated records: {summary.get('execution_flow_documents', 0)}",
        f"- Documents missing canonical sections: {len(missing_docs)}",
        f"- Task event errors: {summary.get('task_event_errors', 0)}",
        f"- Missing record links: {summary.get('missing_private_evidence_links', 0)}",
        f"- Invalid record files: {summary.get('invalid_private_evidence_files', 0)}",
        f"- Stale completed tasks: {summary.get('stale_completed_tasks', 0)}",
        f"- Active task leases: {summary.get('active_task_leases', 0)}",
        f"- Expired task leases: {summary.get('expired_task_leases', 0)}",
        f"- Blocked tasks: {summary.get('blocked_tasks', 0)}",
        f"- Dependency violations: {summary.get('dependency_violations', 0)}",
        f"- Override events: {summary.get('override_events', 0)}",
        f"- private session red flags: {summary['session_red_flags']}",
        f"- private session test/build commands captured: {summary['session_test_commands']}",
        "",
        "## Next Repair Order",
        "",
    ]
    for index, item in enumerate(next_order, start=1):
        lines.append(f"{index}. {item}")
    return "\n".join(lines) + "\n"


def render_source_inventory(plan: dict[str, Any], session: dict[str, Any]) -> str:
    docs = plan["docs"]
    state_sources = plan["state_sources"]
    missing_docs = [
        d
        for d in docs
        if d.get("execution_required_section_gaps", d["missing_required_sections"])
    ]
    flow_items = plan["flow_items"]
    deferred_items = plan["deferred_items"]
    claims = plan["claims"]

    lines = [
        "# XQ-zip-analysis Source Inventory",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Scope",
        "",
        "Included:",
        "",
        f"- `{rel(MAIN_PLAN)}`",
        f"- `{rel(ENTRY_DOC)}`",
        f"- `{rel(README_DOC)}`",
        "- `plans/xq-integrated-rebuild/**/*.md` excluding generated `ledger`, `ledger/private-execution-records`, and `<private-evidence-dir>` directories.",
        "",
        "Excluded:",
        "",
        "- `<xq-implementation-workspace>`",
        "- `<agent-session-log>`",
        "- `<agent-session-state>`",
        "- old Copilot, Codeium, Windsurf, and external dependency plan files.",
        "",
        "## Counts",
        "",
        f"- Plan documents scanned: {len(docs)}",
        f"- State-source lines: {len(state_sources)}",
        f"- Test/build/completion claims: {len(claims)}",
        f"- Deferred/not-complete lines: {len(deferred_items)}",
        f"- Execution-flow lines to migrate: {len(flow_items)}",
        f"- Session red flags: {len(session.get('red_flags', []))}",
        "",
        "## State Mirrors",
        "",
        "| Kind | Classification | Suggested action | File | Line | Excerpt |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for item in state_sources:
        lines.append(
            f"| {item['kind']} | {item.get('classification', 'unknown')} | {item.get('suggested_action', '-')} | `{item['path']}` | {item['line']} | {item['excerpt']} |"
        )

    lines.extend(
        [
            "",
            "## Required-Section Gaps",
            "",
            "| File | Role | Missing required sections | Unchecked steps | Notes |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for doc in missing_docs:
        note = ""
        gaps = doc.get("execution_required_section_gaps", doc["missing_required_sections"])
        if doc["has_first_pass_verification_commands"] and "Test Plan" in gaps:
            note = "Has `First-Pass Verification Commands`, but no canonical `Test Plan` heading."
        lines.append(
            f"| `{doc['path']}` | {doc['role']} | {', '.join(gaps)} | {doc['unchecked_steps']} | {note} |"
        )

    lines.extend(
        [
            "",
            "## Execution-Flow Content Still In Plan Docs",
            "",
            "| File | Line | Suggested action | Excerpt |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for item in flow_items[:120]:
        lines.append(
            f"| `{item['path']}` | {item['line']} | {item['suggested_action']} | {item['text_excerpt']} |"
        )
    if len(flow_items) > 120:
        lines.append(f"| ... | ... | ... | {len(flow_items) - 120} more entries omitted from markdown; see JSON/JSONL ledgers. |")

    lines.extend(
        [
            "",
            "## Deferred Lines",
            "",
            "Deferred items are preserved as scope boundaries and must not be swallowed by completed-source summaries.",
            "",
            "| File | Line | Status | Bucket | Owner hint | Excerpt |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in deferred_items[:160]:
        lines.append(
            f"| `{item['path']}` | {item['line']} | {item.get('ledger_status', '-')} | {item.get('deferred_bucket', '-')} | {item.get('owner_hint', '-')} | {item['text_excerpt']} |"
        )
    if len(deferred_items) > 160:
        lines.append(f"| ... | ... | ... | ... | ... | {len(deferred_items) - 160} more entries omitted from markdown; see ledger outputs. |")

    return "\n".join(lines) + "\n"


def render_red_flags(session: dict[str, Any]) -> str:
    lines = [
        f"# Session {SESSION_ID} Red Flags",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Summary",
        "",
        f"- Session file exists: {session.get('exists')}",
        f"- JSONL lines: {session.get('line_count')}",
        f"- Compaction markers: {session.get('compaction_markers')}",
        f"- Max observed total usage units: {session.get('session_usage_max_total')}",
        f"- Function calls: {session.get('function_call_counts')}",
        f"- Test/build commands captured: {len(session.get('test_commands', []))}",
        f"- Red flags captured: {len(session.get('red_flags', []))}",
        "",
        "## P0/P1 Flags",
        "",
        "| Severity | Kind | Line | Excerpt |",
        "| --- | --- | ---: | --- |",
    ]
    for flag in session.get("red_flags", []):
        if flag.get("severity") in {"P0", "P1"}:
            lines.append(
                f"| {flag.get('severity')} | {flag.get('kind')} | {flag.get('line')} | {flag.get('excerpt')} |"
            )

    lines.extend(
        [
            "",
            "## Captured Test/Build Commands",
            "",
            "| Line | Function | Command excerpt |",
            "| ---: | --- | --- |",
        ]
    )
    for cmd in session.get("test_commands", [])[:120]:
        lines.append(
            f"| {cmd.get('line')} | {cmd.get('function')} | {cmd.get('command_excerpt')} |"
        )
    if len(session.get("test_commands", [])) > 120:
        lines.append(
            f"| ... | ... | {len(session.get('test_commands', [])) - 120} more commands omitted from markdown; see `session-index.json`. |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- P0/P1 flags are evidence-routing markers, not automatic proof that code is wrong.",
            "- Claims found in this session must be reconciled against current plan files and fresh command record before being treated as true.",
            "- Mechanical count-replacement and very long compaction chains are process risks that should block direct continuation from long Markdown status text.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_repair_backlog(plan: dict[str, Any], session: dict[str, Any]) -> str:
    missing_docs = [
        d
        for d in plan["docs"]
        if d.get("execution_required_section_gaps", d["missing_required_sections"])
    ]
    state_sources = [
        item
        for item in plan["state_sources"]
        if item.get("classification") == "status-source"
    ]
    flow_items = plan["flow_items"]
    deferred_items = plan["deferred_items"]
    claims = plan["claims"]
    claim_status_counts = Counter(claim.get("claim_status", "unknown") for claim in claims)
    actionable_claims = claim_status_counts["needs-rerun"] + claim_status_counts["unsupported"]
    deferred_status_counts = Counter(item.get("ledger_status", "unknown") for item in deferred_items)
    red_flags = session.get("red_flags", [])
    code_risk_flags = [
        flag
        for flag in red_flags
        if flag.get("kind") in {"build-test-orchestration-risk", "mechanical-doc-or-count-risk"}
    ]

    p0 = []
    if any("56/56" in f.get("excerpt", "") or "误替换" in f.get("excerpt", "") for f in red_flags):
        p0.append("Verify and repair any `XQActorFactory tests passed 56/56` or similar mechanical test-count claims before continuing implementation.")
    if state_sources:
        p0.append("Replace multi-file Markdown status mirroring with `ledger/private-task-events.jsonl` history and derived `ledger/snapshots/tasks.json` selection snapshots.")
    if actionable_claims:
        p0.append("Work through `claims-triage.md`: rerun historical test/build claims or keep completion claims unsupported until record is linked.")

    p1 = []
    if missing_docs:
        p1.append(f"Normalize or harden {len(missing_docs)} documents with missing canonical sections before using them as executable tasks.")
    if flow_items:
        p1.append(f"Move {len(flow_items)} execution-flow lines out of plan docs into `ledger/private-execution-records`.")
    if deferred_status_counts["needs-owner-confirmation"]:
        p1.append(f"Confirm owner routing for {deferred_status_counts['needs-owner-confirmation']} ambiguous deferred reference.")
    if deferred_items:
        p1.append(f"Keep {len(deferred_items)} deferred/not-complete ledger entries visible so completed-source summaries cannot hide them.")
    p1.append("Do not resume from `Current cursor`; select work from the derived `ledger/snapshots/tasks.json` snapshot only.")

    lines = [
        "# XQ-zip-analysis Repair Backlog",
        "",
        f"Generated: {now_iso()}",
        "",
        "This backlog is scoped only to `<public-or-private-plan-root>` plan state and the `<private-session-id>` session audit.",
        "",
        "## P0: Blockers Before Continuing Implementation",
        "",
    ]
    for item in p0:
        lines.append(f"- [ ] {item}")
    if not p0:
        lines.append("- [ ] No P0 items were generated by the scanner; manually confirm before resuming implementation.")

    lines.extend(["", "## P1: Required Cleanup Before Long-Horizon Automation", ""])
    for item in p1:
        lines.append(f"- [ ] {item}")

    lines.extend(
        [
            "",
            "## P2: Follow-Up Hardening",
            "",
            "- [ ] Convert README and main-plan status sections into short summaries derived from ledger state.",
            "- [ ] Replace source `.md` execution-flow sections with links to generated per-document execution records.",
            "- [ ] Add a repeatable command that regenerates source inventory, claims, and repair backlog after each task.",
            "",
            "## Risk Categories",
            "",
            "| Category | Count | Meaning | First action |",
            "| --- | ---: | --- | --- |",
            f"| Document pollution | {len(state_sources) + len(flow_items)} | Markdown contains mirrored status or session流水账 that can mislead resume. | Move status into `ledger/snapshots/tasks.json` and execution text into `ledger/private-execution-records`. |",
            f"| Evidence missing | {actionable_claims} | Test/build/completion claims remain actionable after triage. | Attach record under `<private-evidence-dir>/`, rerun targeted commands, or keep unsupported in `claims.jsonl`. |",
            f"| Scanner non-claims | {claim_status_counts['not-a-verification-claim']} | Lines preserved by the scanner but classified as definitions, headings, or deferred boundaries rather than proof. | Do not use these lines to drive automation. |",
            f"| Deferred boundary risk | {len(deferred_items)} | Deferred/not-complete items can be hidden by completed-source summaries. | Preserve them in ledger before simplifying any `.md`. |",
            f"| Deferred registered boundaries | {deferred_status_counts['registered-boundary']} | Scope items that should remain visible in the ledger. | Keep them in `deferred-items.jsonl` and `deferred-register.json`. |",
            f"| Possible code/process risk | {len(code_risk_flags)} | Session contains build/test orchestration issues or mechanical count/doc replacement risks. | Re-run targeted verification only after ledger cleanup chooses a task. |",
            "",
            "## Top Missing-Section Documents",
            "",
            "| File | Missing |",
            "| --- | --- |",
        ]
    )
    for doc in missing_docs[:80]:
        gaps = doc.get("execution_required_section_gaps", doc["missing_required_sections"])
        lines.append(f"| `{doc['path']}` | {', '.join(gaps)} |")
    if len(missing_docs) > 80:
        lines.append(f"| ... | {len(missing_docs) - 80} more omitted; see `tasks.json`. |")
    return "\n".join(lines) + "\n"


def main() -> int:
    by_document_dir = EXEC_DIR / "by-document"
    for directory in [
        LEDGER_DIR,
        SESSION_OUT,
        by_document_dir,
        EVIDENCE_DIR / "test-runs",
        EVIDENCE_DIR / "command-summaries",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    plan = scan_plans()
    session = scan_session()
    event_store = EventStore()
    event_state = event_store.derive_tasks(plan["tasks"])
    lease_summary = LeaseManager().summarize()
    runtime_tasks = event_state["tasks"]
    for task in runtime_tasks:
        if task["id"] in lease_summary["expired_task_ids"] and task.get("status") in {"claimed", "in-progress"}:
            task["status"] = "lease-expired"
        if task["id"] in lease_summary["active_task_ids"] and task.get("status") == "ready-for-ledger-review":
            task["status"] = "claimed"
    deps = dependency_violations(runtime_tasks)

    metadata = {
        "generated_at": now_iso(),
        "scope_root": str(ROOT),
        "plan_root": str(PLAN_ROOT),
        "tree_root": str(TREE_ROOT),
        "excluded_roots": [
            "<xq-implementation-workspace>",
            "<agent-session-log>",
            "<agent-session-state>",
            "old Copilot/Codeium/Windsurf plans",
            "external dependency source trees",
        ],
    }

    status_source_count = sum(
        1
        for item in plan["state_sources"]
        if item.get("classification") == "status-source"
    )
    diagnostic_reference_count = sum(
        1
        for item in plan["state_sources"]
        if item.get("classification") == "diagnostic-command-reference"
    )
    claim_status_counts = Counter(claim.get("claim_status", "unknown") for claim in plan["claims"])
    deferred_status_counts = Counter(item.get("ledger_status", "unknown") for item in plan["deferred_items"])
    execution_flow_documents = len({item["path"] for item in plan["flow_items"]})
    needs_hardening_documents = sum(
        1 for task in runtime_tasks if task.get("status") == "needs-hardening"
    )
    task_status_counts = Counter(task.get("status", "unknown") for task in runtime_tasks)
    completion_standard_counts = Counter(
        task.get("completion_standard", "unverified")
        for task in runtime_tasks
        if task.get("status") == "completed"
    )
    scope_violations = scope_violations_for_docs(plan["docs"])
    kernel_violation_counts = Counter(
        item.get("kind", "unknown") for item in plan["plan_kernel_violations"]
    )
    active_execution_record_sections = kernel_violation_counts["active_execution_record_section"]
    active_execution_record_pointers = kernel_violation_counts["active_execution_record_pointer"]
    active_deferred_detail_blocks = kernel_violation_counts["active_deferred_detail_block"]
    active_status_language_lines = kernel_violation_counts["active_status_language_line"]
    active_historical_record_lines = active_execution_record_pointers

    summary = {
        "plan_documents": len(plan["docs"]),
        "scope_violations": len(scope_violations),
        "scope_violation_examples": scope_violations[:10],
        "active_plan_kernel_violations": len(plan["plan_kernel_violations"]),
        "active_execution_record_sections": active_execution_record_sections,
        "active_execution_record_pointers": active_execution_record_pointers,
        "active_deferred_detail_blocks": active_deferred_detail_blocks,
        "active_status_language_lines": active_status_language_lines,
        "active_historical_record_lines": active_historical_record_lines,
        "state_sources": len(plan["state_sources"]),
        "status_source_lines": status_source_count,
        "diagnostic_reference_lines": diagnostic_reference_count,
        "claims": len(plan["claims"]),
        "deferred_items": len(plan["deferred_items"]),
        "execution_flow_items": len(plan["flow_items"]),
        "session_red_flags": len(session.get("red_flags", [])),
        "session_test_commands": len(session.get("test_commands", [])),
        "claim_actionable": claim_status_counts["needs-rerun"] + claim_status_counts["unsupported"],
        "claim_needs_rerun": claim_status_counts["needs-rerun"],
        "claim_unsupported": claim_status_counts["unsupported"],
        "claim_not_verification": claim_status_counts["not-a-verification-claim"],
        "deferred_registered_boundaries": deferred_status_counts["registered-boundary"],
        "deferred_section_markers": deferred_status_counts["section-marker"],
        "deferred_routing_policy": deferred_status_counts["routing-policy"],
        "deferred_not_boundary": deferred_status_counts["not-a-deferred-boundary"],
        "deferred_needs_owner_confirmation": deferred_status_counts["needs-owner-confirmation"],
        "execution_flow_documents": execution_flow_documents,
        "needs_hardening_documents": needs_hardening_documents,
        "task_event_errors": len(event_state["event_errors"]),
        "task_events": len(event_state["events"]),
        "task_event_type_counts": event_type_counts(event_state["events"]),
        "task_failure_type_counts": failure_count_by_type(event_state["events"]),
        "missing_private_evidence_links": len(event_state["missing_private_evidence"]),
        "invalid_private_evidence_files": len(event_state["invalid_private_evidence"]),
        "stale_completed_tasks": len(event_state["stale_completed"]),
        "active_task_leases": len(lease_summary["active_leases"]),
        "expired_task_leases": len(lease_summary["expired_leases"]),
        "invalid_task_leases": len(lease_summary["invalid_leases"]),
        "blocked_tasks": task_status_counts["blocked"],
        "lease_expired_tasks": task_status_counts["lease-expired"],
        "stale_completion_tasks": task_status_counts["stale-completion"],
        "completed_tasks": task_status_counts["completed"],
        "completion_standard_counts": dict(sorted(completion_standard_counts.items())),
        "ready_tasks": task_status_counts["ready-for-ledger-review"],
        "failed_retry_ready_tasks": task_status_counts["failed-retry-ready"],
        "not_executable_index_tasks": task_status_counts["not-executable-index"],
        "claimed_tasks": task_status_counts["claimed"] + task_status_counts["in-progress"],
        "dependency_violations": len(deps),
        "dependency_violation_examples": deps[:10],
        "override_events": event_state["override_count"],
    }
    summary["gate_summary"] = gate_summary(summary)

    tasks = {
        "metadata": metadata,
        "policy": {
            "historical_truth_source": "ledger/task-events.jsonl",
            "task_selection_snapshot": "ledger/snapshots/tasks.json",
            "markdown_status_is_not_authoritative": True,
            "default_next_action": "audit-and-repair-before-implementation",
        },
        "authoritative_state": authoritative_state(metadata, summary),
        "tasks": runtime_tasks,
    }
    write_json(LEDGER_DIR / "tasks.json", tasks)
    write_json(TASK_GRAPH_FILE, build_task_graph(runtime_tasks))
    write_json(
        LEDGER_DIR / "task-runtime-summary.json",
        {
            "metadata": metadata,
            "event_errors": event_state["event_errors"],
            "missing_private_evidence": event_state["missing_private_evidence"],
            "invalid_private_evidence": event_state["invalid_private_evidence"],
            "stale_completed": event_state["stale_completed"],
            "leases": lease_summary,
            "dependency_violations": deps,
            "status_counts": dict(sorted(task_status_counts.items())),
            "completion_standard_counts": dict(sorted(completion_standard_counts.items())),
            "gate_summary": summary["gate_summary"],
        },
    )
    write_jsonl(LEDGER_DIR / "claims.jsonl", plan["claims"])
    write_jsonl(LEDGER_DIR / "deferred-items.jsonl", plan["deferred_items"])
    write_jsonl(LEDGER_DIR / "execution-flow-items.jsonl", plan["flow_items"])
    write_jsonl(LEDGER_DIR / "plan-kernel-violations.jsonl", plan["plan_kernel_violations"])
    write_json(LEDGER_DIR / "plan-docs.json", {"metadata": metadata, "documents": plan["docs"]})
    write_json(SESSION_OUT / "session-index.json", session)
    by_document_index = build_by_document_index(plan, metadata)
    write_json(by_document_dir / "index.json", by_document_index)
    claim_triage = build_claim_triage(plan, metadata)
    deferred_register = build_deferred_register(plan, metadata)
    execution_flow_register = build_execution_flow_register(plan, metadata)
    by_document_records = write_by_document_execution_records(by_document_dir, plan, metadata)
    write_json(LEDGER_DIR / "claim-triage.json", claim_triage)
    write_json(LEDGER_DIR / "deferred-register.json", deferred_register)
    write_json(LEDGER_DIR / "execution-flow-register.json", execution_flow_register)
    write_json(by_document_dir / "records.json", {"metadata": metadata, "records": by_document_records})

    (LEDGER_DIR / "source-inventory.md").write_text(
        render_source_inventory(plan, session), encoding="utf-8"
    )
    (LEDGER_DIR / "claims-triage.md").write_text(
        render_claims_triage(claim_triage, plan["claims"]), encoding="utf-8"
    )
    (LEDGER_DIR / "deferred-register.md").write_text(
        render_deferred_register(deferred_register, plan["deferred_items"]), encoding="utf-8"
    )
    (LEDGER_DIR / "execution-flow-register.md").write_text(
        render_execution_flow_register(execution_flow_register, plan["flow_items"]), encoding="utf-8"
    )
    (SESSION_OUT / "red-flags.md").write_text(render_red_flags(session), encoding="utf-8")
    (LEDGER_DIR / "repair-backlog.md").write_text(
        render_repair_backlog(plan, session), encoding="utf-8"
    )
    (by_document_dir / "README.md").write_text(
        render_by_document_readme(by_document_index), encoding="utf-8"
    )

    (LEDGER_DIR / "README.md").write_text(
        render_ledger_readme(plan, session, summary), encoding="utf-8"
    )
    write_json(LEDGER_DIR / "audit-summary.json", {"metadata": metadata, "summary": summary})
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    hard_gates = summary["gate_summary"]["hard_blocking_gates"]
    return 1 if any(int(value) for value in hard_gates.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
