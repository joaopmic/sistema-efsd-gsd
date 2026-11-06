from django.urls import path

from . import views

app_name = "daily_roster"

urlpatterns = [
    path("", views.efetivo, name="efetivo"),
    path("gerar/", views.gerar, name="gerar"),
    path("<uuid:pk>/ajustar/", views.ajustar, name="ajustar"),
]
