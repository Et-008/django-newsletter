from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    subscribed_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    accountId = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return self.email


class Campaign(models.Model):
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    accountId = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return self.subject

class Newsletter(models.Model):
    accountId = models.CharField(max_length=100, blank=False)
    title = models.CharField(max_length=200)
    sections = models.JSONField(default=list, blank=True)
    html_content = models.TextField(blank=True, null=True)
    source_url = models.URLField(blank=True)
    date_generated = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

# INSERT_YOUR_CODE
class UrlData(models.Model):
    url = models.URLField(unique=True)
    json_data = models.JSONField()
    image_sources = models.JSONField(null=True, blank=True)
    image = models.ImageField(upload_to="url_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accountId = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return self.url

class UploadedImage(models.Model):
    accountId = models.CharField(max_length=100, blank=False)
    image = models.ImageField(upload_to="uploaded_images/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name


class EmailConfig(models.Model):
    PROVIDER_SMTP = "smtp"
    PROVIDER_CHOICES = [
        (PROVIDER_SMTP, "SMTP"),
        # Future: ("mailgun", "Mailgun"), ("ses", "AWS SES"), ("sendgrid", "SendGrid")
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_configs",
    )

    # Identity and selection
    name = models.CharField(max_length=80)  # human-readable, user-scoped
    from_email = models.EmailField()
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    # Transport/provider
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, default=PROVIDER_SMTP)
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255, blank=True)
    password_encrypted = models.TextField(blank=True)  # store encrypted; never expose via API
    password_set = models.BooleanField(default=False)  # indicates a secret exists

    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)

    from_name = models.CharField(max_length=120, blank=True)
    reply_to = models.EmailField(blank=True)

    last_verified_at = models.DateTimeField(null=True, blank=True)
    last_verify_error = models.TextField(blank=True)
    daily_quota = models.PositiveIntegerField(null=True, blank=True)
    per_minute_rate = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_config_name_per_user"),
            models.UniqueConstraint(fields=["user", "from_email"], name="uniq_from_email_per_user"),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def clean(self):
        if self.use_tls and self.use_ssl:
            raise ValidationError("use_tls and use_ssl cannot both be True.")
        if not (1 <= int(self.port) <= 65535):
            raise ValidationError("port must be between 1 and 65535.")
        if self.provider == self.PROVIDER_SMTP:
            missing = []
            if not self.host:
                missing.append("host")
            if not self.username:
                missing.append("username")
            if not (self.password_encrypted or self.password_set):
                missing.append("password")
            if missing:
                raise ValidationError(f"Missing required SMTP fields: {', '.join(missing)}")

    def save(self, *args, **kwargs):
        # Maintain password_set flag based on encrypted value
        self.password_set = bool(self.password_encrypted) or self.password_set
        super().save(*args, **kwargs)
        # Enforce single primary per user by unsetting others when this one is primary
        if self.is_primary:
            EmailConfig.objects.filter(user=self.user, is_primary=True).exclude(id=self.id).update(is_primary=False)

    def __str__(self):
        return f"{self.user_id}:{self.name}<{self.from_email}>"