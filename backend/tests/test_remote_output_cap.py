"""Regression tests for the silent output truncation that used to make
remote scan/import quietly lose files.

app/remote_exec.py capped ALL captured stdout at 20k characters, which
was fine for "show me what this script printed" but catastrophic for
app/remote_import.py, which streams every scanned file through that same
stdout as base64: a directory of ordinary scripts came back as HTTP 200
with only the first couple of entries and no error anywhere, and any
single file over ~15 KB failed to base64-decode on rescan (reported as
"could not decode content", i.e. looked like a corrupt source file
rather than a size limit).

SSH is mocked throughout -- these are about how much of the transport's
output survives, not about SSH itself.
"""

import base64
import subprocess

import pytest


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


MACHINE = {
    "name": "testbox",
    "ssh_user": "u",
    "host": "h",
    "port": 22,
    "ssh_key_path": "/key",
    "auth_type": "key",
}


@pytest.fixture()
def modules(app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "true")
    from app import remote_exec, remote_import

    return remote_exec, remote_import


def _scan_payload(files: dict[str, str]) -> str:
    """Rebuild exactly what _list_script_command prints on the remote
    side: marker, path, base64 on one line, marker."""
    from app.remote_import import FILE_END, FILE_START

    out = []
    for path, content in files.items():
        b64 = base64.b64encode(content.encode()).decode()
        out.append(f"{FILE_START}\n{path}\n{b64}\n{FILE_END}\n")
    return "".join(out)


def test_scan_does_not_silently_drop_files_past_the_display_cap(modules, monkeypatch):
    remote_exec, remote_import = modules

    # 8 scripts of ~5 KB each -- well past the 20k display cap once
    # base64-encoded, but an entirely ordinary script folder.
    files = {f"/home/u/scripts/s{i}.sh": f"#!/bin/bash\n# script {i}\n" + ("x" * 5000) for i in range(8)}
    payload = _scan_payload(files)
    assert len(payload) > remote_exec.MAX_OUTPUT_CHARS

    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: FakeCompletedProcess(stdout=payload)
    )

    result = remote_import.scan_remote_path(MACHINE, "/home/u/scripts", set())

    assert len(result["candidates"]) == len(files), "files were dropped from the scan"
    assert [c["path"] for c in result["candidates"]] == list(files)
    assert result["skipped"] == []


def test_scan_raises_instead_of_returning_a_partial_result(modules, monkeypatch):
    """If output ever DOES exceed the (much larger) transfer cap, the
    caller must find out -- a short candidate list that looks like a
    successful scan is the exact failure mode being fixed."""
    remote_exec, remote_import = modules

    monkeypatch.setattr(remote_exec, "MAX_TRANSFER_OUTPUT_CHARS", 500)
    monkeypatch.setattr(remote_import, "MAX_TRANSFER_OUTPUT_CHARS", 500)
    payload = _scan_payload({f"/s{i}.sh": "y" * 300 for i in range(4)})
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: FakeCompletedProcess(stdout=payload)
    )

    with pytest.raises(remote_exec.RemoteOutputTruncatedError):
        remote_import.scan_remote_path(MACHINE, "/x", set())


def test_pull_file_handles_a_file_larger_than_the_display_cap(modules, monkeypatch):
    """`base64 <path>` of anything over ~15 KB used to land mid-quantum
    after truncation (len % 4 == 1) and blow up in binascii."""
    remote_exec, remote_import = modules

    content = "#!/bin/bash\n" + "echo hello\n" * 4000
    # GNU base64 wraps at 76 columns -- reproduce that, since the
    # decoder has to tolerate the newlines.
    raw = base64.b64encode(content.encode()).decode()
    wrapped = "\n".join(raw[i : i + 76] for i in range(0, len(raw), 76)) + "\n"
    assert len(wrapped) > remote_exec.MAX_OUTPUT_CHARS

    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: FakeCompletedProcess(stdout=wrapped)
    )

    assert remote_import.pull_file(MACHINE, "/home/u/big.sh") == content


def test_truncation_is_reported_on_the_normal_display_path(modules, monkeypatch):
    """Interactive runs still get the small cap -- but now they say so
    instead of just handing back a shortened string."""
    remote_exec, _ = modules
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kw: FakeCompletedProcess(stdout="z" * (remote_exec.MAX_OUTPUT_CHARS + 10)),
    )

    result = remote_exec.run_remote(MACHINE, "echo hi")
    assert len(result["stdout"]) == remote_exec.MAX_OUTPUT_CHARS
    assert result["stdout_truncated"] is True
    assert result["stderr_truncated"] is False


def test_unparseable_block_is_reported_not_swallowed(modules, monkeypatch):
    """A block that can't be decoded used to vanish into a bare
    `except: continue`."""
    _, remote_import = modules
    from app.remote_import import FILE_END, FILE_START

    good = _scan_payload({"/ok.sh": "#!/bin/bash\necho ok\n"})
    broken = f"{FILE_START}\n/broken.sh\n!!!not-base64!!!\n{FILE_END}\n"
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: FakeCompletedProcess(stdout=good + broken)
    )

    result = remote_import.scan_remote_path(MACHINE, "/x", set())
    assert [c["path"] for c in result["candidates"]] == ["/ok.sh"]
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["path"] == "/broken.sh"
