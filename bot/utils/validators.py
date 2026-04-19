import re


def validate_kingdom_name(name):
    """Validate kingdom name: 3-20 chars, alphanumeric + spaces"""
    if not name:
        return False, "Name khali nahi ho sakta!"
    if len(name) < 3:
        return False, "Name kam se kam 3 characters ka hona chahiye!"
    if len(name) > 20:
        return False, "Name 20 characters se zyada nahi ho sakta!"
    if not re.match(r'^[a-zA-Z0-9\s]+$', name):
        return False, "Sirf letters, numbers, aur spaces allowed hain!"
    return True, None


def validate_alliance_name(name):
    """Validate alliance name"""
    if not name:
        return False, "Alliance name khali nahi ho sakta!"
    if len(name) < 3:
        return False, "3 characters minimum!"
    if len(name) > 20:
        return False, "20 characters maximum!"
    return True, None


def validate_positive_number(value, min_val=1, max_val=None):
    """Validate a positive number within range"""
    try:
        num = int(value)
        if num < min_val:
            return False, f"Minimum {min_val} hona chahiye!"
        if max_val and num > max_val:
            return False, f"Maximum {max_val} allowed!"
        return True, num
    except (ValueError, TypeError):
        return False, "Valid number enter karo!"
