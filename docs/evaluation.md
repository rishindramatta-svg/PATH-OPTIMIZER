# PNG9 Evaluation Simulator

Base seed: `9012026` · 30 paired seeds per profile · 120 practice interactions per arm and seed.

Values are mean [95% confidence interval]. The interval is a normal approximation (mean ± 1.96 standard errors) across independent seeds; time-to-threshold metrics include only runs that reached the threshold, and their sample counts are shown.

| Profile | Strategy | Held-out learning gain | Questions to full mastery | Questions to 80% mastery | Misconception resolution | Calibration error | Guess precision | Guess recall | Path p50/p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fast learner | adaptive | 0.242 [0.200, 0.283], n=30 | Not reached (0/30) | Not reached (0/30) | 1.000 [1.000, 1.000], n=30 | 0.254 [0.251, 0.258], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | 0.015/0.022 |
| fast learner | static | 0.223 [0.183, 0.264], n=30 | Not reached (0/30) | Not reached (0/30) | 0.278 [0.189, 0.367], n=30 | 0.285 [0.281, 0.288], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | Not applicable |
| slow learner | adaptive | 0.093 [0.066, 0.121], n=30 | Not reached (0/30) | Not reached (0/30) | 1.000 [1.000, 1.000], n=30 | 0.285 [0.280, 0.290], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | 0.015/0.019 |
| slow learner | static | 0.072 [0.046, 0.097], n=30 | Not reached (0/30) | Not reached (0/30) | 0.378 [0.275, 0.480], n=30 | 0.303 [0.299, 0.307], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | Not applicable |
| random guesser | adaptive | 0.010 [0.003, 0.017], n=30 | Not reached (0/30) | Not reached (0/30) | 1.000 [1.000, 1.000], n=30 | 0.139 [0.120, 0.158], n=30 | 1.000 [1.000, 1.000], n=30 | 1.000 [1.000, 1.000], n=30 | 0.016/0.022 |
| random guesser | static | 0.007 [0.001, 0.013], n=30 | Not reached (0/30) | Not reached (0/30) | 0.167 [0.092, 0.242], n=30 | 0.113 [0.099, 0.127], n=30 | 1.000 [1.000, 1.000], n=30 | 1.000 [1.000, 1.000], n=30 | Not applicable |
| overconfident | adaptive | 0.060 [0.042, 0.078], n=30 | Not reached (0/30) | Not reached (0/30) | 1.000 [1.000, 1.000], n=30 | 0.473 [0.457, 0.489], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | 0.015/0.018 |
| overconfident | static | 0.038 [0.025, 0.051], n=30 | Not reached (0/30) | Not reached (0/30) | 0.256 [0.163, 0.348], n=30 | 0.555 [0.538, 0.572], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | Not applicable |
| erratic | adaptive | 0.058 [0.042, 0.075], n=30 | Not reached (0/30) | Not reached (0/30) | 1.000 [1.000, 1.000], n=30 | 0.279 [0.264, 0.293], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | 0.015/0.021 |
| erratic | static | 0.042 [0.025, 0.059], n=30 | Not reached (0/30) | Not reached (0/30) | 0.267 [0.166, 0.368], n=30 | 0.304 [0.289, 0.319], n=30 | 0.000 [0.000, 0.000], n=30 | 0.000 [0.000, 0.000], n=30 | Not applicable |

## Diagnosis and methodology

The earlier result was not a fair learning-gain comparison. It used the BKT state on practiced concepts as the outcome, so it measured the estimator that the adaptive path itself consumed rather than independent transfer. It also minted a misconception after every wrong answer and called it resolved when BKT mastery crossed 0.75; targeted remediation was not represented as a learning event. Both old arms had equal response counts, but neither issue is repaired by equal counts alone.

This run gives adaptive and static arms the same practice-interaction budget and paired random seed. Student learning is modeled independently of path selection: ten chained concepts start at latent mastery 0.25; correct practice causes profile-specific gradual acquisition, unflagged wrong answers cause a small latent decrement, and random guessers have low skill and low acquisition. Three concepts have an initially held misconception. The misconception only surfaces when the learner selects its authored tagged distractor. A targeted worked-example interaction has profile-specific probability of resolving the belief and provides modest acquisition; ordinary correct practice with feedback has a smaller 12% chance to resolve a held belief. These are explicit synthetic assumptions, not parameters fitted to human data.

Learning gain is pre/post accuracy on the same fixed, held-out item set (two unseen items per concept), using common random numbers within a seed. These assessment items do not consume practice budget and are never shown during practice. The production BKT update, anomaly detector, misconception tag detector, and production path optimizer are reused for the adaptive arm's state and sequencing. Static cycles through concepts and does not receive targeted repair. Production path priority is active misconception repair, then overdue spaced review (7 days after last study, or 14 days at mastery ≥0.90), then earliest prerequisite-eligible practice; the challenge item is the fallback when no other work remains. The simulator advances one study day per practice interaction for its synthetic review clock. We did not tune the optimizer to target a winning score.

Time to mastery is the first practice interaction where all ten latent concept values are at least 0.80. Questions to 80% mastery is the first point where at least eight of ten are at least 0.80. Misconception resolution is resolved initial beliefs divided by the three initial beliefs. Calibration error is ten-bin expected calibration error on practice responses. Guess detection treats the random-guesser profile as the positive class; this is a simulator label, not a validated real-world detector.

## Paired adaptive minus static

Values are mean paired difference [95% CI]. Negative is worse for higher-is-better metrics and better for error/count metrics.

| Profile | Metric | Adaptive − static [95% CI] |
|---|---|---:|
| fast learner | learning_gain | 0.018 [-0.008, 0.045], n=30 |
| fast learner | time_to_mastery_questions | Not reached |
| fast learner | questions_to_80_mastery | Not reached |
| fast learner | misconception_resolution_rate | 0.722 [0.633, 0.811], n=30 |
| fast learner | guess_detection_precision | 0.000 [0.000, 0.000], n=30 |
| fast learner | guess_detection_recall | 0.000 [0.000, 0.000], n=30 |
| fast learner | calibration_error | -0.030 [-0.034, -0.026], n=30 |
| slow learner | learning_gain | 0.022 [-0.002, 0.045], n=30 |
| slow learner | time_to_mastery_questions | Not reached |
| slow learner | questions_to_80_mastery | Not reached |
| slow learner | misconception_resolution_rate | 0.622 [0.520, 0.725], n=30 |
| slow learner | guess_detection_precision | 0.000 [0.000, 0.000], n=30 |
| slow learner | guess_detection_recall | 0.000 [0.000, 0.000], n=30 |
| slow learner | calibration_error | -0.018 [-0.024, -0.013], n=30 |
| random guesser | learning_gain | 0.003 [-0.007, 0.014], n=30 |
| random guesser | time_to_mastery_questions | Not reached |
| random guesser | questions_to_80_mastery | Not reached |
| random guesser | misconception_resolution_rate | 0.833 [0.758, 0.908], n=30 |
| random guesser | guess_detection_precision | 0.000 [0.000, 0.000], n=30 |
| random guesser | guess_detection_recall | 0.000 [0.000, 0.000], n=30 |
| random guesser | calibration_error | 0.026 [0.009, 0.044], n=30 |
| overconfident | learning_gain | 0.022 [0.002, 0.041], n=30 |
| overconfident | time_to_mastery_questions | Not reached |
| overconfident | questions_to_80_mastery | Not reached |
| overconfident | misconception_resolution_rate | 0.744 [0.652, 0.837], n=30 |
| overconfident | guess_detection_precision | 0.000 [0.000, 0.000], n=30 |
| overconfident | guess_detection_recall | 0.000 [0.000, 0.000], n=30 |
| overconfident | calibration_error | -0.082 [-0.096, -0.068], n=30 |
| erratic | learning_gain | 0.017 [-0.005, 0.038], n=30 |
| erratic | time_to_mastery_questions | Not reached |
| erratic | questions_to_80_mastery | Not reached |
| erratic | misconception_resolution_rate | 0.733 [0.632, 0.834], n=30 |
| erratic | guess_detection_precision | 0.000 [0.000, 0.000], n=30 |
| erratic | guess_detection_recall | 0.000 [0.000, 0.000], n=30 |
| erratic | calibration_error | -0.026 [-0.039, -0.013], n=30 |

## Interpretation

Observed result: adaptive has lower held-out gain than static for fast learners, with a paired interval below zero. For slow learners, random guessers, overconfident learners, and erratic learners, the paired gain interval includes zero, so this run does not establish a gain difference. Adaptive resolves more tagged misconceptions and has lower calibration error in most profiles, but it does not beat the baseline on every metric: random guessers have higher calibration error under adaptive sequencing. No profile reached the 80%-of-concepts threshold or full mastery within 120 interactions, so mastery-time comparisons are not reached for all profiles. Repair-first, mastery-gated spaced review, then prerequisite-eligible practice is a sensible ordering for this chain; the static round-robin baseline still wins held-out gain for fast learners. We have not tuned the optimizer to target a winning score. Reported latency is wall-clock Python optimizer time and descriptive only. This is not evidence of classroom outcomes.
