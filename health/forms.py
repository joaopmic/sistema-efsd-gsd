from django.core.exceptions import ValidationError

from core.forms import AnexoFormMixin, BaseModelForm

from .models import Dispensa, JuntaSaude


class _PeriodoMixin:
    def clean(self):
        dados = super().clean()
        inicio, termino = dados.get("inicio"), dados.get("termino")
        if inicio and termino and termino < inicio:
            raise ValidationError("O término não pode ser anterior ao início.")
        return dados


class DispensaForm(_PeriodoMixin, AnexoFormMixin, BaseModelForm):
    class Meta:
        model = Dispensa
        fields = ["recruta", "tipo", "cid", "inicio", "termino", "observacoes"]


class JuntaSaudeForm(_PeriodoMixin, AnexoFormMixin, BaseModelForm):
    """O anexo desta tela é a ATA da junta."""

    class Meta:
        model = JuntaSaude
        fields = ["recruta", "cid", "inicio", "termino", "observacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["anexo"].label = "Anexo da ATA (PDF, JPG ou PNG, até 10 MB)"
