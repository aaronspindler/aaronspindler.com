import re


def clean_phone_number(phone_number):
    cleaned_number = re.sub(r'\D', '', phone_number)
    
    return cleaned_number
