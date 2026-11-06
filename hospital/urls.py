from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.urls import path, reverse

from core.crud import FILTRO_GRUPO, FILTRO_PELOTAO, crud_urls
from core.permissions import exige

from .forms import IdaForm, RetornoForm
from .models import IdaGSAU, RetornoGSAU

app_name = "hospital"


@exige("ver")
def ida_list(request):
    """Painel do GSAU-YS: quem está lá agora (com o tempo fora) e o histórico de idas."""
    if request.turma is None:
        return render(request, "core/sem_turma.html")
    base = IdaGSAU.objects.filter(recruta__turma=request.turma).select_related("recruta", "acompanhante")
    agora = base.filter(aberta=True).order_by("saida")
    q = request.GET.get("q", "").strip()
    historico = base.filter(aberta=False)
    if q:
        cond = Q(recruta__nome_guerra__icontains=q) | Q(recruta__nome_completo__icontains=q) | Q(motivo__icontains=q)
        if q.isdigit():
            cond |= Q(recruta__numero=int(q))
        historico = historico.filter(cond)
    return render(request, "hospital/ida_list.html", {
        "agora": agora, "historico": historico[:60], "q": q,
        "editavel": request.turma.editavel,
    })


def _pre_save_retorno(obj, request):
    obj._novo = obj._state.adding
    if obj._novo:
        obj.ida = IdaGSAU.objects.filter(recruta=obj.recruta, aberta=True).first()


def _pos_save_retorno(obj, request):
    ida = obj.ida
    if ida is not None:
        if ida.aberta or ida.retornou_em != obj.retorno:
            ida.aberta = False
            ida.retornou_em = obj.retorno
            ida.save()
    elif getattr(obj, "_novo", False):
        from handover.models import Pendencia

        Pendencia.objects.create(
            turma=obj.recruta.turma, recruta=obj.recruta, origem="retorno_sem_ida",
            descricao=f"Retorno do GSAU-YS registrado sem ida aberta. Justificativa: {obj.justificativa}"[:500],
        )


def _sucesso_retorno(request, obj):
    if obj.recebeu_dispensa and getattr(obj, "_novo", False):
        messages.info(request, "O recruta recebeu dispensa: registre-a agora.")
        return reverse("health:dispensa_create") + f"?recruta={obj.recruta_id}"
    return reverse("hospital:ida_list")


BUSCA = ("recruta__nome_guerra", "recruta__nome_completo", "recruta__numero")

urlpatterns = [path("", ida_list, name="ida_list")]

urlpatterns += crud_urls(
    slug="idas", nome="ida", model=IdaGSAU, form_class=IdaForm, turma_lookup="recruta__turma",
    titulo="Idas ao GSAU-YS", singular="Ida ao GSAU-YS", cap_escrita="registrar",
    incluir=("create", "update", "delete"),
    sucesso_fn=lambda request, obj: reverse("hospital:ida_list"),
)

urlpatterns += crud_urls(
    slug="retornos", nome="retorno", model=RetornoGSAU, form_class=RetornoForm, turma_lookup="recruta__turma",
    titulo="Retornos do GSAU-YS", singular="Retorno do GSAU-YS", cap_escrita="registrar",
    colunas=[("Recruta", "recruta"), ("Retorno", "retorno"), ("Recebeu dispensa", "recebeu_dispensa"), ("Justificativa", "justificativa")],
    busca=BUSCA, filtros=[FILTRO_PELOTAO, FILTRO_GRUPO], ordenacao=("-retorno",), select_related=("recruta",),
    pre_save=_pre_save_retorno, pos_save=_pos_save_retorno, sucesso_fn=_sucesso_retorno,
)
