from django import forms
from django.core.exceptions import ValidationError

from .models import Parametro, Turma
from .params import CHAVES_NUMERICAS
from .services import salvar_anexo
from .validators import validar_arquivo


class BaseModelForm(forms.ModelForm):
    """Formulário base: estilo Bootstrap, campos de data/hora nativos e seleção de recruta
    limitada à turma ativa. Recebe `turma` e `user` da view."""

    def __init__(self, *args, turma=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.turma = turma
        self.user = user
        if turma is not None:
            from recruits.models import Recruta

            for nome in ("recruta", "acompanhante"):
                if nome in self.fields:
                    self.fields[nome].queryset = Recruta.objects.filter(turma=turma).order_by("numero")
                    self.fields[nome].widget.attrs["class"] = "select-busca"
        self._estilizar()

    def _estilizar(self):
        for nome, campo in self.fields.items():
            if isinstance(campo, forms.DateTimeField):
                campo.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
                campo.widget.is_required = campo.required
                campo.input_formats = [
                    "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M",
                ]
            elif isinstance(campo, forms.DateField):
                campo.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
                campo.widget.is_required = campo.required
                campo.input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
            w = campo.widget
            if isinstance(w, forms.CheckboxInput):
                classe = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                classe = "form-select"
            else:
                classe = "form-control"
            w.attrs["class"] = (w.attrs.get("class", "") + " " + classe).strip()


class AnexoFormMixin:
    """Acrescenta um anexo opcional (PDF/JPG/PNG) ao formulário. A view chama depois_de_salvar()."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["anexo"] = forms.FileField(required=False, label="Anexo (PDF, JPG ou PNG, até 10 MB)")
        self.fields["anexo"].widget.attrs["class"] = "form-control"

    def clean_anexo(self):
        arquivo = self.cleaned_data.get("anexo")
        if arquivo:
            validar_arquivo(arquivo)
        return arquivo

    def depois_de_salvar(self, obj):
        arquivo = self.cleaned_data.get("anexo")
        if arquivo:
            salvar_anexo(obj, arquivo)


class TurmaForm(BaseModelForm):
    class Meta:
        model = Turma
        fields = ["nome", "data_praca", "data_formatura"]

    def clean(self):
        dados = super().clean()
        praca, formatura = dados.get("data_praca"), dados.get("data_formatura")
        if praca and formatura and formatura <= praca:
            raise ValidationError("A data de formatura deve ser posterior à data de praça.")
        return dados


class ParametroForm(BaseModelForm):
    class Meta:
        model = Parametro
        fields = ["valor"]

    def clean_valor(self):
        valor = self.cleaned_data["valor"].strip()
        if self.instance.chave in CHAVES_NUMERICAS and not valor.isdigit():
            raise ValidationError("Informe um número inteiro.")
        return valor
