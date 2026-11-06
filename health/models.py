from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Dispensa(BaseModel):
    class Tipo(models.TextChoices):
        FISICA = "FISICA", "Dispensa de atividade física"
        TOTAL = "TOTAL", "Dispensa total de expediente"

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="dispensas")
    tipo = models.CharField("Tipo", max_length=10, choices=Tipo.choices)
    cid = models.CharField("CID", max_length=20, blank=True)
    inicio = models.DateField("Início")
    termino = models.DateField("Término")
    observacoes = models.TextField("Observações", blank=True)

    class Meta:
        ordering = ["-inicio"]
        indexes = [models.Index(fields=["recruta", "inicio", "termino"])]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma

    def clean(self):
        if self.inicio and self.termino and self.termino < self.inicio:
            raise ValidationError("O término não pode ser anterior ao início.")

    @property
    def dias(self):
        return (self.termino - self.inicio).days + 1

    @property
    def situacao_texto(self):
        hoje = timezone.localdate()
        if self.termino < hoje:
            return "Encerrada"
        if self.inicio > hoje:
            return "Futura"
        return "Vigente"


class JuntaSaude(BaseModel):
    """Junta de Saúde. As anteriores são mantidas: uma nova junta é um novo registro."""

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="juntas")
    cid = models.CharField("CID", max_length=20, blank=True)
    inicio = models.DateField("Início")
    termino = models.DateField("Término")
    observacoes = models.TextField("Observações", blank=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "Junta de Saúde"
        verbose_name_plural = "Juntas de Saúde"

    def __str__(self):
        return f"Junta de Saúde — {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma

    def clean(self):
        if self.inicio and self.termino and self.termino < self.inicio:
            raise ValidationError("O término não pode ser anterior ao início.")

    @property
    def situacao_texto(self):
        hoje = timezone.localdate()
        if self.termino < hoje:
            return "Encerrada"
        if self.inicio > hoje:
            return "Futura"
        return "Vigente"
