"""Unit tests for app/remote_exec.py's security properties, from
docs/REMOTE_EXEC.md: no shell involved (no injection surface from
script content), sudo/ssh passwords never appear in argv, and any
password that leaks into stderr text gets redacted before it's
returned. subprocess.run is monkeypatched -- no real SSH connection is
made."""

import subprocess

import pytest


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture()
def remote_exec_module(app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "true")
    from app import remote_exec

    return remote_exec


def test_ssh_invoked_as_argv_list_not_shell_string(remote_exec_module, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeCompletedProcess(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    machine = {"ssh_user": "u", "host": "h", "port": 22, "ssh_key_path": "/key", "auth_type": "key"}
    remote_exec_module.run_remote(machine, "echo hi")

    assert isinstance(captured["cmd"], list)
    assert "shell" not in captured["kwargs"] or captured["kwargs"]["shell"] is False


def test_sudo_password_never_in_argv(remote_exec_module, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input", "")
        return FakeCompletedProcess(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    machine = {"ssh_user": "u", "host": "h", "port": 22, "ssh_key_path": "/key", "auth_type": "key"}
    secret = "s3cr3t-sudo-pw"
    remote_exec_module.run_remote(machine, "echo hi", sudo_password=secret)

    joined_argv = " ".join(captured["cmd"])
    assert secret not in joined_argv
    # it IS expected on stdin -- that's the documented delivery channel
    assert secret in captured["input"]


def test_sudo_password_redacted_from_stderr(remote_exec_module, monkeypatch):
    secret = "s3cr3t-sudo-pw"

    def fake_run(cmd, **kwargs):
        # simulate a password that leaked into stderr somehow (e.g. sudo
        # prompt text bleeding through despite -p '')
        return FakeCompletedProcess(returncode=1, stdout="", stderr=f"Password: {secret}\nSorry.")

    monkeypatch.setattr(subprocess, "run", fake_run)

    machine = {"ssh_user": "u", "host": "h", "port": 22, "ssh_key_path": "/key", "auth_type": "key"}
    result = remote_exec_module.run_remote(machine, "echo hi", sudo_password=secret)

    assert secret not in result["stderr"]
    assert "***" in result["stderr"]


def test_password_auth_password_never_in_argv(remote_exec_module, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env") or {}
        return FakeCompletedProcess(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    machine = {"ssh_user": "u", "host": "h", "port": 22, "auth_type": "password"}
    secret = "s3cr3t-ssh-pw"
    remote_exec_module.run_remote(machine, "echo hi", ssh_password=secret)

    joined_argv = " ".join(captured["cmd"])
    assert secret not in joined_argv
    # delivered via SSHPASS env var instead, per docs/REMOTE_EXEC.md
    assert captured["env"].get("SSHPASS") == secret


def test_disabled_by_default(app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "false")
    from app import remote_exec

    machine = {"ssh_user": "u", "host": "h", "port": 22, "ssh_key_path": "/key", "auth_type": "key"}
    with pytest.raises(remote_exec.RemoteExecDisabledError):
        remote_exec.run_remote(machine, "echo hi")
