from .models import MyUser
from django.core.exceptions import ValidationError


def user_validation(data):
    email = data['email'].strip()
    password = data['password'].strip()

    if not email or MyUser.objects.filter(email__iexact=email).exists():
        raise ValidationError('Invalid email')
    ##
    if not password or len(password) < 8:
        raise ValidationError('Invalid password, min 8 characters')

    return data

def email_validation(email):
    if not email:
        raise ValidationError('Invalid email')
    return True

def password_validation(password):
    if not password:
        raise ValidationError('Please enter a password')
    return True