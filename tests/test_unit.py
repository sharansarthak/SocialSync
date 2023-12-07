import pytest

from app.helpers import is_strong_password, is_valid_email



def test_is_strong_password():
    assert is_strong_password("StrongPassword123!") == True
    assert is_strong_password("weak") == False
    assert is_strong_password("") == False

def test_is_valid_email():
    # Test with valid emails
    assert is_valid_email("example@test.com") == True
    assert is_valid_email("user123@domain.co.uk") == True

    # Test with invalid emails
    assert is_valid_email("invalidemail") == False
    assert is_valid_email("missingatsign.com") == False
    assert is_valid_email("invalid@.com") == False
    assert is_valid_email("@no-local-part.com") == False
    assert is_valid_email("invalid@domain") == False
    assert is_valid_email("") == False  # Empty string