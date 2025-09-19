import re

def clean_phone_number(phone_number):
    """
    Clean a phone number by removing all non-digit characters.
    
    Args:
    phone_number (str): The phone number to clean.
    
    Returns:
    str: The cleaned phone number containing only digits.
    """
    # Remove all non-digit characters
    cleaned_number = re.sub(r'\D', '', phone_number)
    
    return cleaned_number
