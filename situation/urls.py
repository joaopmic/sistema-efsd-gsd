from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.crud import FILTRO_GRUPO, FILTRO_PELOTAO, crud_urls
from core.permissions import exige

from .forms import CondicaoManualForm, TipoSituacaoForm
from .models import CondicaoManual, TipoSituacao

app_name = "situation"


@exige("gerir", escrita=True)
@require_POST
def encerrar_manual(request, pk):
    cond = get_object_or_404(CondicaoManual.objects.filter(recruta__turma=request.turma), pk=pk)
    cond.termino = timezone.localdate()
    cond.save()
    messages.success(request, "Situação manual encerrada.")
    return redirect("situation:manual_list")


def _pode_excluir_tipo(obj, request):
    if obj.sistema:
        return False, "Tipos de sistema não podem ser excluídos; ajuste nome, cor ou prioridade."
    return True, ""


urlpatterns = crud_urls(
    slug="manuais", nome="manual", model=CondicaoManual, form_class=CondicaoManualForm,
    titulo="Situações manuais (administrativo / atividade externa)", singular="Situação manual",
    turma_lookup="recruta__turma", cap_escrita="gerir",
    colunas=[
        ("Recruta", "recruta"), ("Situação", "tipo"), ("Motivo", "motivo"),
        ("Início", "inicio"), ("Término", "termino"),
    ],
    busca=("recruta__nome_guerra", "recruta__nome_completo", "recruta__numero", "motivo"),
    filtros=[FILTRO_PELOTAO, FILTRO_GRUPO],
    ordenacao=("-inicio",), select_related=("recruta", "tipo"),
    acoes_extra=[{
        "label": "Encerrar hoje", "url": "situation:manual_encerrar", "cap": "gerir", "post": True,
        "visivel": lambda c: c.termino is None, "classe": "btn-outline-primary",
    }],
)
urlpatterns += [path("manuais/<uuid:pk>/encerrar/", encerrar_manual, name="manual_encerrar")]

urlpatterns += crud_urls(
    slug="tipos", nome="tipo", model=TipoSituacao, form_class=TipoSituacaoForm,
    titulo="Tipos de situação", singular="Tipo de situação", cap_ver="admin", cap_escrita="admin",
    colunas=[
        ("Nome", "self", "badge"), ("Código", "codigo"), ("Prioridade", "prioridade"),
        ("Conta como presente", "conta_como_presente"),
    ],
    ordenacao=("prioridade",), incluir=("list", "update", "delete"), pode_excluir=_pode_excluir_tipo,
)
