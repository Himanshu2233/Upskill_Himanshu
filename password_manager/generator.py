# generator.py — Strong Password Generator
#
# Uses Python's built-in 'secrets' module.
#
# Why 'secrets' and not 'random'?
# → 'random' is for simulations/games (predictable if you know the seed)
# → 'secrets' uses the OS's cryptographically secure random source
#   It's the RIGHT choice for anything security-related.

import secrets
import string


def generate_password(length: int = 16,
                      use_upper: bool = True,
                      use_digits: bool = True,
                      use_symbols: bool = True) -> str:
    """
    Generates a strong random password.

    Parameters:
        length      : Total length of the password (default 16)
        use_upper   : Include uppercase letters (A-Z)
        use_digits  : Include numbers (0-9)
        use_symbols : Include symbols (!@#$...)

    Returns:
        A randomly generated password string.

    How it works:
        1. Build a pool of allowed characters
        2. Guarantee at least 1 of each required type
        3. Fill the rest randomly
        4. Shuffle to remove any predictable pattern
    """
    # Start with lowercase letters (always included)
    pool = string.ascii_lowercase           # 'abcdefghijklmnopqrstuvwxyz'
    guaranteed = [secrets.choice(string.ascii_lowercase)]

    if use_upper:
        pool += string.ascii_uppercase      # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        guaranteed.append(secrets.choice(string.ascii_uppercase))

    if use_digits:
        pool += string.digits               # '0123456789'
        guaranteed.append(secrets.choice(string.digits))

    if use_symbols:
        symbols = '!@#$%^&*()-_=+[]{}|;:,.<>?'
        pool += symbols
        guaranteed.append(secrets.choice(symbols))

    # Fill remaining slots
    remaining_length = length - len(guaranteed)
    rest = [secrets.choice(pool) for _ in range(remaining_length)]

    # Combine guaranteed + rest, then shuffle
    password_list = guaranteed + rest
    secrets.SystemRandom().shuffle(password_list)   # Cryptographically secure shuffle

    return ''.join(password_list)


def check_strength(password: str) -> dict:
    """
    Analyzes how strong a password is.

    Returns a dict with:
        score   : 0-100
        label   : 'Weak' / 'Fair' / 'Strong' / 'Very Strong'
        color   : Hex color for the strength bar
        tips    : List of improvement suggestions
    """
    score = 0
    tips  = []

    # Length scoring
    if len(password) >= 8:   score += 20
    if len(password) >= 12:  score += 15
    if len(password) >= 16:  score += 15
    else: tips.append('Use at least 16 characters')

    # Character variety scoring
    has_lower   = any(c.islower() for c in password)
    has_upper   = any(c.isupper() for c in password)
    has_digit   = any(c.isdigit() for c in password)
    has_symbol  = any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?' for c in password)

    if has_lower:  score += 10
    if has_upper:  score += 10; 
    else:          tips.append('Add uppercase letters')
    if has_digit:  score += 15
    else:          tips.append('Add numbers')
    if has_symbol: score += 15
    else:          tips.append('Add symbols (!@#$...)')

    score = min(score, 100)

    if score < 40:   label, color = 'Weak',        '#ef4444'
    elif score < 65: label, color = 'Fair',        '#f59e0b'
    elif score < 85: label, color = 'Strong',      '#10b981'
    else:            label, color = 'Very Strong', '#06b6d4'

    return {'score': score, 'label': label, 'color': color, 'tips': tips}
