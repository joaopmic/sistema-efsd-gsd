from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.crud import crud_urls
from core.permissions import exige, pode
from notifications.models import Notificacao
from notifications.rules import sincronizar

from .forms import PassagemForm, PendenciaForm
from .models import PassagemServico, Pendencia

app_name = "handover"


def _pre_passagem(obj, request):
    if obj.entrega_id is None:
        obj.entrega = request.user


def _pos_passagem(obj, request):
    """Vincula as pendências abertas à passagem e avisa quem recebe até confirmar."""
    if obj.pendencias.exists():
        return
    Pendencia.objects.filter(turma=obj.turma, resolvida=False, passagem__isnull=True).update(passagem=obj)
    sincronizar(
        obj.turma, "PASSAGEM", obj.pk, True,
        categoria="Passagem de serviço", prioridade=Notificacao.Prioridade.MEDIA,
        mensagem=f"{obj.entrega} passou o serviço para você em {timezone.localtime(obj.data_hora):%d/%m %H:%M}. Confirme o recebimento.",
        destinatario=obj.recebe,
    )


@exige("registrar", escrita=True)
@require_POST
def confirmar(request, pk):
    passagem = get_object_or_404(PassagemServico, pk=pk, turma=request.turma)
    if passagem.recebe_id != request.user.pk and not pode(request.user, "admin"):
        return HttpResponseForbidden("Somente quem recebe o serviço pode confirmar.")
    if passagem.confirmada_em is None:
        passagem.confirmada_em = timezone.now()
        passagem.save()
        sincronizar(passagem.turma, "PASSAGEM", passagem.pk, False)
        messages.success(request, "Recebimento confirmado.")
    return redirect("handover:passagem_list")


@exige("registrar", escrita=True)
@require_POST
def resolver_pendencia(request, pk):
    p = get_object_or_404(Pendencia, pk=pk, turma=request.turma)
    p.resolvida = True
    p.resolvida_em = timezone.now()
    p.save()
    messages.success(request, "Pendência resolvida.")
    return redirect("handover:pendencia_list")


urlpatterns = [
    path("<uuid:pk>/confirmar/", confirmar, name="confirmar"),
    path("pendencias/<uuid:pk>/resolver/", resolver_pendencia, name="pendencia_resolver"),
]

urlpatterns += crud_urls(
    slug="pendencias", nome="pendencia", model=Pendencia, form_class=PendenciaForm, turma_lookup="turma",
    titulo="Pendências", singular="Pendência", cap_escrita="registrar",
    colunas=[
        ("Descrição", "descricao"), ("Recruta", "recruta"), ("Origem", "origem_texto"),
        ("Situação", "situacao_texto"), ("Criada em", "created_at"),
    ],
    busca=("descricao", "recruta__nome_guerra"),
    filtros=[("resolvida", "resolvida", "Situação", [("False", "Abertas"), ("True", "Resolvidas")])],
    ordenacao=("resolvida", "-created_at"), select_related=("recruta",),
    acoes_extra=[{
        "label": "Resolver", "url": "handover:pendencia_resolver", "cap": "registrar", "post": True,
        "visivel": lambda p: not p.resolvida, "classe": "btn-outline-success",
    }],
)

urlpatterns += crud_urls(
    slug="", nome="passagem", model=PassagemServico, form_class=PassagemForm, turma_lookup="turma",
    titulo="Passagens de serviço", singular="Passagem de serviço", cap_escrita="gerir",
    colunas=[
        ("Data e hora", "data_hora"), ("Entrega", "entrega"), ("Recebe", "recebe"),
        ("Situação", "situacao_texto"), ("Confirmada em", "confirmada_em"),
    ],
    ordenacao=("-data_hora",), select_related=("entrega", "recebe"),
    pre_save=_pre_passagem, pos_save=_pos_passagem, incluir=("list", "create", "delete"),
    acoes_extra=[
        {"label": "Confirmar recebimento", "url": "handover:confirmar", "cap": "registrar", "post": True,
         "visivel": lambda p: p.confirmada_em is None, "classe": "btn-outline-primary"},
        {"label": "PDF", "url": "reports:passagem_pdf", "cap": "ver", "post": False, "classe": "btn-outline-secondary"},
    ],
)
