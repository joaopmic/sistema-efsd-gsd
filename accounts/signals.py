from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_login_failed, dispatch_uid="accounts_login_falhou")
def login_falhou(sender, credentials, request=None, **kwargs):
    from audit.services import registrar

    User = get_user_model()
    username = (credentials or {}).get("username", "") or ""
    usuario = User.objects.filter(username__iexact=username).first() if username else None
    if usuario is not None:
        falhas = usuario.falhas_login + 1
        bloqueado_ate = usuario.bloqueado_ate
        if falhas >= settings.LOGIN_MAX_FALHAS:
            bloqueado_ate = timezone.now() + timedelta(minutes=settings.LOGIN_BLOQUEIO_MINUTOS)
            falhas = 0
        # update() para não gerar ruído no Livro de Alterações a cada tentativa
        User.objects.filter(pk=usuario.pk).update(falhas_login=falhas, bloqueado_ate=bloqueado_ate)
    registrar("LOGIN_FALHA", modulo="accounts.User", registro_repr=username[:150], user=None, request=request)


@receiver(user_logged_in, dispatch_uid="accounts_login_ok")
def login_ok(sender, request, user, **kwargs):
    from audit.services import registrar

    get_user_model().objects.filter(pk=user.pk).update(falhas_login=0, bloqueado_ate=None)
    registrar("LOGIN", modulo="accounts.User", registro_id=user.pk, registro_repr=str(user), user=user, request=request)


@receiver(user_logged_out, dispatch_uid="accounts_logout")
def logout_ok(sender, request, user, **kwargs):
    from audit.services import registrar

    if user is not None:
        registrar("LOGOUT", modulo="accounts.User", registro_id=user.pk, registro_repr=str(user), user=user, request=request)
