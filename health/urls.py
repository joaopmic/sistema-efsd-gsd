from django.utils import timezone

from core.crud import FILTRO_GRUPO, FILTRO_PELOTAO, crud_urls

from .forms import DispensaForm, JuntaSaudeForm
from .models import Dispensa, JuntaSaude

app_name = "health"

OPCOES_VIGENTE = [("1", "Somente vigentes")]


def _filtrar_vigentes(request, qs):
    if request.GET.get("vigentes") == "1":
        hoje = timezone.localdate()
        qs = qs.filter(inicio__lte=hoje, termino__gte=hoje)
    return qs


BUSCA = ("recruta__nome_guerra", "recruta__nome_completo", "recruta__numero", "cid")

urlpatterns = crud_urls(
    slug="dispensas", nome="dispensa", model=Dispensa, form_class=DispensaForm,
    titulo="Dispensas médicas", singular="Dispensa", turma_lookup="recruta__turma", cap_escrita="gerir",
    colunas=[
        ("Recruta", "recruta"), ("Tipo", "get_tipo_display"), ("CID", "cid"),
        ("Início", "inicio"), ("Término", "termino"), ("Dias", "dias"), ("Situação", "situacao_texto"),
    ],
    busca=BUSCA,
    filtros=[
        FILTRO_PELOTAO, FILTRO_GRUPO,
        ("tipo", "tipo", "Tipo", Dispensa.Tipo.choices),
        ("vigentes", None, "Vigência", OPCOES_VIGENTE),
    ],
    ordenacao=("-inicio",), select_related=("recruta",), queryset_fn=_filtrar_vigentes,
)

urlpatterns += crud_urls(
    slug="juntas", nome="junta", model=JuntaSaude, form_class=JuntaSaudeForm,
    titulo="Juntas de Saúde", singular="Junta de Saúde", turma_lookup="recruta__turma", cap_escrita="gerir",
    colunas=[
        ("Recruta", "recruta"), ("CID", "cid"), ("Início", "inicio"),
        ("Término", "termino"), ("Situação", "situacao_texto"),
    ],
    busca=BUSCA,
    filtros=[FILTRO_PELOTAO, FILTRO_GRUPO, ("vigentes", None, "Vigência", OPCOES_VIGENTE)],
    ordenacao=("-inicio",), select_related=("recruta",), queryset_fn=_filtrar_vigentes,
)
