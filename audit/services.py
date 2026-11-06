from django.conf import settings

from core.middleware import get_current_user, get_request_atual

_AUTO = object()


def _ip(request):
    if request is None:
        return None
    if settings.CONFIAR_CABECALHO_PROXY:
        encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if encaminhado:
            return encaminhado.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def registrar(operacao, *, modulo="", registro_id="", registro_repr="", anterior=None, atual=None,
              justificativa="", user=_AUTO, request=None):
    """Acrescenta uma linha ao Livro de Alterações."""
    from .models import LogAuditoria

    if request is None:
        request = get_request_atual()
    if user is _AUTO:
        user = get_current_user()
    if user is not None and not getattr(user, "is_authenticated", True):
        user = None
    return LogAuditoria.objects.create(
        user=user,
        user_nome=str(user)[:200] if user is not None else "",
        operacao=operacao,
        modulo=modulo[:80],
        registro_id=str(registro_id)[:64],
        registro_repr=str(registro_repr)[:200],
        valor_anterior=anterior,
        valor_atual=atual,
        justificativa=justificativa,
        ip=_ip(request),
    )
