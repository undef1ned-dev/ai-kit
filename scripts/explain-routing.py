#!/usr/bin/env python3
"""
Explain profile routing for a free-form task description.

Usage:
    python scripts/explain-routing.py "Измени stores/auth.ts и добавь optimistic update"
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from profile_routing import extract_paths, load_profile_data, score_task_candidates


def select_visible_candidates(results: list, top_n: int) -> list:
    meaningful = [candidate for candidate in results if candidate.score > 0]
    if not meaningful:
        meaningful = results[:1]
    return meaningful[:top_n]


def main() -> int:
    parser = argparse.ArgumentParser(description="Explain profile and capability routing")
    parser.add_argument("task", help="Task description to evaluate")
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="How many ranked candidates to show (default: 3)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report",
    )
    args = parser.parse_args()

    task = args.task.strip()
    if not task:
        print("Task must not be empty")
        return 1

    profiles = load_profile_data()
    results = score_task_candidates(task, profiles)
    result = results[0]
    top_n = max(1, args.top)
    visible_candidates = select_visible_candidates(results, top_n)

    if args.json:
        payload = {
            "task": task,
            "detected_paths": extract_paths(task),
            "selected": asdict(result),
            "candidates": [asdict(candidate) for candidate in visible_candidates],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("Routing explanation")
    print("===================")
    print(f"Task: {task}")
    print(f"Detected paths: {extract_paths(task) or '—'}")
    print(f"Matched profile: {result.profile}")
    print(f"Confidence: {result.confidence}")
    print(f"Task intent: {result.intent}")
    print(f"Matched mode: {result.mode or '—'}")
    print(f"Workflow recipe: {result.workflow_recipe or '—'}")
    print(f"Workflow execution mode: {result.workflow_execution_mode or '—'}")
    print(f"Workflow chain: {result.workflow_chain or '—'}")
    print(f"Workflow graph: {result.workflow_graph_summary or '—'}")
    print(f"Path hits: {result.path_hits or '—'}")
    print(f"Keyword hits: {result.keyword_hits or '—'}")
    print(f"Matched globs: {result.matched_globs or '—'}")
    print(f"Suggested skills: {result.suggested_skills or '—'}")
    print(f"Profile skills: {result.profile_skills or '—'}")
    print(f"Next action: {result.next_action}")
    print(f"Next action reason: {result.next_action_reason}")
    print(f"Intent reason: {result.intent_reason}")
    print(f"Default chain: {result.default_chain or '—'}")
    print(f"Decision summary: {result.decision_summary}")
    print(f"Ambiguity: {result.ambiguity_level}")
    print(f"Ambiguity reason: {result.ambiguity_reason}")
    print(f"Fallback candidate: {result.fallback_profile or '—'}")
    print(f"Fallback reason: {result.fallback_reason}")
    print(f"Starter prompt: {result.starter_prompt}")
    print(f"Score: {result.score}")

    if len(visible_candidates) > 1:
        print()
        print(f"Top {len(visible_candidates)} candidates")
        print("================")
        for index, candidate in enumerate(visible_candidates, start=1):
            print(f"{index}. {candidate.profile}")
            print(f"   score: {candidate.score}")
            print(f"   confidence: {candidate.confidence}")
            print(f"   intent: {candidate.intent}")
            print(f"   mode: {candidate.mode or '—'}")
            print(f"   workflow recipe: {candidate.workflow_recipe or '—'}")
            print(f"   workflow execution mode: {candidate.workflow_execution_mode or '—'}")
            print(f"   workflow chain: {candidate.workflow_chain or '—'}")
            print(f"   workflow graph: {candidate.workflow_graph_summary or '—'}")
            print(f"   path hits: {candidate.path_hits or '—'}")
            print(f"   keyword hits: {candidate.keyword_hits or '—'}")
            print(f"   matched globs: {candidate.matched_globs or '—'}")
            print(f"   suggested skills: {candidate.suggested_skills or '—'}")
            print(f"   next action: {candidate.next_action}")
            print(f"   ambiguity: {candidate.ambiguity_level}")
            print(f"   decision summary: {candidate.decision_summary}")
            print(f"   default chain: {candidate.default_chain or '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
