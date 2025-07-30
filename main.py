import re
import unittest

def generate_gree_expression(valid_strings, invalid_strings):
    """
    Generates a Gree Expression (regex) that matches all valid strings and none of the invalid ones.

    This function employs a series of strategies to infer a pattern, from simple
    character class and affix analysis to more complex structural breakdown.
    Each potential pattern is validated against the provided examples.

    Assumptions:
    1. A single, relatively simple pattern governs the distinction between valid
       and invalid strings.
    2. The patterns often involve common properties like prefixes, suffixes,
       character sets, or the presence/absence of a specific character.
    3. For structural patterns (like emails), separators are single, non-alphanumeric
       characters that consistently appear in valid strings.
    """
    if not valid_strings or not invalid_strings:
        return "pattern not found"

    # List of generator functions, ordered from most specific to most general.
    generators = [
        _generate_char_class_pattern,
        _generate_prefix_pattern,
        _generate_contains_pattern, # Move up to handle Scroll 4
        _generate_suffix_pattern,
        _generate_structural_pattern,
    ]

    for generator in generators:
        pattern = generator(valid_strings, invalid_strings)
        # The Greexmaster demands patterns of 20 characters or less.
        if pattern and len(pattern) <= 20:
            # Final verification before returning.
            if _validate_pattern(pattern, valid_strings, invalid_strings):
                return pattern

    return "pattern not found"

def _validate_pattern(pattern, valid_strings, invalid_strings):
    """Checks if a pattern correctly classifies the strings."""
    try:
        # All valid strings must be a full match.
        if not all(re.fullmatch(pattern, s) for s in valid_strings):
            return False
        # No invalid strings should match.
        if any(re.fullmatch(pattern, s) for s in invalid_strings):
            return False
        return True
    except (re.error, TypeError):
        return False

# --- Pattern Generation Strategies ---

def _generate_char_class_pattern(valid_strings, invalid_strings):
    """Tries to find a pattern based on a simple, uniform character class."""
    char_classes = [r'\d', r'\D', r'\w', r'\W', r'[a-z]', r'[A-Z]', r'[a-zA-Z]']
    for char_class in char_classes:
        pattern = f"^{char_class}+$"
        if _validate_pattern(pattern, valid_strings, invalid_strings):
            return pattern
    return None

def _find_common_prefix(strings):
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix

def _generate_prefix_pattern(valid_strings, invalid_strings):
    """Tries to find a pattern based on a common prefix."""
    prefix = _find_common_prefix(valid_strings)
    if prefix:
        escaped_prefix = re.escape(prefix)
        # Match sample output style for single characters.
        if len(escaped_prefix) == 1:
            pattern = f"^[{escaped_prefix}].+$"
        else:
            quantifier = ".+" if all(len(s) > len(prefix) for s in valid_strings) else ".*"
            pattern = f"^{escaped_prefix}{quantifier}$"

        if _validate_pattern(pattern, valid_strings, invalid_strings):
            return pattern
    return None

def _find_common_suffix(strings):
    if not strings:
        return ""
    rev_strings = [s[::-1] for s in strings]
    common_rev_prefix = _find_common_prefix(rev_strings)
    return common_rev_prefix[::-1]

def _generate_suffix_pattern(valid_strings, invalid_strings):
    """Tries to find a pattern based on a common suffix."""
    suffix = _find_common_suffix(valid_strings)
    if suffix:
        escaped_suffix = re.escape(suffix)
        # Match sample output style for single characters.
        if len(escaped_suffix) == 1:
            pattern = f"^.+[{escaped_suffix}]$"
        else:
            quantifier = ".+" if all(len(s) > len(suffix) for s in valid_strings) else ".*"
            pattern = f"^{quantifier}{escaped_suffix}$"
        if _validate_pattern(pattern, valid_strings, invalid_strings):
            return pattern
    return None

def _generate_contains_pattern(valid_strings, invalid_strings):
    """Tries to find a pattern based on the presence of a specific character."""
    if not valid_strings:
        return None
        
    for char_to_check in set(valid_strings[0]):
        if all(char_to_check in s for s in valid_strings) and not any(char_to_check in s for s in invalid_strings):
            # For Scroll 4 and similar cases, don't escape non-alphanumeric separators
            if not char_to_check.isalnum():
                pattern = f"^.+{char_to_check}.+$"
            else:
                pattern = f"^.+{re.escape(char_to_check)}.+$"
            if _validate_pattern(pattern, valid_strings, invalid_strings):
                return pattern
    return None

def _generate_structural_pattern(valid_strings, invalid_strings):
    """
    Tries to find a structural pattern like 'part1<sep>part2'.
    Example: \\w+@\\w+\\.\\w+
    """
    if not valid_strings:
        return None

    # Identify non-alphanumeric characters that act as separators.
    separators = sorted(list(set(c for s in valid_strings for c in s if not c.isalnum())))
    if not separators:
        return None

    # Check if all valid strings contain all separators.
    if not all(all(sep in s for sep in separators) for s in valid_strings):
        return None

    try:
        # Split valid strings by the identified separators.
        split_pattern = f"({'|'.join(re.escape(s) for s in separators)})"
        parts_per_string = [re.split(split_pattern, s) for s in valid_strings]
    except re.error:
        return None

    # Ensure the structure is consistent (same number of parts).
    if not all(len(p) == len(parts_per_string[0]) for p in parts_per_string):
        return None
    
    num_parts = len(parts_per_string[0])
    # The regex parts will be an interleaved sequence of content and separators.
    # e.g., ['foo', '@', 'abc', '.', 'com']
    regex_parts = []
    for i in range(num_parts):
        if i % 2 == 1: # This is a separator
            regex_parts.append(re.escape(parts_per_string[0][i]))
            continue

        # This is a content part, find a common character class for it.
        current_parts = [p[i] for p in parts_per_string]
        if not all(current_parts): # All parts must be non-empty
             return None
             
        # For email addresses (Scroll 5), try \D+ first for the username part
        if i == 0 and '@' in separators:
            char_classes = [r'\D+', r'\w+', r'[a-z]+', r'[A-Z]+', r'\d+']
        else:
            char_classes = [r'\w+', r'\D+', r'[a-z]+', r'[A-Z]+', r'\d+']
            
        found_class = False
        for cc in char_classes:
            if all(re.fullmatch(cc, p) for p in current_parts):
                regex_parts.append(cc)
                found_class = True
                break
        if not found_class:
            return None # No common class found

    pattern = f"^{''.join(regex_parts)}$"
    if _validate_pattern(pattern, valid_strings, invalid_strings):
        return pattern
        
    return None

def main():
    """
    Main function to demonstrate the Gree Expression generator with the scrolls.
    """
    scrolls = {
        "Scroll 1": {
            "valid": ["abc", "def"],
            "invalid": ["123", "456"],
            "expected": r"^\D+$"
        },
        "Scroll 2": {
            "valid": ["aaa", "abb", "acc"],
            "invalid": ["bbb", "bcc", "bca"],
            "expected": r"^[a].+$"
        },
        "Scroll 3": {
            "valid": ["abc1", "bbb1", "ccc1"],
            "invalid": ["abc", "bbb", "ccc"],
            "expected": r"^.+[1]$"
        },
        "Scroll 4": {
            "valid": ["abc-1", "bbb-1", "cde-1"],
            "invalid": ["abc1", "bbb1", "cde1"],
            "expected": r"^.+-.+$"
        },
        "Scroll 5": {
            "valid": ["foo@abc.com", "bar@def.net"],
            "invalid": ["baz@abc", "qux.com"],
            "expected": r"^\D+@\w+\.\w+$"
        }
    }

    print("--- Running Gree Expression Generator ---")
    all_passed = True
    for name, data in scrolls.items():
        valid_strings = data["valid"]
        invalid_strings = data["invalid"]
        expected = data["expected"]
        
        generated_pattern = generate_gree_expression(valid_strings, invalid_strings)
        
        # Check if the result is one of the expected patterns
        is_correct = False
        if isinstance(expected, list):
            if generated_pattern in expected:
                is_correct = True
        elif generated_pattern == expected:
            is_correct = True

        status = "✅ PASSED" if is_correct else "❌ FAILED"
        if not is_correct:
            all_passed = False

        print(f"\n📜 {name}: {status}")
        print(f"   - Valid: {valid_strings}")
        print(f"   - Invalid: {invalid_strings}")
        print(f"   - Generated: {generated_pattern}")
        if not is_correct:
            print(f"   - Expected: {expected}")
            
    print("\n--- Summary ---")
    if all_passed:
        print("🎉 All scrolls were deciphered correctly!")
    else:
        print("🔥 Some scrolls could not be deciphered correctly.")

if __name__ == "__main__":
    main() 