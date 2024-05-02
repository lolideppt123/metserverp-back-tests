from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin

class MyUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **other_fields):
        # Creates and saves a normaluser using credentials below
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **other_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_staffuser(self, email, first_name, last_name, password=None, **other_fields):
        # Creates and saves a staffuser using credentials below
        other_fields.setdefault('is_staff', True)

        user = self.create_user(
            email,
            first_name,
            last_name,
            password=password,
            **other_fields
        )

        return user
    
    def create_adminuser(self, email, first_name, last_name, password=None, **other_fields):
        # Creates and saves a staffuser using credentials below
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_admin', True)

        user = self.create_user(
            email,
            first_name,
            last_name,
            password=password,
            **other_fields
        )

        return user

    def create_superuser(self, email, first_name, last_name, password=None, **other_fields):
        # Creates and saves a superuser using credentials below
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_admin', True)
        other_fields.setdefault('is_superuser', True)

        user = self.create_user(
            email,
            first_name,
            last_name,
            password=password,
            **other_fields
        )

        return user


class MyUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name="email address",max_length=150,unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin  = models.BooleanField(default=False)
    is_superuser  = models.BooleanField(default=False) 

    objects = MyUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name_plural = 'Users'

    def __str__(self):
        return str(self.email)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_first_name(self):
        return str(self.first_name)

    # def has_perm(self, perm, obj=None):
    #     "Does the user have a specific permission?"
    #     # Simplest possible answer: Yes, always
    #     return True

    # def has_module_perms(self, app_label):
    #     "Does the user have permissions to view the app `app_label`?"
    #     # Simplest possible answer: Yes, always
    #     return True
    
    
