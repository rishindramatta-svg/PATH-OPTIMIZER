from app.evaluation.run import render_markdown
from app.evaluation.simulator import SEED, simulate


def test_simulator_is_seed_reproducible_and_uses_both_strategies():
    first = simulate(SEED, 40, 3)
    second = simulate(SEED, 40, 3)
    assert len(first["results"]) == 10
    volatile = {"path_update_latency_p50_ms", "path_update_latency_p95_ms"}

    def normalized(result):
        return [{key: value for key, value in row.items() if key not in volatile} for row in result["results"]]

    assert normalized(first) == normalized(second)
    assert {row["strategy"] for row in first["results"]} == {"adaptive", "static"}


def test_simulator_reports_required_metrics_and_honest_interpretation():
    output = simulate(SEED, 30, 4)
    expected = {
        "learning_gain",
        "time_to_mastery_questions",
        "misconception_resolution_rate",
        "guess_detection_precision",
        "guess_detection_recall",
        "calibration_error",
        "path_update_latency_p50_ms",
        "path_update_latency_p95_ms",
    }
    assert expected <= output["results"][0].keys()
    report = render_markdown(output)
    assert "not evidence of classroom outcomes" in report
    assert "Adaptive − static" in report


def test_thirty_seed_evaluation_reports_held_out_gain_and_paired_intervals():
    result = simulate(SEED, 2, 30)
    assert result["seedsPerProfile"] == 30
    assert len(result["results"]) == 10
    adaptive = result["results"][0]
    assert adaptive["learning_gain"]["n"] == 30
    assert "questions_to_80_mastery" in adaptive
    assert adaptive["path_update_latency_p95_ms"] is not None
    report = render_markdown(result)
    assert "held-out item set" in report
    assert "paired seeds" in report
    assert "adaptive minus static" in report.lower()
