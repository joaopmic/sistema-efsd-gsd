from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class FatoObservado(BaseModel):
    class Tipo(models.TextChoices):
        POSITIVO = "POS", "Positivo"
        NEGATIVO = "NEG", "Negativo"

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="fatos")
    tipo = models.CharField("Tipo", max_length=3, choices=Tipo.choices)
    data = models.DateTimeField("Data e hora", default=timezone.now)
    ocorrencia = models.CharField("Ocorrência", max_length=150)
    descricao = models.TextField("Descrição", blank=True)
    medida_tomada = models.TextField("Medida tomada", blank=True)
    observador = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.PROTECT, related_name="+", verbose_name="Observador",
    )

    class Meta:
        ordering = ["-data"]
        verbose_name = "Fato observado"
        verbose_name_plural = "Fatos observados"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.ocorrencia} — {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma
