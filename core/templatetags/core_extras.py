from datetime import date, datetime

from django import template
from django.utils import timezone
from django.utils.formats import date_format

register = template.Library()


@register.filter
def valor(obj, caminho):
    """Lê um atributo (ou cadeia a.b.c); chama o resultado se for método."""
    if caminho in ("", "self"):
        return obj
    atual = obj
    for parte in str(caminho).split("."):
        if atual is None:
            return None
        atual = getattr(atual, parte, None)
        if callable(atual):
            atual = atual()
    return atual


@register.filter
def fmt(v):
    if v is None or v == "":
        return "—"
    if v is True:
        return "Sim"
    if v is False:
        return "Não"
    if isinstance(v, datetime):
        if timezone.is_aware(v):
            v = timezone.localtime(v)
        return date_format(v, "d/m/Y H:i")
    if isinstance(v, date):
        return date_format(v, "d/m/Y")
    return v


@register.filter
def tem_cap(caps, nome):
    return nome in caps


@register.simple_tag(takes_context=True)
def qs(context, **novos):
    """Query string atual com parâmetros trocados (para paginação)."""
    params = context["request"].GET.copy()
    for k, v in novos.items():
        params[k] = v
    return params.urlencode()


@register.filter
def zero3(n):
    try:
        return f"{int(n):03d}"
    except (TypeError, ValueError):
        return n
