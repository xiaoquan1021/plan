#!/usr/bin/env python3
"""Deterministic public snapshot projection helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - CI installs PyYAML.
    yaml = None

from schema_validation import SchemaValidationError, validate_data


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_NAMES = [
    "tasks.json",
    "task-graph.json",
    "public-state-summary.json",
    "task-runtime-summary.json",
]

IMPLEMENTATION_TASK_KINDS = {"implementation", "implementation-readiness"}
ACCEPTANCE_TASK_KINDS = {"acceptance"}
TASK_PACK_REQUIRED_KINDS = IMPLEMENTATION_TASK_KINDS | ACCEPTANCE_TASK_KINDS
PRIVATE_PATH_RE = re.compile(r"[A-Za-z]:[/\\][^\\n\\r\\t\"']*", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
TIME_KEYS = {"event_time", "timestamp", "created_at", "generated_at", "completed_at", "reviewed_at", "reconciled_at"}
PLAN_REVIEW_ALLOWED_AFTER_COMMIT_PREFIXES = (
    "ledger/reviews/",
    "ledger/evidence/",
    "docs/contracts/reviews/",
    "docs/reviews/",
)
SENSITIVE_KEYS = {
    "patient_name",
    "patient_id",
    "institution",
    "institution_name",
    "operator_name",
    "raw_log",
    "stdout",
    "stderr",
}


class ProjectionError(ValueError):
    """Raised when runtime projection inputs are inconsistent."""


def canonical_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def canonical_hash_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise ProjectionError("PyYAML is required to read YAML inputs")
        return yaml.safe_load(text)
    return json.loads(text)


def repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def normalize_for_hash(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: normalize_for_hash(data[key]) for key in sorted(data)}
    if isinstance(data, list):
        return [normalize_for_hash(item) for item in data]
    return data


def normalize_projection_inputs(data: Any) -> Any:
    if isinstance(data, dict):
        normalized = {key: normalize_projection_inputs(value) for key, value in data.items()}
        for list_key in ("events", "task_results", "gate_results", "epic_reviews", "plan_rewrite_reviews"):
            value = normalized.get(list_key)
            if isinstance(value, list):
                normalized[list_key] = sorted(
                    value,
                    key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                )
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(data, list):
        return [normalize_projection_inputs(item) for item in data]
    return data


def hash_data(data: Any) -> str:
    return sha256_bytes(canonical_hash_bytes(normalize_for_hash(data)))


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def canonical_task_pack_hash(task_pack: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(task_pack, ensure_ascii=False))
    normalized["task_pack_sha256"] = None
    return hash_data(normalized)


def canonical_contract_hash(raw_contract: dict[str, Any]) -> str:
    normalized = {
        key: value
        for key, value in json.loads(json.dumps(raw_contract, ensure_ascii=False)).items()
        if not str(key).startswith("_")
    }
    return hash_data(normalized)


def canonical_approval_record_hash(record: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(record, ensure_ascii=False))
    normalized["approval_record_sha256"] = None
    return hash_data(normalized)


def canonical_plan_rewrite_review_hash(record: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(record, ensure_ascii=False))
    normalized["review_record_sha256"] = None
    return hash_data(normalized)


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json_or_yaml_file(path_value: str | Path) -> Any:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return load_data(path)


def source_commit_time() -> str | None:
    """Deprecated compatibility hook. Snapshots must not use Git HEAD time."""
    return None


def timestamp_from_epoch() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "0")
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat(timespec="seconds")


def definitions_generated_at() -> str:
    if "SOURCE_DATE_EPOCH" in os.environ:
        return timestamp_from_epoch()
    return "1970-01-01T00:00:00+00:00"


def parse_input_time(value: str) -> datetime:
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProjectionError(f"invalid timestamp {value}") from exc
    if parsed.tzinfo is None:
        raise ProjectionError(f"invalid timestamp {value}: timezone required")
    return parsed.astimezone(timezone.utc)


def latest_timestamp_from_inputs(inputs: list[Any]) -> str | None:
    candidates: list[datetime] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in TIME_KEYS and isinstance(item, str):
                    candidates.append(parse_input_time(item))
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for item in inputs:
        walk(item)
    return max(candidates).isoformat(timespec="seconds") if candidates else None


def deterministic_generated_at(runtime_inputs: list[Any], *, definitions_only: bool) -> str:
    if definitions_only:
        return definitions_generated_at()
    return latest_timestamp_from_inputs(runtime_inputs) or timestamp_from_epoch()


def redact_private(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: redact_private(item)
            for key, item in value.items()
            if key not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [redact_private(item) for item in value]
    if isinstance(value, str):
        return PRIVATE_PATH_RE.sub("PRIVATE_PATH_REDACTED", value)
    return value


def load_epic_contracts() -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "docs/contracts/epics").glob("*.yaml")):
        data = load_data(path)
        try:
            validate_data(data, "epic-contract.schema.json", label=repo_relative(path))
        except SchemaValidationError as exc:
            raise ProjectionError(str(exc)) from exc
        computed = canonical_contract_hash(data)
        data["_path"] = repo_relative(path)
        data["_computed_sha256"] = computed
        contracts[str(data["epic_id"])] = data
    return contracts


def approval_record_valid(epic_contract: dict[str, Any]) -> bool:
    if epic_contract.get("decision_state") != "approved":
        return False
    record = epic_contract.get("approval_record")
    if not isinstance(record, dict):
        return False
    if record.get("record_type") == "none" or not is_sha256(record.get("record_sha256")):
        return False
    record_path = record.get("record_path")
    if not isinstance(record_path, str) or not record_path:
        return False
    path = ROOT / record_path
    if not path.exists():
        return False
    try:
        approval = load_data(path)
        validate_data(approval, "epic-contract-approval.schema.json", label=record_path)
    except (OSError, json.JSONDecodeError, SchemaValidationError, ValueError):
        return False
    computed = canonical_approval_record_hash(approval)
    try:
        parse_input_time(str(approval.get("reviewed_at")))
    except ProjectionError:
        return False
    return (
        computed == approval.get("approval_record_sha256")
        and computed == record.get("record_sha256")
        and approval.get("decision") == "approved"
        and approval.get("reviewer_role") == "Codex A"
        and approval.get("epic_id") == epic_contract.get("epic_id")
        and approval.get("epic_contract_sha256") == epic_contract.get("_computed_sha256")
        and approval.get("unresolved_decisions") == []
        and approval.get("required_repairs") == []
        and bool(approval.get("architecture_findings"))
    )


def enrich_task_pack(task: dict[str, Any]) -> None:
    path_value = task.get("task_pack_path")
    if path_value in (None, ""):
        task["task_pack_path"] = None
        task["task_pack_schema_valid"] = False if task.get("task_kind") in TASK_PACK_REQUIRED_KINDS else None
        task["task_pack_hash_valid"] = False if task.get("task_kind") in TASK_PACK_REQUIRED_KINDS else None
        task["issuance_status"] = None
        task["execution_ready"] = False if task.get("task_kind") in TASK_PACK_REQUIRED_KINDS else None
        return
    path = ROOT / str(path_value)
    if not path.exists():
        raise ProjectionError(f"{task['task_id']}: task pack does not exist: {path_value}")
    pack = load_data(path)
    try:
        validate_data(pack, "atomic-task-pack.schema.json", label=str(path_value))
    except SchemaValidationError as exc:
        raise ProjectionError(str(exc)) from exc
    if pack.get("task_id") != task.get("task_id"):
        raise ProjectionError(f"{task['task_id']}: task pack task_id mismatch")
    if pack.get("epic_id") != task.get("epic_id"):
        raise ProjectionError(f"{task['task_id']}: task pack epic_id mismatch")
    computed = canonical_task_pack_hash(pack)
    declared = pack.get("task_pack_sha256")
    hash_valid = declared is None or declared == computed
    task.update(
        {
            "task_pack_path": str(path_value),
            "task_pack_schema_valid": True,
            "computed_task_pack_sha256": computed,
            "declared_task_pack_sha256": declared,
            "task_pack_hash_valid": hash_valid,
            "issuance_status": pack.get("issuance_status"),
            "execution_ready": pack.get("execution_ready"),
            "base_commit": pack.get("base_commit"),
            "rollback_point": pack.get("rollback_point"),
            "worktree_binding": pack.get("worktree_binding"),
            "epic_contract_sha256": pack.get("epic_contract_sha256"),
            "task_pack_sha256": computed,
            "dependency_contract_sha256": pack.get("dependency_contract_sha256"),
            "implementation_dependency_lock_sha256": pack.get("implementation_dependency_lock_sha256"),
            "dependency_lock_sha256": pack.get("implementation_dependency_lock_sha256"),
            "toolchain_manifest_sha256": pack.get("toolchain_manifest_sha256"),
        }
    )


def enrich_epic_contract(task: dict[str, Any], epic_contracts: dict[str, dict[str, Any]]) -> None:
    epic_id = task.get("epic_id")
    contract = epic_contracts.get(str(epic_id)) if epic_id else None
    if contract is None:
        task["epic_contract_path"] = None
        task["computed_epic_contract_sha256"] = None
        task["epic_contract_status"] = "not-started"
        task["epic_contract_decision_state"] = "none"
        return
    task["epic_contract_path"] = contract.get("_path")
    task["computed_epic_contract_sha256"] = contract.get("_computed_sha256")
    task["epic_contract_decision_state"] = contract.get("decision_state")
    task["epic_contract_approval_record"] = contract.get("approval_record")
    task["epic_contract_status"] = "approved" if approval_record_valid(contract) else "draft"


def load_task_definitions() -> tuple[list[dict[str, Any]], str]:
    index_path = ROOT / "ledger/task-definitions/index.yaml"
    index = load_data(index_path)
    try:
        validate_data(index, "task-definition-index.schema.json", label=repo_relative(index_path))
    except SchemaValidationError as exc:
        raise ProjectionError(str(exc)) from exc
    source_material: list[bytes] = [canonical_bytes(index)]
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    epic_contracts = load_epic_contracts()
    for entry in sorted(index["task_definitions"], key=lambda item: item["task_id"]):
        task_path = ROOT / entry["path"]
        task = load_data(task_path)
        try:
            validate_data(task, "task-definition.schema.json", label=entry["path"])
        except SchemaValidationError as exc:
            raise ProjectionError(str(exc)) from exc
        task_id = task["task_id"]
        if task_id in seen:
            raise ProjectionError(f"duplicate task definition: {task_id}")
        seen.add(task_id)
        enrich_task_pack(task)
        enrich_epic_contract(task, epic_contracts)
        source_material.append(canonical_bytes(task))
        tasks.append(task)
    return tasks, sha256_bytes(b"".join(source_material))


def definition_projection(task: dict[str, Any]) -> dict[str, Any]:
    status = task.get("status", "ready-for-ledger-review")
    return {
        "id": task["task_id"],
        "task_id": task["task_id"],
        "title": task["title"],
        "task_kind": task["task_kind"],
        "required_for_epic": task.get("required_for_epic", False),
        "plan_rewrite_milestone": task.get("plan_rewrite_milestone"),
        "product_milestone": task.get("product_milestone"),
        "epic_id": task.get("epic_id"),
        "task_pack_path": task.get("task_pack_path"),
        "task_pack_schema_valid": task.get("task_pack_schema_valid"),
        "computed_task_pack_sha256": task.get("computed_task_pack_sha256"),
        "declared_task_pack_sha256": task.get("declared_task_pack_sha256"),
        "task_pack_hash_valid": task.get("task_pack_hash_valid"),
        "issuance_status": task.get("issuance_status"),
        "execution_ready": task.get("execution_ready"),
        "base_commit": task.get("base_commit"),
        "rollback_point": task.get("rollback_point"),
        "worktree_binding": task.get("worktree_binding"),
        "epic_contract_path": task.get("epic_contract_path"),
        "computed_epic_contract_sha256": task.get("computed_epic_contract_sha256"),
        "epic_contract_sha256": task.get("epic_contract_sha256") or task.get("computed_epic_contract_sha256"),
        "epic_contract_status": task.get("epic_contract_status"),
        "epic_contract_decision_state": task.get("epic_contract_decision_state"),
        "dependency_contract_sha256": task.get("dependency_contract_sha256"),
        "implementation_dependency_lock_sha256": task.get("implementation_dependency_lock_sha256"),
        "dependency_lock_sha256": task.get("dependency_lock_sha256"),
        "toolchain_manifest_sha256": task.get("toolchain_manifest_sha256"),
        "source_md": (task.get("source_contracts") or [None])[0],
        "source_contracts": task.get("source_contracts", []),
        "source_contract_hashes": task.get("source_contract_hashes", {}),
        "status": status,
        "decision_state": task.get("decision_state", "none"),
        "task_dependencies": task.get("dependencies", []),
        "allowed_logical_scopes": task.get("allowed_logical_scopes", []),
        "claimability_rules": task.get("claimability_rules", []),
        "blocked_reason": task.get("blocked_reason"),
        "required_evidence": task.get("required_evidence", []),
        "unblock_condition": task.get("unblock_condition"),
        "owner": task.get("owner"),
        "next_action": task.get("next_action"),
        "supersedes": task.get("supersedes", []),
        "evidence_status": "definitions-only",
        "workspace_state": "not-projected",
        "runtime_projection": "none",
        "implementation_evidence": "none",
        "acceptance_evidence": "none",
        "plan_gate_evidence": "not-run",
        "plan_review_evidence": "not-run",
        "stale_reasons": [],
    }


def list_from_projection(data: Any, key: str) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ProjectionError(f"{key} projection must be object or list")
    aliases = {
        "events": ["events", "runtime_events"],
        "task_results": ["task_results", "completion_records"],
        "gate_results": ["gate_results", "codex_b_gate_results"],
        "epic_reviews": ["epic_reviews", "codex_a_epic_reviews"],
        "plan_rewrite_reviews": ["plan_rewrite_reviews", "codex_a_plan_rewrite_reviews"],
    }
    for alias in aliases.get(key, [key]):
        value = data.get(alias)
        if value is not None:
            if not isinstance(value, list):
                raise ProjectionError(f"{key} must be a list")
            return value
    return []


def validate_known_task_ids(records: list[dict[str, Any]], known: set[str], label: str) -> None:
    for record in records:
        task_id = record.get("task_id")
        if task_id is not None and task_id not in known:
            raise ProjectionError(f"{label} references unknown task_id {task_id}")


def validate_private_inputs(
    *,
    runtime_data: Any,
    completion_data: Any,
    workspace_data: Any,
    known_tasks: set[str],
    known_epics: set[str],
    known_plan_milestones: set[str],
) -> None:
    try:
        validate_data(runtime_data, "runtime-projection.schema.json", label="runtime projection")
        validate_data(completion_data, "completion-projection.schema.json", label="completion projection")
        validate_data(workspace_data, "workspace-reconciliation.schema.json", label="workspace reconciliation")
    except SchemaValidationError as exc:
        raise ProjectionError(str(exc)) from exc

    events = list_from_projection(runtime_data, "events")
    task_results = list_from_projection(completion_data, "task_results")
    gate_results = list_from_projection(completion_data, "gate_results")
    epic_reviews = list_from_projection(completion_data, "epic_reviews")
    plan_rewrite_reviews = list_from_projection(completion_data, "plan_rewrite_reviews")
    validate_known_task_ids(events, known_tasks, "runtime event")
    validate_known_task_ids(task_results, known_tasks, "task result")
    validate_known_task_ids(gate_results, known_tasks, "gate result")
    if workspace_data.get("epic_id") not in (None, "") and str(workspace_data.get("epic_id")) not in known_epics:
        raise ProjectionError(f"workspace reconciliation references unknown epic_id {workspace_data.get('epic_id')}")
    integrated = workspace_data.get("integrated_task_commits")
    if isinstance(integrated, dict):
        for key in integrated:
            if str(key) not in known_tasks:
                raise ProjectionError(f"workspace reconciliation references unknown task_id {key}")

    seen_events: set[str] = set()
    for index, event in enumerate(events):
        event_id = event.get("event_id")
        if event_id in seen_events:
            raise ProjectionError(f"runtime projection: events/{index}: duplicate event_id {event_id}")
        seen_events.add(str(event_id))
        if event.get("event_time"):
            parse_input_time(str(event["event_time"]))

    for label, records in {"task result": task_results, "gate result": gate_results}.items():
        terminal_by_task: dict[str, dict[str, Any]] = {}
        for record in records:
            task_id = str(record.get("task_id"))
            prior = terminal_by_task.get(task_id)
            if prior is not None and prior != record:
                raise ProjectionError(f"{label} has conflicting terminal records for task_id {task_id}")
            terminal_by_task[task_id] = record

    accepted_reviews: dict[str, dict[str, Any]] = {}
    for index, review in enumerate(epic_reviews):
        epic_id = review.get("epic_id")
        if epic_id not in known_epics:
            raise ProjectionError(f"epic review/{index} references unknown epic_id {epic_id}")
        if review.get("decision") == "accepted":
            prior = accepted_reviews.get(str(epic_id))
            if prior is not None and prior != review:
                raise ProjectionError(f"epic review has multiple accepted records for epic_id {epic_id}")
            accepted_reviews[str(epic_id)] = review

    accepted_plan_reviews: dict[tuple[str, str], dict[str, Any]] = {}
    for index, review in enumerate(plan_rewrite_reviews):
        milestone = review.get("plan_rewrite_milestone")
        if milestone not in known_plan_milestones:
            raise ProjectionError(f"plan rewrite review/{index} references unknown plan_rewrite_milestone {milestone}")
        if review.get("reviewed_at"):
            parse_input_time(str(review["reviewed_at"]))
        if review.get("decision") == "accepted":
            role = str(review.get("reviewer_role"))
            key = (str(milestone), role)
            prior = accepted_plan_reviews.get(key)
            if prior is not None and prior != review:
                raise ProjectionError(f"multiple accepted plan rewrite reviews for {milestone} role {role}")
            accepted_plan_reviews[key] = review


def git_commit_exists(commit: str) -> bool:
    if not isinstance(commit, str) or not GIT_COMMIT_RE.fullmatch(commit):
        return False
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def git_is_ancestor(commit: str, head: str = "HEAD") -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, head],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def changed_files_since_commit(commit: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{commit}..HEAD"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ProjectionError(result.stderr.strip() or "git diff failed while checking plan review commit binding")
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def plan_review_change_allowed(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith(PLAN_REVIEW_ALLOWED_AFTER_COMMIT_PREFIXES)


def current_public_snapshot_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in SNAPSHOT_NAMES:
        path = ROOT / "ledger/snapshots" / name
        if path.exists():
            hashes[name] = file_sha256(path)
    return hashes


def repository_relative_existing_file(path_value: Any, reasons: list[str], reason_prefix: str) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        reasons.append(f"{reason_prefix}-missing")
        return None
    path = Path(path_value)
    if path.is_absolute() or ".." in path.parts:
        reasons.append(f"{reason_prefix}-invalid-path")
        return None
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        reasons.append(f"{reason_prefix}-invalid-path")
        return None
    if not resolved.exists():
        reasons.append(f"{reason_prefix}-missing")
        return None
    return resolved


def ci_verification_report_valid(item: dict[str, Any], reasons: list[str]) -> bool:
    path_value = item.get("verification_report_path")
    hash_value = item.get("verification_report_sha256")
    if path_value in (None, "") and hash_value in (None, ""):
        return False
    report_path = repository_relative_existing_file(path_value, reasons, "ci-verification-report")
    if report_path is None:
        return False
    if not is_sha256(hash_value) or file_sha256(report_path) != hash_value:
        reasons.append("ci-verification-report-hash-mismatch")
        return False
    try:
        report = load_data(report_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        reasons.append(f"ci-verification-report-invalid:{exc}")
        return False

    ok = True
    for key in ["workflow_name", "run_id", "run_url", "commit_sha", "conclusion"]:
        if report.get(key) != item.get(key):
            reasons.append(f"ci-verification-report-{key}-mismatch")
            ok = False
    if report.get("conclusion") != "success":
        reasons.append("ci-verification-report-not-success")
        ok = False
    if report.get("verified_via") not in {"GitHub connector _fetch_workflow_run_jobs", "GitHub Actions API"}:
        reasons.append("ci-verification-report-source-invalid")
        ok = False

    expected_jobs = {job.get("name"): job.get("conclusion") for job in item.get("jobs", []) if isinstance(job, dict)}
    actual_jobs = {job.get("name"): job for job in report.get("jobs", []) if isinstance(job, dict)}
    if not expected_jobs:
        reasons.append("ci-jobs-missing")
        ok = False
    for name, conclusion in expected_jobs.items():
        actual = actual_jobs.get(name)
        if not actual or actual.get("conclusion") != conclusion or conclusion != "success":
            reasons.append("ci-verification-report-job-mismatch")
            ok = False
            break
        steps = actual.get("steps") if isinstance(actual.get("steps"), list) else []
        if not steps:
            reasons.append("ci-verification-report-steps-missing")
            ok = False
            break
        for step in steps:
            if not isinstance(step, dict) or step.get("status") != "completed" or step.get("conclusion") != "success":
                reasons.append("ci-verification-report-step-not-success")
                ok = False
                break
    return ok


def validate_ci_evidence(review: dict[str, Any], reasons: list[str]) -> None:
    plan_commit = review.get("plan_commit_sha")
    evidence = review.get("ci_evidence") if isinstance(review.get("ci_evidence"), list) else []
    if not evidence:
        reasons.append("ci-evidence-missing")
        return
    for item in evidence:
        if not isinstance(item, dict):
            reasons.append("ci-evidence-invalid")
            continue
        if item.get("workflow_name") != "plan-contracts":
            reasons.append("ci-workflow-mismatch")
        if item.get("commit_sha") != plan_commit:
            reasons.append("ci-commit-mismatch")
        if item.get("conclusion") != "success":
            reasons.append("ci-not-success")
        if not item.get("run_id") or not item.get("run_url"):
            reasons.append("ci-run-missing")
        jobs = item.get("jobs") if isinstance(item.get("jobs"), list) else []
        if not jobs:
            reasons.append("ci-jobs-missing")
        for job in jobs:
            if not isinstance(job, dict) or job.get("conclusion") != "success":
                reasons.append("ci-job-not-success")
                break
        if ci_verification_report_valid(item, reasons):
            continue
        verified, verify_reasons = github_ci_evidence_verified(item)
        if not verified:
            reasons.extend(verify_reasons)


def github_repo_slug() -> str | None:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", remote)
    if not match:
        return None
    return f"{match.group('owner')}/{match.group('repo')}"


def fetch_github_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "xq-plan-harness",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - public GitHub API only.
        return json.loads(response.read().decode("utf-8"))


def github_ci_evidence_verified(item: dict[str, Any]) -> tuple[bool, list[str]]:
    repo = github_repo_slug()
    if not repo:
        return False, ["ci-repo-unresolved"]
    run_id = item.get("run_id")
    if run_id in (None, ""):
        return False, ["ci-run-missing"]
    try:
        run = fetch_github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}")
        jobs_payload = fetch_github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return False, [f"ci-run-unverified:{exc}"]

    reasons: list[str] = []
    if run.get("name") != item.get("workflow_name"):
        reasons.append("ci-workflow-mismatch")
    if run.get("head_sha") != item.get("commit_sha"):
        reasons.append("ci-commit-mismatch")
    if run.get("conclusion") != item.get("conclusion") or run.get("conclusion") != "success":
        reasons.append("ci-not-success")
    expected_jobs = {job.get("name"): job.get("conclusion") for job in item.get("jobs", []) if isinstance(job, dict)}
    actual_jobs = {job.get("name"): job.get("conclusion") for job in jobs_payload.get("jobs", []) if isinstance(job, dict)}
    for name, conclusion in expected_jobs.items():
        if actual_jobs.get(name) != conclusion or conclusion != "success":
            reasons.append("ci-job-not-success")
    return not reasons, sorted(set(reasons))


def validate_snapshot_evidence(review: dict[str, Any], reasons: list[str]) -> None:
    evidence = review.get("snapshot_hashes") if isinstance(review.get("snapshot_hashes"), dict) else {}
    actual = current_public_snapshot_hashes()
    if not evidence:
        reasons.append("snapshot-hashes-missing")
        return
    for name in SNAPSHOT_NAMES:
        if name not in evidence:
            reasons.append(f"snapshot-hash-missing:{name}")
        elif evidence.get(name) != actual.get(name):
            reasons.append(f"snapshot-hash-mismatch:{name}")


def validate_migration_evidence(review: dict[str, Any], reasons: list[str]) -> None:
    evidence = review.get("migration_evidence") if isinstance(review.get("migration_evidence"), list) else []
    if not evidence:
        reasons.append("migration-evidence-missing")
        return
    valid = False
    for item in evidence:
        if not isinstance(item, dict):
            reasons.append("migration-evidence-invalid")
            continue
        if item.get("exit_code") != 0 or item.get("status") != "passed":
            reasons.append("migration-check-failed")
        command = str(item.get("command") or "")
        if "migrate_legacy_ledger.py" not in command or "--check" not in command:
            reasons.append("migration-command-missing")
        report_path = item.get("report_path")
        report_sha256 = item.get("report_sha256")
        if not isinstance(report_path, str) or not isinstance(report_sha256, str):
            reasons.append("migration-report-missing")
            continue
        path = ROOT / report_path
        if not path.exists():
            reasons.append("migration-report-missing")
            continue
        if not is_sha256(report_sha256) or file_sha256(path) != report_sha256:
            reasons.append("migration-report-hash-mismatch")
            continue
        valid = True
    if not valid:
        reasons.append("migration-evidence-unverified")


def validate_public_preflight_evidence(review: dict[str, Any], reasons: list[str]) -> None:
    evidence = review.get("public_preflight_evidence") if isinstance(review.get("public_preflight_evidence"), list) else []
    if not evidence:
        reasons.append("public-preflight-evidence-missing")
        return
    for item in evidence:
        if not isinstance(item, dict):
            reasons.append("public-preflight-evidence-invalid")
            continue
        if item.get("exit_code") != 0 or item.get("status") != "passed":
            reasons.append("public-preflight-failed")
        if "preflight_plan.py" not in str(item.get("command") or "") or "--public" not in str(item.get("command") or ""):
            reasons.append("public-preflight-command-missing")


def validate_plan_commit_binding(review: dict[str, Any], reasons: list[str]) -> None:
    commit = review.get("plan_commit_sha")
    if not isinstance(commit, str) or not GIT_COMMIT_RE.fullmatch(commit):
        reasons.append("plan-commit-invalid")
        return
    if not git_commit_exists(commit):
        reasons.append("plan-commit-missing")
        return
    if not git_is_ancestor(commit):
        reasons.append("plan-commit-not-ancestor")
        return
    changed = changed_files_since_commit(commit)
    if any(not plan_review_change_allowed(path) for path in changed):
        reasons.append("plan-review-stale-after-reviewed-commit")


def valid_plan_rewrite_review(review: dict[str, Any] | None, expected_role: str) -> tuple[bool, list[str]]:
    if not review:
        return False, [f"missing-{expected_role.lower().replace(' ', '-')}-review"]
    reasons: list[str] = []
    if review.get("decision") != "accepted":
        reasons.append("plan-review-not-accepted")
    if review.get("reviewer_role") != expected_role:
        reasons.append("plan-review-role-mismatch")
    if review.get("review_record_sha256") != canonical_plan_rewrite_review_hash(review):
        reasons.append("plan-review-self-hash-mismatch")
    if review.get("unresolved_findings") not in ([], None):
        reasons.append("plan-review-unresolved-findings")
    if review.get("required_repairs") not in ([], None):
        reasons.append("plan-review-required-repairs")
    for key in ["required_outcomes", "ci_evidence", "snapshot_hashes", "migration_evidence", "public_preflight_evidence"]:
        require_nonempty(review, key, reasons, f"plan-review-missing-{key}")
    try:
        parse_input_time(str(review.get("reviewed_at")))
    except ProjectionError:
        reasons.append("plan-review-invalid-reviewed-at")
    validate_plan_commit_binding(review, reasons)
    validate_ci_evidence(review, reasons)
    validate_snapshot_evidence(review, reasons)
    validate_migration_evidence(review, reasons)
    validate_public_preflight_evidence(review, reasons)
    return not reasons, sorted(set(reasons))


def index_by_task(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in sorted(records, key=lambda item: (str(item.get("task_id", "")), hash_data(item))):
        task_id = record.get("task_id")
        if isinstance(task_id, str):
            indexed[task_id] = record
    return indexed


def latest_event_status(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in sorted(events, key=lambda item: (parse_input_time(str(item.get("event_time") or item.get("timestamp"))), str(item.get("event_id") or ""))):
        task_id = event.get("task_id")
        if isinstance(task_id, str):
            latest[task_id] = event
    return latest


def status_from_event(event: dict[str, Any]) -> str | None:
    if "status" in event:
        return str(event["status"])
    return {
        "task_claimed": "claimed",
        "task_started": "in-progress",
        "task_failed": "failed-retry-ready",
        "task_blocked": "blocked",
        "task_reopened": "ready-for-ledger-review",
    }.get(str(event.get("event_type", "")))


def expected_hashes(task: dict[str, Any], workspace: dict[str, Any]) -> dict[str, Any]:
    source_hashes = task.get("source_contract_hashes") if isinstance(task.get("source_contract_hashes"), dict) else {}
    return {
        "base_commit": task.get("base_commit") or workspace.get("base_commit") or source_hashes.get("base_commit"),
        "task_pack_sha256": task.get("computed_task_pack_sha256") or task.get("task_pack_sha256") or source_hashes.get("task_pack_sha256"),
        "epic_contract_sha256": task.get("epic_contract_sha256") or task.get("computed_epic_contract_sha256") or task.get("contract_sha256") or source_hashes.get("epic_contract_sha256") or source_hashes.get("contract_sha256"),
        "dependency_contract_sha256": task.get("dependency_contract_sha256") or workspace.get("dependency_contract_sha256") or source_hashes.get("dependency_contract_sha256"),
        "implementation_dependency_lock_sha256": task.get("implementation_dependency_lock_sha256") or workspace.get("implementation_dependency_lock_sha256") or source_hashes.get("implementation_dependency_lock_sha256"),
        "dependency_lock_sha256": task.get("dependency_lock_sha256") or workspace.get("dependency_lock_sha256") or workspace.get("implementation_dependency_lock_sha256") or source_hashes.get("dependency_lock_sha256"),
        "toolchain_manifest_sha256": task.get("toolchain_manifest_sha256") or workspace.get("toolchain_manifest_sha256") or source_hashes.get("toolchain_manifest_sha256"),
    }


def check_hashes(
    record: dict[str, Any] | None,
    expected: dict[str, Any],
    key_map: dict[str, str] | None = None,
    *,
    require_expected: bool = False,
) -> list[str]:
    if record is None:
        return []
    reasons: list[str] = []
    key_map = key_map or {}
    for key, expected_value in expected.items():
        if expected_value in (None, "", {}):
            if require_expected:
                reasons.append(f"missing-{key}")
            continue
        record_key = key_map.get(key, key)
        actual = record.get(record_key)
        if actual in (None, ""):
            reasons.append(f"missing-{key}")
        elif actual != expected_value:
            reasons.append(f"{key}-changed")
    return reasons


def require_nonempty(record: dict[str, Any], key: str, reasons: list[str], reason: str | None = None) -> None:
    value = record.get(key)
    if value in (None, "", []):
        reasons.append(reason or f"missing-{key}")


def require_sha256(record: dict[str, Any], key: str, reasons: list[str]) -> None:
    value = record.get(key)
    if not is_sha256(value):
        reasons.append(f"missing-{key}" if value in (None, "") else f"invalid-{key}")


def valid_task_result(task: dict[str, Any], workspace: dict[str, Any], result: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not result:
        return False, ["missing-task-result"]
    reasons: list[str] = []
    passing = result.get("decision") in {"completed", "passed"} or result.get("overall_status") in {"passed", "completed"}
    if result.get("decision") not in {"completed", "gate-required", "ready-for-gate", "passed"} and result.get("overall_status") not in {"passed", "completed"}:
        reasons.append("task-result-not-passing")
    if passing:
        for key in ["task_pack_sha256", "epic_contract_sha256", "dependency_lock_sha256", "toolchain_manifest_sha256"]:
            require_sha256(result, key, reasons)
        for key in ["base_commit", "result_commit", "changed_files", "commands_run", "test_results", "artifacts"]:
            require_nonempty(result, key, reasons)
        if result.get("unresolved_issues") not in ([], None):
            reasons.append("task-result-unresolved-issues")
    reasons.extend(check_hashes(result, expected_hashes(task, workspace), require_expected=True))
    return not reasons, reasons


def valid_gate(task: dict[str, Any], workspace: dict[str, Any], gate: dict[str, Any] | None, result: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not gate:
        return False, ["missing-b-gate-result"]
    reasons: list[str] = []
    if gate.get("decision") != "accepted":
        reasons.append("b-gate-not-accepted")
    for key in ["task_pack_sha256", "epic_contract_sha256"]:
        require_sha256(gate, key, reasons)
    for key in ["base_commit", "result_commit", "changed_files", "commands_reexecuted", "tests_observed"]:
        require_nonempty(gate, key, reasons)
    if gate.get("base_commit") and gate.get("result_commit") and gate.get("base_commit") == gate.get("result_commit"):
        reasons.append("gate-result-commit-equals-base")
    allowed = gate.get("allowed_path_check") if isinstance(gate.get("allowed_path_check"), dict) else {}
    if allowed.get("passed") is not True:
        reasons.append("gate-allowed-path-check-failed")
    if allowed.get("violations") not in ([], None):
        reasons.append("gate-allowed-path-violations")
    if gate.get("workspace_clean_before") is not True:
        reasons.append("gate-workspace-not-clean-before")
    if gate.get("workspace_clean_after") is not True:
        reasons.append("gate-workspace-not-clean-after")
    commands = gate.get("commands_reexecuted") if isinstance(gate.get("commands_reexecuted"), list) else []
    exits = gate.get("exit_codes") if isinstance(gate.get("exit_codes"), list) else []
    if not commands:
        reasons.append("gate-commands-reexecuted-missing")
    if len(commands) != len(exits):
        reasons.append("gate-exit-code-count-mismatch")
    if any(code != 0 for code in exits):
        reasons.append("gate-command-exit-nonzero")
    if not gate.get("tests_observed"):
        reasons.append("gate-tests-observed-missing")
    integrity = gate.get("test_integrity_check") if isinstance(gate.get("test_integrity_check"), dict) else {}
    if integrity.get("passed") is not True:
        reasons.append("gate-test-integrity-failed")
    forbidden = gate.get("forbidden_scan") if isinstance(gate.get("forbidden_scan"), dict) else {}
    if forbidden.get("passed") is not True:
        reasons.append("gate-forbidden-scan-failed")
    if forbidden.get("findings") not in ([], None):
        reasons.append("gate-forbidden-scan-findings")
    artifacts = gate.get("result_artifact_hashes") if isinstance(gate.get("result_artifact_hashes"), list) else []
    if not artifacts:
        reasons.append("gate-artifact-hash-missing")
    for artifact_hash in artifacts:
        if not is_sha256(artifact_hash):
            reasons.append("gate-artifact-hash-invalid")
            break
    if gate.get("rework_reason") is not None:
        reasons.append("gate-rework-reason-present")
    if gate.get("escalation_reason") is not None:
        reasons.append("gate-escalation-reason-present")
    if result and result.get("task_pack_sha256") and gate.get("task_pack_sha256") != result.get("task_pack_sha256"):
        reasons.append("task-pack-hash-mismatch")
    reasons.extend(check_hashes(gate, expected_hashes(task, workspace), require_expected=True))
    return not reasons, reasons


def valid_epic_review(task: dict[str, Any], workspace: dict[str, Any], review: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not review:
        return False, ["missing-a-epic-review"]
    reasons: list[str] = []
    if review.get("decision") != "accepted":
        reasons.append("epic-review-not-accepted")
    require_sha256(review, "epic_contract_sha256", reasons)
    for key in ["review_base_commit", "review_head_commit", "required_outcomes", "architecture_constraints", "acceptance_evidence"]:
        require_nonempty(review, key, reasons)
    if review.get("contract_defects") not in ([], None):
        reasons.append("epic-review-contract-defects")
    if review.get("required_repairs") not in ([], None):
        reasons.append("epic-review-required-repairs")
    for risk in review.get("unresolved_risks") or []:
        if isinstance(risk, dict) and risk.get("severity") == "blocking":
            reasons.append("epic-review-blocking-risk")
            break
    all_expected = expected_hashes(task, workspace)
    expected = {
        key: all_expected.get(key)
        for key in ["base_commit", "epic_contract_sha256", "dependency_lock_sha256", "toolchain_manifest_sha256"]
    }
    reasons.extend(check_hashes(review, expected, {"base_commit": "review_base_commit"}, require_expected=True))
    return not reasons, reasons


def epic_review_integration_reasons(
    review: dict[str, Any] | None,
    workspace: dict[str, Any],
    required_tasks: list[dict[str, Any]],
    gates_by_task: dict[str, dict[str, Any]],
) -> list[str]:
    if not review:
        return []
    reasons: list[str] = []
    workspace_epic_id = workspace.get("epic_id")
    if workspace_epic_id in (None, "") or workspace_epic_id != review.get("epic_id"):
        reasons.append("workspace-epic-id-mismatch")
    if workspace.get("epic_base_commit") in (None, "") or workspace.get("epic_base_commit") != review.get("review_base_commit"):
        reasons.append("epic-review-base-mismatch")
    if workspace.get("epic_head_commit") in (None, "") or workspace.get("epic_head_commit") != review.get("review_head_commit"):
        reasons.append("epic-review-head-mismatch")
    integrated = workspace.get("integrated_task_commits") if isinstance(workspace.get("integrated_task_commits"), dict) else {}
    for required in required_tasks:
        task_id = str(required.get("task_id") or required.get("id"))
        integrated_commit = integrated.get(task_id)
        gate = gates_by_task.get(task_id)
        if not integrated_commit:
            reasons.append("required-task-commit-missing")
            continue
        if not gate or not gate.get("result_commit"):
            reasons.append("required-task-commit-missing")
            continue
        if gate.get("result_commit") != integrated_commit:
            reasons.append("required-task-commit-mismatch")
    return sorted(set(reasons))


def task_pack_completion_reasons(task: dict[str, Any]) -> list[str]:
    if task.get("task_kind") not in TASK_PACK_REQUIRED_KINDS:
        return []
    reasons: list[str] = []
    if not task.get("task_pack_path"):
        reasons.append("missing-task-pack")
    if task.get("task_pack_schema_valid") is not True:
        reasons.append("task-pack-schema-invalid")
    if task.get("issuance_status") != "issued":
        reasons.append(f"task-pack-{task.get('issuance_status') or 'missing'}")
    if task.get("execution_ready") is not True:
        reasons.append("execution-ready-false")
    for key in ["base_commit", "rollback_point", "worktree_binding"]:
        if not task.get(key):
            reasons.append(f"missing-{key}")
    if task.get("task_pack_hash_valid") is not True:
        reasons.append("task-pack-hash-mismatch")
    if task.get("epic_contract_status") != "approved":
        reasons.append("epic-contract-not-approved")
    return reasons


def apply_full_projection(
    projected: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    runtime_data: Any,
    completion_data: Any,
    workspace_data: Any,
) -> None:
    known = {str(task["task_id"]) for task in definitions}
    known_epics = {str(task.get("epic_id")) for task in definitions if task.get("epic_id")}
    known_plan_milestones = {str(task.get("plan_rewrite_milestone")) for task in definitions if task.get("plan_rewrite_milestone")}
    by_task_id = {task["task_id"]: task for task in projected}
    definition_by_id = {task["task_id"]: task for task in definitions}
    events = list_from_projection(runtime_data, "events")
    task_results = list_from_projection(completion_data, "task_results")
    gate_results = list_from_projection(completion_data, "gate_results")
    epic_reviews = list_from_projection(completion_data, "epic_reviews")
    plan_rewrite_reviews = list_from_projection(completion_data, "plan_rewrite_reviews")
    validate_private_inputs(
        runtime_data=runtime_data,
        completion_data=completion_data,
        workspace_data=workspace_data,
        known_tasks=known,
        known_epics=known_epics,
        known_plan_milestones=known_plan_milestones,
    )

    latest_events = latest_event_status(events)
    results_by_task = index_by_task(task_results)
    gates_by_task = index_by_task(gate_results)
    reviews_by_epic: dict[str, dict[str, Any]] = {}
    for review in sorted(epic_reviews, key=lambda item: (str(item.get("epic_id", "")), hash_data(item))):
        epic_id = review.get("epic_id")
        if isinstance(epic_id, str):
            reviews_by_epic[epic_id] = review
    plan_reviews_by_milestone_role: dict[tuple[str, str], dict[str, Any]] = {}
    for review in sorted(plan_rewrite_reviews, key=lambda item: (str(item.get("plan_rewrite_milestone", "")), str(item.get("reviewer_role", "")), hash_data(item))):
        milestone = review.get("plan_rewrite_milestone")
        role = review.get("reviewer_role")
        if isinstance(milestone, str) and isinstance(role, str):
            plan_reviews_by_milestone_role[(milestone, role)] = review

    workspace = workspace_data if isinstance(workspace_data, dict) else {}
    for task_id, task in by_task_id.items():
        definition = definition_by_id[task_id]
        task["evidence_status"] = "full-projection"
        task["runtime_projection"] = "projected"
        task["workspace_state"] = workspace.get("workspace_state", "projected")
        for key in ["base_commit", "dependency_contract_sha256", "implementation_dependency_lock_sha256", "dependency_lock_sha256", "toolchain_manifest_sha256"]:
            if workspace.get(key) and not task.get(key):
                task[key] = workspace[key]

        event = latest_events.get(task_id)
        if event:
            event_status = status_from_event(event)
            if event_status:
                task["status"] = event_status
            task["last_runtime_event"] = redact_private(event)

        result = results_by_task.get(task_id)
        gate = gates_by_task.get(task_id)
        expected_context = {**definition, **task}
        result_ok, result_reasons = valid_task_result(expected_context, workspace, result)
        gate_ok, gate_reasons = valid_gate(expected_context, workspace, gate, result)

        task_pack_reasons = task_pack_completion_reasons(task)
        stale_reasons = result_reasons + gate_reasons + task_pack_reasons
        if definition.get("task_kind") in IMPLEMENTATION_TASK_KINDS:
            if result_ok and gate_ok and not task_pack_reasons:
                task["status"] = "completed"
                task["implementation_evidence"] = "codex-b-gate-accepted"
            else:
                task["implementation_evidence"] = "incomplete"
                if result or gate:
                    task["status"] = "stale-completion" if any("changed" in reason for reason in stale_reasons) else task["status"]
        task["stale_reasons"] = sorted(set(stale_reasons))

    required_by_epic: dict[str, list[dict[str, Any]]] = {}
    for task in projected:
        if task.get("task_kind") in IMPLEMENTATION_TASK_KINDS and task.get("required_for_epic"):
            required_by_epic.setdefault(str(task.get("epic_id")), []).append(task)

    for task_id, task in by_task_id.items():
        definition = definition_by_id[task_id]
        epic_id = str(definition.get("epic_id")) if definition.get("epic_id") else None
        review = reviews_by_epic.get(epic_id) if epic_id else None
        review_ok, review_reasons = valid_epic_review({**definition, **task}, workspace, review)
        required_tasks = required_by_epic.get(epic_id or "", [])
        incomplete_required = [item["task_id"] for item in required_tasks if item.get("status") != "completed"]
        stale_required = [item["task_id"] for item in required_tasks if item.get("status") == "stale-completion" or item.get("stale_reasons")]
        integration_reasons = epic_review_integration_reasons(review, workspace, required_tasks, gates_by_task)
        if task.get("task_kind") in ACCEPTANCE_TASK_KINDS or epic_id:
            reasons = list(task.get("stale_reasons", []))
            if (
                review_ok
                and not integration_reasons
                and required_tasks
                and not incomplete_required
                and not stale_required
                and task.get("epic_contract_status") == "approved"
            ):
                task["acceptance_evidence"] = "codex-a-epic-review-accepted"
            else:
                task["acceptance_evidence"] = "not-passed"
                reasons.extend(review_reasons)
                reasons.extend(integration_reasons)
                if review_ok and (not required_tasks or incomplete_required):
                    reasons.append("epic-review-before-required-tasks-complete")
                if task.get("epic_contract_status") != "approved":
                    reasons.append("epic-contract-not-approved")
                for required_id in stale_required:
                    reasons.append(f"required-task-stale:{required_id}")
            task["stale_reasons"] = sorted(set(reasons))

    for task in projected:
        milestone = task.get("plan_rewrite_milestone")
        if not isinstance(milestone, str):
            continue
        plan_gate = plan_reviews_by_milestone_role.get((milestone, "Plan Gate"))
        codex_review = plan_reviews_by_milestone_role.get((milestone, "Codex A"))
        gate_ok, gate_reasons = valid_plan_rewrite_review(plan_gate, "Plan Gate")
        review_ok, review_reasons = valid_plan_rewrite_review(codex_review, "Codex A")
        same_reviewed_commit = (
            bool(plan_gate)
            and bool(codex_review)
            and plan_gate.get("plan_commit_sha") == codex_review.get("plan_commit_sha")
        )
        commit_pair_reasons = [] if same_reviewed_commit or not (gate_ok and review_ok) else ["plan-review-target-commit-mismatch"]
        if commit_pair_reasons:
            gate_ok = False
            review_ok = False
        task["plan_gate_evidence"] = "accepted" if gate_ok else ("stale" if plan_gate else "not-run")
        task["plan_review_evidence"] = "accepted" if review_ok else ("stale" if codex_review else "not-run")
        reasons = list(task.get("stale_reasons", []))
        if plan_gate:
            reasons.extend(gate_reasons)
        if codex_review:
            reasons.extend(review_reasons)
        reasons.extend(commit_pair_reasons)
        if (
            gate_ok
            and review_ok
            and task.get("task_kind") in {"plan-contract", "contract-readiness", "harness"}
        ):
            task["status"] = "completed"
        task["stale_reasons"] = sorted(set(reasons))


def build_graph(projected: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        {
            "id": task["id"],
            "status": task["status"],
            "plan_rewrite_milestone": task.get("plan_rewrite_milestone"),
            "product_milestone": task.get("product_milestone"),
            "epic_id": task.get("epic_id"),
        }
        for task in projected
    ]
    edges = [
        {"from": dep, "to": task["id"], "kind": "task"}
        for task in projected
        for dep in task.get("task_dependencies", [])
    ]
    return {
        "metadata": metadata,
        "nodes": sorted(nodes, key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: (item["from"], item["to"])),
    }


def counts(projected: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for task in projected:
        status = str(task.get("status"))
        result[status] = result.get(status, 0) + 1
    return dict(sorted(result.items()))


def aggregate_milestones(projected: list[dict[str, Any]]) -> dict[str, Any]:
    milestones: dict[str, dict[str, Any]] = {}
    for key in ["plan_rewrite_milestone", "product_milestone"]:
        for task in projected:
            milestone = task.get(key)
            if not milestone:
                continue
            entry = milestones.setdefault(
                milestone,
                {
                    "contract_status": "draft",
                    "contract_readiness_status": "not-started",
                    "plan_acceptance_status": "not-run",
                    "implementation_status": "not-started",
                    "acceptance_status": "not-run",
                    "status_source": "generated from task definitions and runtime projection",
                    "required_task_ids": [],
                },
            )
            if task.get("epic_contract_status") == "approved":
                entry["contract_status"] = "approved"
                entry["contract_readiness_status"] = "approved"
            elif task.get("epic_contract_status") == "draft" and entry["contract_status"] != "approved":
                entry["contract_status"] = "draft"
            if task.get("task_kind") in {"plan-contract", "contract-readiness", "harness"}:
                if task.get("status") == "completed" and entry["contract_readiness_status"] not in {"approved", "stale", "blocked"}:
                    entry["contract_readiness_status"] = "ready-for-approval"
                elif task.get("status") in {"claimed", "in-progress"} and entry["contract_readiness_status"] == "not-started":
                    entry["contract_readiness_status"] = "in-progress"
                elif task.get("status") == "blocked":
                    entry["contract_readiness_status"] = "blocked"

    for milestone, entry in milestones.items():
        milestone_tasks = [
            task for task in projected if task.get("plan_rewrite_milestone") == milestone or task.get("product_milestone") == milestone
        ]
        required_impl = [
            task
            for task in milestone_tasks
            if task.get("task_kind") in IMPLEMENTATION_TASK_KINDS and task.get("required_for_epic", True)
        ]
        entry["required_task_ids"] = sorted(str(task["task_id"]) for task in required_impl)
        if required_impl:
            statuses = [str(task.get("status")) for task in required_impl]
            if any(status == "stale-completion" for status in statuses) or any(task.get("stale_reasons") for task in required_impl):
                entry["implementation_status"] = "stale"
            elif all(status == "completed" for status in statuses):
                entry["implementation_status"] = "completed"
            elif any(status in {"completed", "claimed", "in-progress"} for status in statuses):
                entry["implementation_status"] = "in-progress"
            elif all(status == "blocked" for status in statuses):
                entry["implementation_status"] = "blocked"
            elif any(status == "blocked" for status in statuses):
                entry["implementation_status"] = "blocked"
            else:
                entry["implementation_status"] = "not-started"

        acceptance_tasks = [task for task in milestone_tasks if task.get("task_kind") in ACCEPTANCE_TASK_KINDS]
        accepted_evidence = any(task.get("acceptance_evidence") == "codex-a-epic-review-accepted" for task in milestone_tasks)
        review_before_complete = any("epic-review-before-required-tasks-complete" in task.get("stale_reasons", []) for task in milestone_tasks)
        if milestone.startswith("PR-"):
            plan_gate = any(task.get("plan_gate_evidence") == "accepted" for task in milestone_tasks)
            plan_review = any(task.get("plan_review_evidence") == "accepted" for task in milestone_tasks)
            stale_plan_evidence = any(task.get("plan_gate_evidence") == "stale" or task.get("plan_review_evidence") == "stale" for task in milestone_tasks)
            if plan_gate and plan_review:
                entry["plan_acceptance_status"] = "accepted"
            elif stale_plan_evidence:
                entry["plan_acceptance_status"] = "stale"
            elif any(task.get("status") in {"claimed", "in-progress"} for task in milestone_tasks):
                entry["plan_acceptance_status"] = "in-progress"
            elif any(task.get("status") == "blocked" for task in milestone_tasks):
                entry["plan_acceptance_status"] = "blocked"
            else:
                entry["plan_acceptance_status"] = "not-run"
        if accepted_evidence and entry.get("implementation_status") == "completed" and entry.get("contract_status") == "approved":
            entry["acceptance_status"] = "passed"
        elif review_before_complete:
            entry["acceptance_status"] = "stale"
        elif any(task.get("status") == "blocked" for task in acceptance_tasks):
            entry["acceptance_status"] = "blocked"
        elif any(task.get("status") in {"claimed", "in-progress"} for task in acceptance_tasks):
            entry["acceptance_status"] = "in-progress"
    return dict(sorted(milestones.items()))


def projection_inputs_hash(definition_hash: str, runtime_data: Any | None, completion_data: Any | None, workspace_data: Any | None) -> str:
    return hash_data(
        {
            "task_definitions": definition_hash,
            "runtime_data": normalize_projection_inputs(runtime_data),
            "completion_data": normalize_projection_inputs(completion_data),
            "workspace_data": normalize_for_hash(workspace_data),
        }
    )


def build_snapshots(
    *,
    definitions_only: bool = False,
    runtime_events: Path | None = None,
    completion_records: Path | None = None,
    workspace_report: Path | None = None,
) -> dict[str, Any]:
    definitions, definition_hash = load_task_definitions()
    runtime_data = read_json_or_yaml_file(runtime_events) if runtime_events else None
    completion_data = read_json_or_yaml_file(completion_records) if completion_records else None
    workspace_data = read_json_or_yaml_file(workspace_report) if workspace_report else None
    full_projection = not definitions_only and any([runtime_events, completion_records, workspace_report])
    if full_projection and not all([runtime_events, completion_records, workspace_report]):
        raise ProjectionError("full projection requires --runtime-events, --completion-records, and --workspace-report")
    metadata = {
        "schema_version": 1,
        "generator": "harness/generate_snapshots.py",
        "generator_version": 3,
        "generated_at": deterministic_generated_at(
            [item for item in [runtime_data, completion_data, workspace_data] if item is not None],
            definitions_only=not full_projection,
        ),
        "source_hash": projection_inputs_hash(definition_hash, runtime_data if full_projection else None, completion_data if full_projection else None, workspace_data if full_projection else None),
        "task_definition_hash": definition_hash,
        "projection_mode": "full" if full_projection else "definitions-only",
    }
    projected = [definition_projection(task) for task in definitions]
    if full_projection:
        apply_full_projection(projected, definitions, runtime_data, completion_data, workspace_data)
    projected = redact_private(projected)
    projected.sort(key=lambda item: item["id"])
    return {
        "tasks.json": {"metadata": metadata, "tasks": projected},
        "task-graph.json": build_graph(projected, metadata),
        "public-state-summary.json": {
            "metadata": metadata,
            "counts": {"tasks": len(projected), "status_counts": counts(projected)},
            "milestones": aggregate_milestones(projected),
        },
        "task-runtime-summary.json": {
            "metadata": metadata,
            "runtime_projection": "projected" if full_projection else "none",
            "status_counts": counts(projected),
            "private_inputs": {
                "runtime_events": "provided" if runtime_events else "not-provided",
                "completion_records": "provided" if completion_records else "not-provided",
                "workspace_report": "provided" if workspace_report else "not-provided",
            },
            "note": "private runtime projection: projected from sanitized inputs" if full_projection else "private runtime projection: not run",
        },
    }


def write_snapshots(snapshots: dict[str, Any], output: Path) -> dict[str, Path]:
    output.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name in SNAPSHOT_NAMES:
        path = output / name
        path.write_bytes(canonical_bytes(snapshots[name]))
        written[name] = path
    return written
