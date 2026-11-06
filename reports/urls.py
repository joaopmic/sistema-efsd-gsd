from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("ficha/<uuid:pk>/", views.ficha, name="ficha"),
    path("passagem/<uuid:pk>/pdf/", views.passagem_pdf, name="passagem_pdf"),
    path("gerar/<slug:chave>/", views.relatorio, name="relatorio"),
]
