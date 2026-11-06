from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.crud import crud_urls
from core.permissions import exige

from .models import Notificacao

app_name = "notifications"


def _visiveis(request, qs):
    qs = qs.filter(Q(destinatario__isnull=True) | Q(destinatario=request.user))
    estado = request.GET.get("estado", "")
    if estado:
        return qs.filter(estado=estado)
    return qs.exclude(estado="RESOLVIDA")


@exige("registrar", escrita=True)
@require_POST
def reconhecer(request, pk):
    n = get_object_or_404(Notificacao.objects.filter(turma=request.turma), pk=pk)
    if n.estado == "ATIVA":
        n.estado = "RECONHECIDA"
        n.reconhecida_por = request.user
        n.reconhecida_em = timezone.now()
        n.save()
    messages.success(request, "Notificação reconhecida.")
    return redirect("notifications:notificacao_list")


@exige("gerir", escrita=True)
@require_POST
def resolver(request, pk):
    n = get_object_or_404(Notificacao.objects.filter(turma=request.turma), pk=pk)
    n.estado = "RESOLVIDA"
    n.resolvida_em = timezone.now()
    n.resolvida_manual = True
    n.save()
    messages.success(request, "Notificação resolvida.")
    return redirect("notifications:notificacao_list")


urlpatterns = [
    path("<uuid:pk>/reconhecer/", reconhecer, name="reconhecer"),
    path("<uuid:pk>/resolver/", resolver, name="resolver"),
]

urlpatterns += crud_urls(
    slug="", nome="notificacao", model=Notificacao, turma_lookup="turma",
    titulo="Central de notificações", singular="Notificação", incluir=("list",),
    colunas=[
        ("Prioridade", "get_prioridade_display"), ("Categoria", "categoria"), ("Mensagem", "mensagem"),
        ("Estado", "get_estado_display"), ("Criada em", "created_at"),
    ],
    filtros=[
        ("estado", None, "Estado", [("ATIVA", "Ativas"), ("RECONHECIDA", "Reconhecidas"), ("RESOLVIDA", "Resolvidas")]),
    ],
    ordenacao=("prioridade", "-created_at"), queryset_fn=_visiveis,
    acoes_extra=[
        {"label": "Reconhecer", "url": "notifications:reconhecer", "cap": "registrar", "post": True,
         "visivel": lambda n: n.estado == "ATIVA", "classe": "btn-outline-primary"},
        {"label": "Resolver", "url": "notifications:resolver", "cap": "gerir", "post": True,
         "visivel": lambda n: n.estado != "RESOLVIDA", "classe": "btn-outline-success"},
    ],
)
