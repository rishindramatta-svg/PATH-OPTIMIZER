import pytest

from app.security import reset_rate_limits


@pytest.fixture(autouse=True)
def reset_process_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()
