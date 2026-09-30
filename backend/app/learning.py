def bkt_update(
    prior: float,
    correct: bool,
    p_learn: float = 0.12,
    p_slip: float = 0.1,
    p_guess: float = 0.2,
) -> float:
    """Bayesian knowledge tracing posterior followed by the learning transition."""
    p = min(1.0, max(0.0, prior))
    likelihood_known = 1 - p_slip if correct else p_slip
    likelihood_unknown = p_guess if correct else 1 - p_guess
    denominator = p * likelihood_known + (1 - p) * likelihood_unknown
    posterior = p if denominator == 0 else p * likelihood_known / denominator
    return min(1.0, max(0.0, posterior + (1 - posterior) * p_learn))


def calibration_label(confidence: int, mastery: float) -> str:
    gap = confidence / 5 - mastery
    if gap > 0.2:
        return "overconfident"
    if gap < -0.2:
        return "underconfident"
    return "calibrated"


def detect_anomalies(time_taken_ms: int, correct: bool, answer: str, confidence: int, recent: list[dict]) -> list[str]:
    """Detect response patterns using the current response and recent owned-session data."""
    reasons: list[str] = []
    if time_taken_ms < 2000:
        reasons.append("under_2_seconds")
    if not correct and len(recent) >= 2 and all(not item["correct"] for item in recent[-2:]):
        reasons.append("fast_wrong_streak")
    if len(recent) >= 2 and all(item["answer"] == answer for item in recent[-2:]):
        reasons.append("same_option_pattern")
    sample = recent[-4:] + [{"answer": answer, "confidence": confidence}]
    low_confidence = sum(item.get("confidence", 3) <= 2 for item in sample)
    if len(sample) >= 4 and low_confidence >= 3 and len({item["answer"] for item in sample}) >= 3:
        reasons.append("random_guess_pattern")
    return reasons


def weighted_mastery_update(prior: float, correct: bool, anomaly_reasons: list[str]) -> float:
    """Suspicious responses have reduced (or zero for implausibly fast) BKT influence."""
    target = bkt_update(prior, correct)
    weight = 0.0 if "under_2_seconds" in anomaly_reasons else 0.25 if anomaly_reasons else 1.0
    return min(1.0, max(0.0, prior + weight * (target - prior)))


def detect_misconception_id(question: dict, selected_index: int) -> str | None:
    """Return the authored misconception tag for an incorrect choice, if present."""
    tags = question.get("misconception_ids") or []
    if selected_index < 0 or selected_index >= len(tags):
        return None
    return tags[selected_index] or None


def build_learning_path(
    concepts: list[dict],
    mastery: dict[str, float],
    active_misconceptions: list[dict],
    last_reviewed_days: dict[str, float] | None = None,
) -> list[dict]:
    """Prioritize repairs, due spaced reviews, then prerequisite-ready new practice."""
    repair_slugs = {item["concept_slug"] for item in active_misconceptions}
    result = [
        {
            "conceptId": item["concept_slug"],
            "title": item["title"],
            "reason": item.get("evidence") or "Review this misconception before advancing.",
            "kind": "repair",
        }
        for item in active_misconceptions
    ]
    last_reviewed_days = last_reviewed_days or {}
    for concept in concepts:
        slug = concept["slug"]
        score = mastery.get(slug, 0.2)
        # Longer-interval review for strongly mastered concepts; review is only
        # eligible after we have evidence that the learner studied the concept.
        interval_days = 14 if score >= 0.9 else 7
        age_days = last_reviewed_days.get(slug)
        if slug not in repair_slugs and score >= 0.75 and age_days is not None and age_days >= interval_days:
            result.append(
                {
                    "conceptId": slug,
                    "title": concept["title"],
                    "reason": f"Spaced review is due after {round(age_days)} days away",
                    "kind": "review",
                }
            )
    for concept in concepts:
        score = mastery.get(concept["slug"], 0.2)
        if (
            concept["slug"] not in repair_slugs
            and score < 0.75
            and all(mastery.get(dep, 0.2) >= 0.6 for dep in concept["prerequisites"])
        ):
            result.append(
                {
                    "conceptId": concept["slug"],
                    "title": concept["title"],
                    "reason": "Strengthen this prerequisite concept before moving forward",
                    "kind": "practice",
                }
            )
    if not result and concepts:
        item = concepts[-1]
        result.append(
            {
                "conceptId": item["slug"],
                "title": item["title"],
                "reason": "Your foundations are strong; revisit a mastered idea with a challenge",
                "kind": "challenge",
            }
        )
    return result[:6]
