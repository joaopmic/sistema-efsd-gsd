from django import forms

from core.forms import AnexoFormMixin, BaseModelForm

from .models import FatoObservado


class FatoForm(AnexoFormMixin, BaseModelForm):
    class Meta:
        model = FatoObservado
        fields = ["recruta", "tipo", "data", "ocorrencia", "descricao", "medida_tomada"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "medida_tomada": forms.Textarea(attrs={"rows": 2}),
        }
