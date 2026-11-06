from django.urls import path

from . import views
from .crud import crud_urls
from .forms import ParametroForm, TurmaForm
from .models import Parametro, Turma

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("turma/selecionar/", views.selecionar_turma, name="selecionar_turma"),
    path("administracao/", views.admin_index, name="admin_index"),
    path("anexos/<uuid:pk>/", views.anexo_download, name="anexo"),
    path("administracao/turmas/<uuid:pk>/arquivar/", views.turma_arquivar, name="turma_arquivar"),
]

urlpatterns += crud_urls(
    slug="administracao/turmas", nome="turma", model=Turma, form_class=TurmaForm,
    titulo="Turmas", singular="Turma", cap_ver="admin", cap_escrita="admin",
    colunas=[
        ("Nome", "nome"), ("Praça", "data_praca"), ("Formatura", "data_formatura"),
        ("Situação", "get_status_display"),
    ],
    ordenacao=("-data_praca",),
    acoes_extra=[{
        "label": "Arquivar", "url": "core:turma_arquivar", "cap": "admin", "post": True,
        "classe": "btn-outline-danger",
        "visivel": lambda t: t.editavel,
    }],
)
urlpatterns += crud_urls(
    slug="administracao/parametros", nome="parametro", model=Parametro, form_class=ParametroForm,
    titulo="Parâmetros do sistema", singular="Parâmetro", cap_ver="admin", cap_escrita="admin",
    colunas=[("Parâmetro", "chave"), ("Valor", "valor"), ("Descrição", "descricao")],
    ordenacao=("chave",), incluir=("list", "update"),
)
