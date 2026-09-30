from __future__ import annotations

import random
from statistics import mean, stdev
from time import perf_counter_ns

from app.learning import (
    build_learning_path,
    detect_anomalies,
    detect_misconception_id,
    weighted_mastery_update,
)

SEED = 9012026
SEEDS_PER_PROFILE = 30
STUDENT_PROFILES = (
    "fast learner",
    "slow learner",
    "random guesser",
    "overconfident",
    "erratic",
)
STRATEGIES = ("adaptive", "static")


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))], 3)


def _interval(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "ci95": [None, None], "n": 0}
    avg = mean(values)
    margin = 1.96 * stdev(values) / (len(values) ** 0.5) if len(values) > 1 else 0.0
    return {
        "mean": round(avg, 4),
        "ci95": [round(avg - margin, 4), round(avg + margin, 4)],
        "n": len(values),
    }


def _ece(confidences: list[float], outcomes: list[int]) -> float:
    if not outcomes:
        return 0.0
    error = 0.0
    for lower in (0, 0.2, 0.4, 0.6, 0.8):
        indexes = [
            i for i, value in enumerate(confidences) if lower <= value < lower + 0.2 or (lower == 0.8 and value == 1)
        ]
        if indexes:
            error += (
                len(indexes)
                / len(outcomes)
                * abs(mean(confidences[i] for i in indexes) - mean(outcomes[i] for i in indexes))
            )
    return error


def _concepts() -> list[dict]:
    names = [
        "variables",
        "types",
        "operators",
        "strings",
        "input",
        "conditions",
        "booleans",
        "lists",
        "indexing",
        "loops",
    ]
    return [
        {
            "slug": name,
            "title": name.title(),
            "prerequisites": [names[i - 1]] if i else [],
        }
        for i, name in enumerate(names)
    ]


def _profile_parameters(profile: str) -> tuple[float, float, float]:
    """Return baseline response skill, practice learning rate, repair efficacy."""
    return {
        "fast learner": (0.55, 0.105, 0.75),
        "slow learner": (0.50, 0.045, 0.58),
        "random guesser": (0.25, 0.012, 0.30),
        "overconfident": (0.48, 0.040, 0.45),
        "erratic": (0.50, 0.035, 0.42),
    }[profile]


def _held_out_score(rng: random.Random, latent: dict[str, float], base_skill: float) -> float:
    """Fixed, unseen item set: two independent items per concept, difficulty .5."""
    outcomes = []
    for value in latent.values():
        probability = min(0.98, max(0.02, base_skill + 0.55 * (value - 0.25)))
        outcomes.extend(rng.random() < probability for _ in range(2))
    return sum(outcomes) / len(outcomes)


def _run_one(profile: str, strategy: str, seed: int, budget: int) -> dict:
    rng = random.Random(seed)
    concepts = _concepts()
    base_skill, learning_rate, repair_efficacy = _profile_parameters(profile)
    latent = {item["slug"]: 0.25 for item in concepts}
    mastery = dict(latent)  # production BKT state used by the path optimizer
    initial_beliefs = {item["slug"] for index, item in enumerate(concepts) if index % 3 == 1}
    active_beliefs = set(initial_beliefs)
    resolved: set[str] = set()
    last_review_step: dict[str, int] = {}
    start_test_rng = random.Random(seed ^ 0x115EA)
    pretest = _held_out_score(start_test_rng, latent, base_skill)
    heldout_seed = seed ^ 0x115EA
    history: list[dict] = []
    confidence_values: list[float] = []
    outcomes: list[int] = []
    flagged_truth: list[bool] = []
    flagged_pred: list[bool] = []
    path_latency_ms: list[float] = []
    time_to_mastery = None
    questions_to_80 = None

    for step in range(budget):
        if strategy == "adaptive":
            started = perf_counter_ns()
            path = build_learning_path(
                concepts,
                mastery,
                [
                    {
                        "concept_slug": slug,
                        "title": slug,
                        "evidence": "Repeated misconception-tagged distractor",
                    }
                    for slug in sorted(active_beliefs)
                ],
                {slug: step - last_seen for slug, last_seen in last_review_step.items()},
            )
            path_latency_ms.append((perf_counter_ns() - started) / 1_000_000)
            chosen = path[0]["conceptId"] if path else concepts[0]["slug"]
            is_repair = bool(path and path[0].get("kind") == "repair")
        else:
            chosen = concepts[step % len(concepts)]["slug"]
            is_repair = False

        if is_repair and chosen in active_beliefs:
            # A targeted worked example consumes one interaction and can resolve
            # the independently represented belief; it does not directly award mastery.
            resolved_now = rng.random() < repair_efficacy
            if resolved_now:
                active_beliefs.remove(chosen)
                resolved.add(chosen)
                latent[chosen] = min(1.0, latent[chosen] + learning_rate * 0.7)
            last_review_step[chosen] = step
            correct = resolved_now
            confidence = 4 if profile == "overconfident" else 3
            seconds = 8.0
            selected = 1 if not resolved_now else 0
            key = chosen if not resolved_now else None
        else:
            prior_belief = chosen in active_beliefs
            probability = base_skill + 0.55 * (latent[chosen] - 0.25)
            if prior_belief:
                probability *= 0.48
            if profile == "erratic":
                probability = rng.choice([max(0.05, probability - 0.3), min(0.9, probability + 0.3)])
            probability = min(0.98, max(0.02, probability))
            correct = rng.random() < probability
            seconds = rng.uniform(0.5, 1.8) if profile == "random guesser" else rng.uniform(3, 12)
            confidence = (
                rng.choice([1, 2])
                if profile == "random guesser"
                else 5
                if profile == "overconfident"
                else rng.choice([2, 5])
                if profile == "erratic"
                else 4
                if correct
                else 2
            )
            # The authored wrong option reveals a misconception only for concepts
            # that the synthetic learner actually holds.
            selected = 0 if correct else (1 if prior_belief else 2)
            tags = ["", f"misunderstands_{chosen}" if prior_belief else "", ""]
            key = detect_misconception_id({"misconception_ids": tags}, selected)
            if key:
                active_beliefs.add(chosen)
            recent = history[-4:]
            reasons = detect_anomalies(int(seconds * 1000), correct, str(selected), confidence, recent)
            mastery[chosen] = weighted_mastery_update(mastery[chosen], correct, reasons)
            # Independent student acquisition model; the optimizer cannot alter it.
            if correct:
                latent[chosen] = min(1.0, latent[chosen] + learning_rate * (1 - latent[chosen]))
                # Correctly applying the idea with feedback can also weaken an
                # existing misconception, but less often than a targeted repair.
                if prior_belief and rng.random() < 0.12:
                    active_beliefs.discard(chosen)
                    resolved.add(chosen)
            elif not reasons:
                latent[chosen] = max(0.0, latent[chosen] - 0.012)
            last_review_step[chosen] = step
            history.append({"answer": str(selected), "correct": correct, "confidence": confidence})
            flagged_pred.append(bool(reasons))
            flagged_truth.append(profile == "random guesser")

        confidence_values.append(confidence / 5)
        outcomes.append(int(correct))
        if questions_to_80 is None and sum(v >= 0.8 for v in latent.values()) / len(latent) >= 0.8:
            questions_to_80 = step + 1
        if time_to_mastery is None and all(v >= 0.8 for v in latent.values()):
            time_to_mastery = step + 1

    posttest_rng = random.Random(heldout_seed)
    posttest = _held_out_score(posttest_rng, latent, base_skill)
    tp = sum(t and p for t, p in zip(flagged_truth, flagged_pred))
    fp = sum((not t) and p for t, p in zip(flagged_truth, flagged_pred))
    fn = sum(t and not p for t, p in zip(flagged_truth, flagged_pred))
    return {
        "learning_gain": posttest - pretest,
        "pretest": pretest,
        "posttest": posttest,
        "time_to_mastery_questions": time_to_mastery,
        "questions_to_80_mastery": questions_to_80,
        "misconception_resolution_rate": len(resolved) / max(1, len(initial_beliefs)),
        "guess_detection_precision": tp / max(1, tp + fp),
        "guess_detection_recall": tp / max(1, tp + fn),
        "calibration_error": _ece(confidence_values, outcomes),
        "path_latency_p50_ms": _percentile(path_latency_ms, 0.5),
        "path_latency_p95_ms": _percentile(path_latency_ms, 0.95),
    }


def simulate(
    seed: int = SEED,
    questions_per_run: int = 120,
    seeds_per_profile: int = SEEDS_PER_PROFILE,
) -> dict:
    """Compare equal-budget sequencing over independent paired synthetic cohorts."""
    results = []
    raw = {}
    metric_names = (
        "learning_gain",
        "time_to_mastery_questions",
        "questions_to_80_mastery",
        "misconception_resolution_rate",
        "guess_detection_precision",
        "guess_detection_recall",
        "calibration_error",
    )
    for profile_index, profile in enumerate(STUDENT_PROFILES):
        for strategy in STRATEGIES:
            runs = [
                _run_one(
                    profile,
                    strategy,
                    seed + i * 7919 + profile_index * 100_003,
                    questions_per_run,
                )
                for i in range(seeds_per_profile)
            ]
            raw[(profile, strategy)] = runs
            row = {"profile": profile, "strategy": strategy, "seeds": seeds_per_profile}
            for metric in metric_names:
                values = [run[metric] for run in runs if run[metric] is not None]
                row[metric] = _interval(values)
            lat50 = [run["path_latency_p50_ms"] for run in runs if run["path_latency_p50_ms"] is not None]
            lat95 = [run["path_latency_p95_ms"] for run in runs if run["path_latency_p95_ms"] is not None]
            row["path_update_latency_p50_ms"] = round(mean(lat50), 3) if lat50 else None
            row["path_update_latency_p95_ms"] = round(mean(lat95), 3) if lat95 else None
            results.append(row)
    comparisons = []
    for profile in STUDENT_PROFILES:
        for metric in metric_names:
            differences = []
            for seed_index in range(seeds_per_profile):
                adaptive = raw[(profile, "adaptive")][seed_index][metric]
                static = raw[(profile, "static")][seed_index][metric]
                if adaptive is not None and static is not None:
                    differences.append(adaptive - static)
            comparisons.append(
                {
                    "profile": profile,
                    "metric": metric,
                    "adaptive_minus_static": _interval(differences),
                }
            )
    return {
        "seed": seed,
        "seedsPerProfile": seeds_per_profile,
        "questionsPerRun": questions_per_run,
        "results": results,
        "pairedComparisons": comparisons,
    }
