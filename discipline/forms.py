from django import forms
from django.core.exceptions import ValidationError

from core.forms import AnexoFormMixin, BaseModelForm

from .models import Punicao, TipoPunicao


class TipoPunicaoForm(BaseModelForm):
    class Meta:
        model = TipoPunicao
        fields = ["nome", "fundamento_padrao"]
        widgets = {"fundamento_padrao": forms.Textarea(attrs={"rows": 3})}


class PunicaoForm(AnexoFormMixin, BaseModelForm):
    """O anexo desta tela é o documento da punição (opcional)."""

    class Meta:
        model = Punicao
        fields = ["recruta", "tipo", "fundamento", "inicio", "termino", "observacoes"]
        widgets = {
            "fundamento": forms.Textarea(attrs={"rows": 2}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        dados = super().clean()
        inicio, termino = dados.get("inicio"), dados.get("termino")
        if inicio and termino and termino < inicio:
            raise ValidationError("O término não pode ser anterior ao início.")
        return dados
