from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("conta/", include("accounts.urls")),
    path("recrutas/", include("recruits.urls")),
    path("situacoes/", include("situation.urls")),
    path("saude/", include("health.urls")),
    path("gsau/", include("hospital.urls")),
    path("fatos/", include("observations.urls")),
    path("punicoes/", include("discipline.urls")),
    path("efetivo/", include("daily_roster.urls")),
    path("passagens/", include("handover.urls")),
    path("notificacoes/", include("notifications.urls")),
    path("auditoria/", include("audit.urls")),
    path("relatorios/", include("reports.urls")),
]

handler403 = "core.views.erro_403"
handler404 = "core.views.erro_404"
handler500 = "core.views.erro_500"
