from django.dispatch import receiver
from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

MAX_FAILS = 3
LOCK_MINUTES = 15

@receiver(user_login_failed)
def on_login_failed(sender, credentials, **kwargs):
    email = (credentials or {}).get("username") or (credentials or {}).get("email")
    if not email:
        return
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return
    # si ya está bloqueado, no sigas contando
    if user.is_locked():
        return
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    updates = ["failed_login_attempts"]
    if user.failed_login_attempts >= MAX_FAILS:
        user.locked_until = timezone.now() + timezone.timedelta(minutes=LOCK_MINUTES)
        updates.append("locked_until")
    user.save(update_fields=updates)

@receiver(user_logged_in)
def on_login_success(sender, user, request, **kwargs):
    # éxito: limpia contador y bloqueo
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts","locked_until"])
