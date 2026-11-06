from django.urls import path, reverse

from core.crud import crud_urls

from . import views
from .forms import RecrutaForm
from .models import Recruta

app_name = "recruits"

urlpatterns = [
    path("", views.lista, name="recruta_list"),
    path("<uuid:pk>/", views.ficha, name="ficha"),
    path("<uuid:pk>/foto/", views.foto, name="foto"),
    path("<uuid:pk>/saude/editar/", views.saude_editar, name="saude_editar"),
    path("<uuid:pk>/documentos/", views.checklist_salvar, name="checklist_salvar"),
]

urlpatterns += crud_urls(
    slug="", nome="recruta", model=Recruta, form_class=RecrutaForm, turma_lookup="turma",
    titulo="Recrutas", singular="Recruta", cap_escrita="gerir",
    incluir=("create", "update", "delete"),
    sucesso_fn=lambda request, obj: obj.get_absolute_url() if not obj.deleted_at else reverse("recruits:recruta_list"),
)
