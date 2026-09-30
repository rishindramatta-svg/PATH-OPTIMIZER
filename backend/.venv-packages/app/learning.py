def bkt_update(prior: float, correct: bool, p_learn: float = .12, p_slip: float = .1, p_guess: float = .2) -> float:
    """Bayesian knowledge tracing posterior followed by the learning transition."""
    p = min(1.0, max(0.0, prior))
    likelihood_known = 1 - p_slip if correct else p_slip
    likelihood_unknown = p_guess if correct else 1 - p_guess
    denominator = p * likelihood_known + (1 - p) * likelihood_unknown
    posterior = p if denominator == 0 else p * likelihood_known / denominator
    return min(1.0, max(0.0, posterior + (1 - posterior) * p_learn))

def calibration_label(confidence: int, mastery: float) -> str:
    gap = confidence / 5 - mastery
    if gap > .2: return "overconfident"
    if gap < -.2: return "underconfident"
    return "calibrated"
