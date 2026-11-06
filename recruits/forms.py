from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from core.fields import indice_cego
from core.forms import BaseModelForm
from core.validators import validar_cpf

from .models import DadosSaude, Recruta


class RecrutaForm(BaseModelForm):
    cpf = forms.CharField(label="CPF", required=False, max_length=14)

    class Meta:
        model = Recruta
        fields = [
            "numero", "nome_completo", "nome_guerra", "pelotao", "grupo", "saram", "cpf",
            "data_nascimento", "telefone", "email_pessoal", "nome_pai", "nome_mae",
            "telefone_responsavel", "endereco", "foto",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.cpf:
            self.initial["cpf"] = self.instance.cpf_formatado

    def clean_cpf(self):
        bruto = self.cleaned_data.get("cpf", "").strip()
        return validar_cpf(bruto) if bruto else ""

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if isinstance(foto, UploadedFile) and foto.size > 5 * 1024 * 1024:
            raise ValidationError("A foto deve ter no máximo 5 MB.")
        return foto

    def clean(self):
        dados = super().clean()
        base = Recruta.objects.exclude(pk=self.instance.pk)
        numero = dados.get("numero")
        if numero is not None and self.turma is not None:
            if base.filter(turma=self.turma, numero=numero).exists():
                self.add_error("numero", "Já existe um recruta com este número na turma.")
        saram = (dados.get("saram") or "").strip()
        if saram and base.filter(saram=saram).exists():
            self.add_error("saram", "Já existe um recruta com este SARAM.")
        cpf = dados.get("cpf")
        if cpf and base.filter(cpf_hash=indice_cego(cpf)).exists():
            self.add_error("cpf", "Já existe um recruta com este CPF.")
        return dados


class DadosSaudeForm(BaseModelForm):
    tipo_sanguineo = forms.ChoiceField(
        label="Tipo sanguíneo", required=False, choices=[("", "—")] + DadosSaude.TIPOS_SANGUINEOS
    )

    class Meta:
        model = DadosSaude
        fields = ["tipo_sanguineo", "alergias", "observacoes"]
        widgets = {
            "alergias": forms.Textarea(attrs={"rows": 3}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }
