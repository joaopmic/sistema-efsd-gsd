from django import forms
from django.contrib.auth import get_user_model

from core.forms import BaseModelForm

from .models import PassagemServico, Pendencia


class PassagemForm(BaseModelForm):
    class Meta:
        model = PassagemServico
        fields = ["recebe", "data_hora", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = get_user_model().objects.filter(is_active=True, deleted_at__isnull=True)
        if self.user is not None:
            usuarios = usuarios.exclude(pk=self.user.pk)
        self.fields["recebe"].queryset = usuarios


class PendenciaForm(BaseModelForm):
    class Meta:
        model = Pendencia
        fields = ["recruta", "descricao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recruta"].required = False
