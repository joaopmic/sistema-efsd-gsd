from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.forms import BaseModelForm

from .models import IdaGSAU, RetornoGSAU


class IdaForm(BaseModelForm):
    class Meta:
        model = IdaGSAU
        fields = ["recruta", "saida", "motivo", "acompanhante", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["recruta"].disabled = True  # trocar o recruta de uma ida é refazer o registro

    def clean(self):
        dados = super().clean()
        recruta, saida = dados.get("recruta"), dados.get("saida")
        acompanhante = dados.get("acompanhante")
        if recruta and acompanhante and recruta == acompanhante:
            self.add_error("acompanhante", "O acompanhante deve ser outro recruta.")
        if saida and saida > timezone.now() + timedelta(minutes=10):
            self.add_error("saida", "A saída não pode estar no futuro.")
        if recruta and not self.instance.pk:
            aberta = IdaGSAU.objects.filter(recruta=recruta, aberta=True).first()
            if aberta:
                desde = timezone.localtime(aberta.saida).strftime("%d/%m %H:%M")
                self.add_error("recruta", f"Este recruta já está no GSAU-YS desde {desde}. Registre o retorno primeiro.")
        return dados


class RetornoForm(BaseModelForm):
    class Meta:
        model = RetornoGSAU
        fields = ["recruta", "retorno", "recebeu_dispensa", "justificativa"]
        widgets = {"justificativa": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ida_aberta = None
        if self.instance.pk:
            self.fields["recruta"].disabled = True

    def clean(self):
        dados = super().clean()
        recruta, retorno = dados.get("recruta"), dados.get("retorno")
        if self.instance.pk:
            return dados
        if retorno and retorno > timezone.now() + timedelta(minutes=10):
            self.add_error("retorno", "O retorno não pode estar no futuro.")
        if recruta:
            self.ida_aberta = IdaGSAU.objects.filter(recruta=recruta, aberta=True).first()
            if self.ida_aberta is None:
                if not (dados.get("justificativa") or "").strip():
                    self.add_error(
                        "justificativa",
                        "Este recruta não tem ida aberta. Informe a justificativa para registrar o retorno mesmo assim.",
                    )
            elif retorno and retorno < self.ida_aberta.saida:
                self.add_error("retorno", "O retorno não pode ser anterior à saída registrada.")
        return dados
