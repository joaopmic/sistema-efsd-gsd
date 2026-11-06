from core.crud import FILTRO_GRUPO, FILTRO_PELOTAO, crud_urls

from .forms import FatoForm
from .models import FatoObservado

app_name = "observations"


def _observador(obj, request):
    if obj.observador_id is None:
        obj.observador = request.user


urlpatterns = crud_urls(
    slug="", nome="fato", model=FatoObservado, form_class=FatoForm, turma_lookup="recruta__turma",
    titulo="Fatos observados", singular="Fato observado", cap_escrita="registrar",
    colunas=[
        ("Recruta", "recruta"), ("Tipo", "get_tipo_display"), ("Data", "data"),
        ("Ocorrência", "ocorrencia"), ("Observador", "observador"),
    ],
    busca=("recruta__nome_guerra", "recruta__nome_completo", "recruta__numero", "ocorrencia", "descricao"),
    filtros=[FILTRO_PELOTAO, FILTRO_GRUPO, ("tipo", "tipo", "Tipo", FatoObservado.Tipo.choices)],
    ordenacao=("-data",), select_related=("recruta", "observador"), pre_save=_observador,
)
