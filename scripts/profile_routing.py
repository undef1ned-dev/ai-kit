#!/usr/bin/env python3
"""
Reusable profile routing helpers for workflow/profile matching.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RoutingResult:
    profile: str
    score: int
    confidence: str
    intent: str
    intent_reason: str
    mode: str | None
    workflow_recipe: str
    workflow_execution_mode: str
    workflow_chain: list[str]
    workflow_graph_summary: str
    path_hits: list[str]
    keyword_hits: list[str]
    default_chain: list[str]
    matched_globs: list[str]
    suggested_skills: list[str]
    profile_skills: list[str]
    next_action: str
    next_action_reason: str
    decision_summary: str
    ambiguity_level: str
    ambiguity_reason: str
    fallback_profile: str | None
    fallback_mode: str | None
    fallback_reason: str
    starter_prompt: str


def load_workflow_policy(root: Path | None = None) -> dict[str, Any]:
    base_root = root or ROOT
    return json.loads((base_root / "policies" / "workflow-policy.json").read_text(encoding="utf-8"))


def confidence_from_signals(path_hits: list[str], matched_mode: str | None, keyword_hits: list[str]) -> str:
    confidence = "low"
    if path_hits or matched_mode:
        confidence = "high" if len(path_hits) >= 1 else "medium"
    elif keyword_hits:
        confidence = "medium"
    return confidence


def load_profile_data(root: Path | None = None) -> list[dict[str, Any]]:
    base_root = root or ROOT
    profiles = []
    for directory in sorted((base_root / "profiles").iterdir()):
        if not directory.is_dir():
            continue
        manifest_path = directory / "profile.manifest.json"
        capability_path = directory / "capabilities.json"
        workflow_path = directory / "workflow.manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        capabilities = json.loads(capability_path.read_text(encoding="utf-8")) if capability_path.exists() else {"modes": []}
        workflow = json.loads(workflow_path.read_text(encoding="utf-8")) if workflow_path.exists() else {"recipes": []}
        profiles.append({"manifest": manifest, "capabilities": capabilities.get("modes", []), "workflow": workflow})
    return profiles


def extract_paths(task: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_\-\[\]\.]+(?:/[A-Za-z0-9_\-\[\]\.]+)+", task)


def glob_specificity(glob: str) -> int:
    return len(glob.replace("**/", "").replace("*", ""))


def detect_task_intent(task: str, paths: list[str], mode: str | None, policy: dict[str, Any]) -> tuple[str, str]:
    lowered = task.lower()
    for rule in policy.get("intent_rules", []):
        markers = [marker.lower() for marker in rule.get("markers_any", [])]
        modes_any = [item.lower() for item in rule.get("modes_any", [])]
        exclude_markers = [marker.lower() for marker in rule.get("exclude_markers_any", [])]
        patch_markers = [marker.lower() for marker in rule.get("patch_markers_any", [])]
        max_paths = rule.get("max_paths")
        requires_mode_or_paths = bool(rule.get("requires_mode_or_paths", False))

        if modes_any and (not mode or mode.lower() not in modes_any):
            continue
        if markers and not any(marker in lowered for marker in markers):
            continue
        if exclude_markers and any(marker in lowered for marker in exclude_markers):
            continue
        if patch_markers and not any(marker in lowered for marker in patch_markers):
            continue
        if max_paths is not None and len(paths) > int(max_paths):
            continue
        if requires_mode_or_paths and not (mode or paths):
            continue
        return (str(rule["intent"]), str(rule["reason"]))

    return ("feature-work", "The task is broad or ambiguous enough that the general feature flow is the safest default.")


def pick_next_action(
    task: str,
    intent: str,
    mode: str | None,
    suggested_skills: list[str],
    profile_skills: list[str],
    policy: dict[str, Any],
) -> tuple[str, str]:
    lowered = task.lower()
    available = list(dict.fromkeys([*suggested_skills, *profile_skills]))
    if not available:
        return ("inspect-chain", "No skill recommendations available, so the safest next step is to inspect the default chain.")

    for rule in policy.get("next_action_rules", []):
        markers = [marker.lower() for marker in rule.get("markers_any", [])]
        required_skill = str(rule.get("required_skill", ""))
        if markers and any(marker in lowered for marker in markers) and required_skill in available:
            return (str(rule["action"]), str(rule["reason"]))

    default_actions = policy.get("default_actions", {})
    default = default_actions.get(intent, default_actions.get("fallback", {}))

    if intent == "review-only":
        return (str(default.get("action", "inspect-chain")), str(default["reason"]))

    preferred_skill = str(default.get("preferred_skill", ""))
    if preferred_skill and preferred_skill in available:
        return (f"/{preferred_skill}", str(default["reason"]))

    new_skill_prefix = str(default.get("prefer_new_skill_prefix", ""))
    if new_skill_prefix:
        for skill in available:
            if skill.startswith(new_skill_prefix):
                return (
                    f"/{skill}",
                    str(default["reason"]).replace("matched mode", mode or "general mode"),
                )

    fallback = default_actions.get("fallback", {})
    fallback_skill = str(fallback.get("preferred_skill", ""))
    if fallback_skill and fallback_skill in available:
        return (f"/{fallback_skill}", str(fallback["reason"]))

    return (f"/{available[0]}", "This is the most relevant recommended skill available for the matched profile and mode.")


def summarize_workflow_graph(recipe: dict[str, Any]) -> str:
    steps = recipe.get("steps", [])
    if not isinstance(steps, list) or not steps:
        return ""
    parts: list[str] = []
    for step in steps:
        step_id = str(step.get("id", ""))
        depends_on = step.get("depends_on", [])
        if depends_on:
            parts.append(f"{step_id}<-{','.join(str(item) for item in depends_on)}")
        else:
            parts.append(step_id)
    return " | ".join(parts)


def select_workflow_recipe(
    profile: dict[str, Any],
    intent: str,
    next_action: str | None = None,
) -> tuple[str, str, list[str], str]:
    workflow = profile.get("workflow", {})
    recipes = workflow.get("recipes", [])
    default_recipe = str(workflow.get("default_recipe", ""))
    preferred_recipe = ""
    if next_action and next_action.startswith("/"):
        command_token = next_action.split()[0]
        preferred_recipe = command_token.removeprefix("/")
    if preferred_recipe:
        for recipe in recipes:
            if str(recipe.get("name", "")) == preferred_recipe and intent in recipe.get("intents", []):
                return (
                    str(recipe["name"]),
                    str(recipe.get("execution_mode", "")),
                    [str(step["agent"]) for step in recipe.get("steps", [])],
                    summarize_workflow_graph(recipe),
                )
    for recipe in recipes:
        if intent in recipe.get("intents", []):
            return (
                str(recipe["name"]),
                str(recipe.get("execution_mode", "")),
                [str(step["agent"]) for step in recipe.get("steps", [])],
                summarize_workflow_graph(recipe),
            )
    for recipe in recipes:
        if str(recipe.get("name", "")) == default_recipe:
            return (
                default_recipe,
                str(recipe.get("execution_mode", "")),
                [str(step["agent"]) for step in recipe.get("steps", [])],
                summarize_workflow_graph(recipe),
            )
    return ("", "", [], "")


def build_decision_summary(result: RoutingResult) -> str:
    signals: list[str] = []
    if result.path_hits:
        signals.append(f"path signals {result.path_hits}")
    if result.mode:
        signals.append(f"mode '{result.mode}'")
    if result.keyword_hits:
        signals.append(f"keywords {result.keyword_hits}")

    if not signals:
        signals.append("fallback profile heuristics")

    summary = (
        f"Matched profile '{result.profile}' via {', '.join(signals)}. "
        f"Intent '{result.intent}' maps to recipe '{result.workflow_recipe or 'default'}'"
    )
    if result.workflow_chain:
        summary += f" ({result.workflow_execution_mode or 'unknown'} mode) and chain {result.workflow_chain}"
    summary += f". Start with {result.next_action}."
    return summary


def build_starter_prompt(task: str, result: RoutingResult) -> str:
    if result.next_action.startswith("/"):
        return f"{result.next_action} {task}"
    if result.workflow_chain:
        lead_agent = result.workflow_chain[0]
        return (
            f"Inspect recipe '{result.workflow_recipe}' for profile '{result.profile}' "
            f"and start from '{lead_agent}' for task: {task}"
        )
    return f"Inspect routing for profile '{result.profile}' and continue with task: {task}"


def describe_fallback_reason(winner: RoutingResult, runner_up: RoutingResult) -> str:
    if runner_up.score <= 0:
        return "No meaningful runner-up signals were found, so the current match is the only practical candidate."
    if winner.path_hits and not runner_up.path_hits:
        return (
            f"Runner-up '{runner_up.profile}' lost because it has no direct path hits, "
            f"while '{winner.profile}' has stronger path-based evidence."
        )
    if winner.mode and not runner_up.mode:
        return (
            f"Runner-up '{runner_up.profile}' lost because it did not resolve a concrete capability mode, "
            f"while '{winner.profile}' matched mode '{winner.mode}'."
        )
    if winner.score > runner_up.score:
        return (
            f"Runner-up '{runner_up.profile}' remains plausible, but its score {runner_up.score} "
            f"is behind the winning score {winner.score}."
        )
    return f"Runner-up '{runner_up.profile}' stays close enough that a human should sanity-check the match."


def annotate_ranked_results(task: str, results: list[RoutingResult]) -> list[RoutingResult]:
    if not results:
        return results

    for index, result in enumerate(results):
        runner_up = results[index + 1] if index + 1 < len(results) else None
        score_gap = result.score - runner_up.score if runner_up else result.score

        ambiguity_level = "low"
        ambiguity_reason = "The routing signals are specific enough that this match should be stable."
        if result.confidence == "low":
            ambiguity_level = "high"
            ambiguity_reason = "The match relies on weak signals, so a human sanity-check is strongly recommended."
        elif runner_up and runner_up.score > 0 and score_gap <= 3:
            ambiguity_level = "high"
            ambiguity_reason = (
                f"The runner-up '{runner_up.profile}' is very close in score ({result.score} vs {runner_up.score}), "
                "so this is an ambiguous routing decision."
            )
        elif runner_up and runner_up.score > 0 and (score_gap <= 8 or result.confidence == "medium"):
            ambiguity_level = "medium"
            ambiguity_reason = (
                f"There is a plausible runner-up '{runner_up.profile}', so the match is usable but worth a quick sanity-check."
            )

        result.ambiguity_level = ambiguity_level
        result.ambiguity_reason = ambiguity_reason
        result.fallback_profile = runner_up.profile if runner_up and runner_up.score > 0 else None
        result.fallback_mode = runner_up.mode if runner_up and runner_up.score > 0 else None
        result.fallback_reason = describe_fallback_reason(result, runner_up) if runner_up else (
            "No runner-up candidate was available."
        )
        result.decision_summary = build_decision_summary(result)
        result.starter_prompt = build_starter_prompt(task, result)

    return results


def score_task_candidates(
    task: str,
    profiles: list[dict[str, Any]],
    intent: str | None = None,
) -> list[RoutingResult]:
    lowered = task.lower()
    paths = extract_paths(task)
    policy = load_workflow_policy()
    results: list[RoutingResult] = []
    explicit_intent = (intent or "").strip()

    for profile in profiles:
        manifest = profile["manifest"]
        profile_skills = [str(skill) for skill in manifest.get("recommended_skills", [])]
        path_hits = [
            signal
            for signal in manifest.get("path_signals", [])
            if signal.lower() in lowered or any(signal.lower() in path.lower() for path in paths)
        ]
        keyword_hits = [word for word in manifest.get("keywords", []) if word.lower() in lowered]

        matched_mode = None
        matched_globs: list[str] = []
        suggested_skills: list[str] = []
        matched_mode_rank = (-1, -1)
        for mode in profile["capabilities"]:
            mode_globs = mode.get("file_globs", [])
            mode_hits = [glob for glob in mode_globs if any(PurePosixPath(path).match(glob) for path in paths)]
            if not mode_hits:
                mode_hits = [glob for glob in mode_globs if glob.lower().replace("**/", "") in lowered]

            mode_signal_match = False
            if not mode_hits and path_hits:
                normalized_signals = {signal.lower().strip("/") for signal in path_hits}
                mode_prefixes = {
                    glob.lower().split("/", 1)[0]
                    for glob in mode_globs
                    if "/" in glob
                }
                mode_signal_match = any(prefix in normalized_signals for prefix in mode_prefixes)

            current_score = 0
            if mode_hits:
                current_score += 10
            elif mode_signal_match:
                current_score += 5
            current_score += max((glob_specificity(glob) for glob in mode_hits or mode_globs), default=0)
            current_rank = (2 if mode_hits else 1 if mode_signal_match else 0, current_score)

            if current_rank > matched_mode_rank and (mode_hits or mode_signal_match):
                matched_mode = mode["name"]
                matched_globs = mode_hits or mode_globs
                suggested_skills = [str(skill) for skill in mode.get("suggested_skills", [])]
                matched_mode_rank = current_rank

        score = len(path_hits) * 10 + len(keyword_hits) * 3 + (5 if matched_mode else 0)
        if explicit_intent:
            task_intent = explicit_intent
            intent_reason = (
                "Explicit intent override selected by the operator; routing, workflow recipe, "
                "agent chain, validators and context pack must be replanned together."
            )
        else:
            task_intent, intent_reason = detect_task_intent(task, paths, matched_mode, policy)
        next_action, next_action_reason = pick_next_action(
            task,
            task_intent,
            matched_mode,
            suggested_skills,
            profile_skills,
            policy,
        )
        workflow_recipe, workflow_execution_mode, workflow_chain, workflow_graph_summary = select_workflow_recipe(
            profile,
            task_intent,
            next_action,
        )
        results.append(
            RoutingResult(
                profile=manifest["profile"],
                score=score,
                confidence=confidence_from_signals(path_hits, matched_mode, keyword_hits),
                intent=task_intent,
                intent_reason=intent_reason,
                mode=matched_mode,
                workflow_recipe=workflow_recipe,
                workflow_execution_mode=workflow_execution_mode,
                workflow_chain=workflow_chain,
                workflow_graph_summary=workflow_graph_summary,
                path_hits=path_hits,
                keyword_hits=keyword_hits,
                default_chain=manifest.get("default_chain", []),
                matched_globs=matched_globs,
                suggested_skills=suggested_skills,
                profile_skills=profile_skills,
                next_action=next_action,
                next_action_reason=next_action_reason,
                decision_summary="",
                ambiguity_level="low",
                ambiguity_reason="",
                fallback_profile=None,
                fallback_mode=None,
                fallback_reason="",
                starter_prompt="",
            )
        )

    results.sort(key=lambda item: (-item.score, item.profile))
    return annotate_ranked_results(task, results)


def score_task(task: str, profiles: list[dict[str, Any]]) -> RoutingResult:
    return score_task_candidates(task, profiles)[0]
