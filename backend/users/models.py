from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    User model. Supports both:
    - Shopify OAuth login (no password, auto-created)
    - Manual registration (email + password)
    """
    ROLE_OWNER   = 'owner'
    ROLE_MANAGER = 'manager'
    ROLE_ANALYST = 'analyst'
    ROLE_CHOICES = [
        (ROLE_OWNER,   'Owner'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_ANALYST, 'Analyst'),
    ]

    email      = models.EmailField(unique=True, db_index=True)
    full_name  = models.CharField(max_length=255, blank=True)
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_OWNER)
    # Shopify OAuth users are marked here
    shopify_auth = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
