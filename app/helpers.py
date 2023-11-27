def is_valid_email(email):
    # Simple regex for validating an email
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_strong_password(password):
    # Check for minimum length, and other criteria if needed
    return len(password) >= 6