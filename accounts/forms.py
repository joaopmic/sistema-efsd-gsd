from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.forms import BaseModelForm

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={"autofocus": True, "class": "form-control"}))
    password = forms.CharField(label="Senha", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean(self):
        username = self.cleaned_data.get("username")
        if username:
            usuario = User.objects.filter(username__iexact=username).first()
            if usuario is not None and usuario.esta_bloqueado():
                raise ValidationError(
                    "Conta temporariamente bloqueada por excesso de tentativas. Tente novamente mais tarde.",
                    code="bloqueado",
                )
        return super().clean()


class UsuarioForm(BaseModelForm):
    password1 = forms.CharField(label="Senha", required=False, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirmar senha", required=False, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "nome_guerra", "email", "graduacao", "administrador", "is_active"]
        labels = {"first_name": "Nome", "last_name": "Sobrenome", "is_active": "Ativo"}

    def clean(self):
        dados = super().clean()
        p1, p2 = dados.get("password1"), dados.get("password2")
        if self.instance.pk is None and not p1:
            self.add_error("password1", "Informe a senha do novo usuário.")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "As senhas não conferem.")
            else:
                try:
                    validate_password(p1, self.instance)
                except ValidationError as erro:
                    self.add_error("password1", erro)
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario
