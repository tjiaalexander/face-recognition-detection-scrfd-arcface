import asyncio

import numpy as np
import pytest

from app.services.liveness import LivenessResult, allowed_for_sensitive_action, build_liveness


def test_default_liveness_never_passes():
    r = asyncio.run(build_liveness("none").check([np.zeros((10, 10, 3), np.uint8)]))
    assert r.status == "not_configured" and r.passed is False
    assert not allowed_for_sensitive_action(r, confirmed=True)


def test_unimplemented_mode_is_not_faked():
    with pytest.raises(NotImplementedError):
        build_liveness("magic")


def test_only_real_pass_allows_action():
    assert allowed_for_sensitive_action(LivenessResult("passed", True), True)
    assert not allowed_for_sensitive_action(LivenessResult("passed", True), False)
