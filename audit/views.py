import json

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from core.permissions import exige

from .models import LogAuditoria


@exige("gerir")
def lista(request):
    qs = LogAuditoria.objects.all()
    operacao = request.GET.get("operacao", "")
    modulo = request.GET.get("modulo", "").strip()
    q = request.GET.get("q", "").strip()
    if operacao:
        qs = qs.filter(operacao=operacao)
    if modulo:
        qs = qs.filter(modulo__icontains=modulo)
    if q:
        qs = qs.filter(Q(registro_repr__icontains=q) | Q(user_nome__icontains=q) | Q(justificativa__icontains=q))
    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    itens = list(page.object_list)
    for item in itens:
        item.resumo = _resumo(item)
    return render(request, "audit/log_list.html", {
        "page": page, "itens": itens, "operacao": operacao, "modulo": modulo, "q": q,
        "operacoes": LogAuditoria.Operacao.choices,
    })


def _resumo(item):
    """Lista só os campos que mudaram (ou os valores, em criações)."""
    antes, atual = item.valor_anterior or {}, item.valor_atual or {}
    if item.operacao == "ALTERAR":
        mudancas = [f"{k}: {antes.get(k)!s} → {atual.get(k)!s}" for k in atual if antes.get(k) != atual.get(k)]
        return "; ".join(mudancas)[:600]
    if item.operacao == "CRIAR":
        return json.dumps(atual, ensure_ascii=False)[:300]
    return item.justificativa
