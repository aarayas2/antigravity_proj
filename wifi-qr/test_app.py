"""Tests for the WiFi QR code generator application."""
# pylint: disable=duplicate-code

import os
from unittest.mock import patch

# pylint: disable=import-error
from streamlit.testing.v1 import AppTest


def test_qr_generation_error():
    """
    Test that the application handles exceptions correctly when generating a QR code.
    This covers the missing error test in app.py:265.
    """
    # Create an AppTest instance pointing to app.py
    # Use dynamic path based on this test file's location
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    at = AppTest.from_file(app_path)

    # Run the app to initialize it
    at.run()

    # Fill in the required fields
    # Network Name (SSID)
    # pylint: disable=no-member
    at.text_input[0].set_value("My WiFi")

    # Password
    at.text_input[1].set_value("password123")

    # Security is already WPA by default (first option)

    # Mock the make_wifi function to raise an exception
    with patch('segno.helpers.make_wifi', side_effect=Exception("Test QR generation error")):
        # Click the 'Generate QR Code' button
        at.button[0].click().run()

        # Verify that an error message is displayed
        assert len(at.error) > 0, "Expected an error message to be displayed"

        # Ensure the error message matches the expected output format
        expected_error_text = (
            "An error occurred while generating the QR code: "
            "Test QR generation error"
        )
        assert at.error[0].value == expected_error_text, (
            f"Expected '{expected_error_text}' but got '{at.error[0].value}'"
        )
