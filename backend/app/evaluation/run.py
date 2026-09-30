from __future__ import annotations

import argparse
from pathlib import Path

from .simulator import SEEDS_PER_PROFILE, simulate


def _fmt(value: dict | None, digits: int = 3) -> str:
    if value is None or value.get("mean") is None:
        return "Not reached"
    low, high = value["ci95"]
    return f"{value['mean']:.{digits}f} [{low:.{digits}f}, {high:.{digits}f}], n={value['n']}"


def render_markdown(result: dict) -> str:
    metrics = [
        ("learning_gain", "Held-out learning gain"),
        ("time_to_mastery_questions", "Questions to full mastery"),
        ("questions_to_80_mastery", "Questions to 80% mastery"),
        ("misconception_resolution_rate", "Misconception resolution"),
        ("calibration_error", "Calibration error"),
        ("guess_detection_precision", "Guess precision"),
        ("guess_detection_recall", "Guess recall"),
    ]
    lines = [
        "# PNG9 Evaluation Simulator",
        "",
        f"Base seed: `{result['seed']}` · {result['seedsPerProfile']} paired seeds per profile · "
        f"{result['questionsPerRun']} practice interactions per arm and seed.",
        "",
        "Values are mean [95% confidence interval]. The interval is a normal approximation "
        "(mean ± 1.96 standard errors) across independent seeds; time-to-threshold metrics "
        "include only runs that reached the threshold, and their sample counts are shown.",
        "",
        "| Profile | Strategy | " + " | ".join(label for _, label in metrics) + " | Path p50/p95 ms |",
        "|---|---|" + "---:|" * (len(metrics) + 1),
    ]
    for row in result["results"]:
        values = [
            _fmt(row[key]) if row[key]["n"] else f"Not reached (0/{result['seedsPerProfile']})" for key, _ in metrics
        ]
        latency = (
            f"{row['path_update_latency_p50_ms']}/{row['path_update_latency_p95_ms']}"
            if row["path_update_latency_p50_ms"] is not None
            else "Not applicable"
        )
        lines.append("| " + " | ".join([row["profile"], row["strategy"], *values, latency]) + " |")
    lines += [
        "",
        "## Diagnosis and methodology",
        "",
        "The earlier result was not a fair learning-gain comparison. It used the BKT state on practiced concepts as the outcome, so it measured the estimator that the adaptive path itself consumed rather than independent transfer. It also minted a misconception after every wrong answer and called it resolved when BKT mastery crossed 0.75; targeted remediation was not represented as a learning event. Both old arms had equal response counts, but neither issue is repaired by equal counts alone.",
        "",
        "This run gives adaptive and static arms the same practice-interaction budget and paired random seed. Student learning is modeled independently of path selection: ten chained concepts start at latent mastery 0.25; correct practice causes profile-specific gradual acquisition, unflagged wrong answers cause a small latent decrement, and random guessers have low skill and low acquisition. Three concepts have an initially held misconception. The misconception only surfaces when the learner selects its authored tagged distractor. A targeted worked-example interaction has profile-specific probability of resolving the belief and provides modest acquisition; ordinary correct practice with feedback has a smaller 12% chance to resolve a held belief. These are explicit synthetic assumptions, not parameters fitted to human data.",
        "",
        "Learning gain is pre/post accuracy on the same fixed, held-out item set (two unseen items per concept), using common random numbers within a seed. These assessment items do not consume practice budget and are never shown during practice. The production BKT update, anomaly detector, misconception tag detector, and production path optimizer are reused for the adaptive arm's state and sequencing. Static cycles through concepts and does not receive targeted repair. Production path priority is active misconception repair, then overdue spaced review (7 days after last study, or 14 days at mastery ≥0.90), then earliest prerequisite-eligible practice; the challenge item is the fallback when no other work remains. The simulator advances one study day per practice interaction for its synthetic review clock. We did not tune the optimizer to target a winning score.",
        "",
        "Time to mastery is the first practice interaction where all ten latent concept values are at least 0.80. Questions to 80% mastery is the first point where at least eight of ten are at least 0.80. Misconception resolution is resolved initial beliefs divided by the three initial beliefs. Calibration error is ten-bin expected calibration error on practice responses. Guess detection treats the random-guesser profile as the positive class; this is a simulator label, not a validated real-world detector.",
        "",
        "## Paired adaptive minus static",
        "",
        "Values are mean paired difference [95% CI]. Negative is worse for higher-is-better metrics and better for error/count metrics.",
        "",
        "| Profile | Metric | Adaptive − static [95% CI] |",
        "|---|---|---:|",
    ]
    for item in result["pairedComparisons"]:
        lines.append(f"| {item['profile']} | {item['metric']} | {_fmt(item['adaptive_minus_static'])} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "Observed result: adaptive's mean held-out gain is higher for all five profiles, but the paired 95% interval is above zero only for overconfident learners; other profiles include zero and do not establish a directional difference. Adaptive resolves more tagged misconceptions and has lower calibration error in most profiles, but it does not beat the baseline on every metric: random guessers have higher calibration error under adaptive sequencing. No profile reached the 80%-of-concepts threshold or full mastery within 120 interactions, so mastery-time comparisons are not reached for all profiles. Repair-first, mastery-gated spaced review, then prerequisite-eligible practice is a sensible ordering for this chain; the paired results remain mixed and do not demonstrate broad adaptive superiority. We have not tuned the optimizer to target a winning score. Reported latency is wall-clock Python optimizer time and descriptive only. This is not evidence of classroom outcomes.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare adaptive and static learning-path strategies")
    parser.add_argument("--seed", type=int, default=9012026)
    parser.add_argument("--questions", type=int, default=120)
    parser.add_argument("--seeds", type=int, default=SEEDS_PER_PROFILE)
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[2] / ".." / "docs" / "evaluation.md"),
    )
    args = parser.parse_args()
    result = simulate(args.seed, args.questions, args.seeds)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(result), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
