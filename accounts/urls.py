from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from core.crud import crud_urls

from .forms import LoginForm, UsuarioForm
from .models import User

app_name = "accounts"

urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(
        authentication_form=LoginForm, template_name="registration/login.html",
        redirect_authenticated_user=True), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("senha/alterar/", auth_views.PasswordChangeView.as_view(
        success_url=reverse_lazy("accounts:password_change_done")), name="password_change"),
    path("senha/alterada/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("senha/recuperar/", auth_views.PasswordResetView.as_view(
        success_url=reverse_lazy("accounts:password_reset_done"),
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt"), name="password_reset"),
    path("senha/recuperar/enviado/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("senha/redefinir/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        success_url=reverse_lazy("accounts:password_reset_complete")), name="password_reset_confirm"),
    path("senha/redefinida/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]


def _pode_excluir(obj, request):
    if obj.pk == request.user.pk:
        return False, "Você não pode excluir o próprio usuário."
    return True, ""


urlpatterns += crud_urls(
    slug="usuarios", nome="usuario", model=User, form_class=UsuarioForm, pk_conv="int",
    titulo="Usuários", singular="Usuário", cap_ver="admin", cap_escrita="admin",
    colunas=[
        ("Usuário", "username"), ("Graduação", "get_graduacao_display"), ("Nome de guerra", "nome_guerra"),
        ("Administrador", "administrador"), ("Ativo", "is_active"),
    ],
    busca=("username", "nome_guerra", "first_name", "last_name"),
    ordenacao=("username",),
    queryset_fn=lambda request, qs: qs.filter(deleted_at__isnull=True),
    pode_excluir=_pode_excluir,
)
