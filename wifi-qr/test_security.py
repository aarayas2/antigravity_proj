"""Tests for security aspects of WiFi QR code generation, specifically SSID sanitization."""

import re

def sanitize_ssid(ssid):
    """Sanitizes the SSID string by replacing non-alphanumeric characters with underscores."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', ssid)

def test_ssid_sanitization():
    """Tests the sanitize_ssid function with various inputs, including path traversal attempts."""
    # "WiFi/../etc/passwd"
    # / is 1 char
    # . is 1 char
    # . is 1 char
    # / is 1 char
    # total 4 chars between WiFi and etc

    # "../../../etc/shadow"
    # .. is 2
    # / is 1
    # .. is 2
    # / is 1
    # .. is 2
    # / is 1
    # total 9 chars before etc

    test_cases = [
        ("My WiFi", "My_WiFi"),
        ("WiFi/../etc/passwd", "WiFi____etc_passwd"),
        ("WiFi_123", "WiFi_123"),
        ("WiFi!@#", "WiFi___"),
        ("../../../etc/shadow", "_________etc_shadow"),
    ]
    for ssid, expected in test_cases:
        assert sanitize_ssid(ssid) == expected

def test_filename_construction():
    """Tests that constructed filenames are safe from path traversal."""
    ssid = "../../../etc/passwd"
    sanitized_ssid = sanitize_ssid(ssid)
    filename = f"{sanitized_ssid}_wifi_qr.png"
    assert ".." not in filename
    assert "/" not in filename
    assert filename == "_________etc_passwd_wifi_qr.png"
