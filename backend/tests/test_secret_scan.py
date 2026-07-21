from app.secret_scan import looks_like_it_has_a_secret


def test_detects_hardcoded_password():
    assert looks_like_it_has_a_secret('PASSWORD="s3cr3t123"')


def test_detects_aws_key_shape():
    assert looks_like_it_has_a_secret("AKIAABCDEFGHIJKLMNOP")


def test_detects_private_key_header():
    assert looks_like_it_has_a_secret("-----BEGIN OPENSSH PRIVATE KEY-----")


def test_detects_bearer_token():
    assert looks_like_it_has_a_secret("Authorization: Bearer abc123def456ghi789")


def test_plain_script_has_no_false_positive():
    content = "#!/bin/bash\nset -euo pipefail\ndu -sh /var/log\n"
    assert not looks_like_it_has_a_secret(content)
