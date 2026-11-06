from django import forms
from django.core.exceptions import ValidationError

from core.forms import BaseModelForm

from .models import CondicaoManual, TipoSituacao


class TipoSituacaoForm(BaseModelForm):
    class Meta:
        model = TipoSituacao
        fields = ["nome", "cor", "conta_como_presente", "prioridade"]
        widgets = {"cor": forms.TextInput(attrs={"type": "color"})}


class CondicaoManualForm(BaseModelForm):
    class Meta:
        model = CondicaoManual
        fields = ["recruta", "tipo", "motivo", "inicio", "termino"]

    def clean(self):
        dados = super().clean()
        inicio, termino = dados.get("inicio"), dados.get("termino")
        if inicio and termino and termino < inicio:
            raise ValidationError("O término não pode ser anterior ao início.")
        return dados
