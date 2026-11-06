from django.utils import timezone

from core.crud import FILTRO_GRUPO, FILTRO_PELOTAO, crud_urls

from .forms import PunicaoForm, TipoPunicaoForm
from .models import Punicao, TipoPunicao

app_name = "discipline"


def _vigentes(request, qs):
    if request.GET.get("vigentes") == "1":
        hoje = timezone.localdate()
        qs = qs.filter(inicio__lte=hoje, termino__gte=hoje)
    return qs


urlpatterns = crud_urls(
    slug="", nome="punicao", model=Punicao, form_class=PunicaoForm, turma_lookup="recruta__turma",
    titulo="Punições", singular="Punição", cap_escrita="gerir",
    colunas=[
        ("Recruta", "recruta"), ("Tipo", "tipo"), ("Início", "inicio"),
        ("Término", "termino"), ("Situação", "situacao_texto"),
    ],
    busca=("recruta__nome_guerra", "recruta__nome_completo", "recruta__numero", "fundamento"),
    filtros=[FILTRO_PELOTAO, FILTRO_GRUPO, ("vigentes", None, "Vigência", [("1", "Somente em cumprimento")])],
    ordenacao=("-inicio",), select_related=("recruta", "tipo"), queryset_fn=_vigentes,
)

urlpatterns += crud_urls(
    slug="tipos", nome="tipo", model=TipoPunicao, form_class=TipoPunicaoForm,
    titulo="Tipos de punição", singular="Tipo de punição", cap_ver="admin", cap_escrita="admin",
    colunas=[("Nome", "nome"), ("Fundamento padrão", "fundamento_padrao")],
    ordenacao=("nome",),
)
