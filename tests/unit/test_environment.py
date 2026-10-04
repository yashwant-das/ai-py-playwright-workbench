"""Checks for the external tools the workbench needs."""

import pytest

from workbench import environment


def test_node_available_follows_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(environment.shutil, "which", lambda name: "/usr/bin/node")
    assert environment.node_available()
    monkeypatch.setattr(environment.shutil, "which", lambda name: None)
    assert not environment.node_available()
