from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class TipoPunicao(BaseModel):
    """Lista configurável de tipos de punição (o administrador cadastra os oficiais da unidade)."""

    nome = models.CharField("Nome", max_length=80)
    fundamento_padrao = models.TextField("Fundamento padrão", blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Tipo de punição"
        verbose_name_plural = "Tipos de punição"

    def __str__(self):
        return self.nome


class Punicao(BaseModel):
    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="punicoes")
    tipo = models.ForeignKey(TipoPunicao, on_delete=models.PROTECT, related_name="+", verbose_name="Tipo")
    fundamento = models.TextField("Fundamento", blank=True)
    inicio = models.DateField("Início")
    termino = models.DateField("Término")
    observacoes = models.TextField("Observações", blank=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "Punição"
        verbose_name_plural = "Punições"

    def __str__(self):
        return f"{self.tipo.nome} — {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma

    def clean(self):
        if self.inicio and self.termino and self.termino < self.inicio:
            raise ValidationError("O término não pode ser anterior ao início.")

    @property
    def situacao_texto(self):
        hoje = timezone.localdate()
        if self.termino < hoje:
            return "Cumprida"
        if self.inicio > hoje:
            return "A cumprir"
        return "Em cumprimento"
