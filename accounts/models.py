from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Graduacao(models.TextChoices):
        TEN = "TEN", "Tenente"
        SGT = "SGT", "Sargento"
        CB = "CB", "Cabo"
        SD = "SD", "Soldado"

    graduacao = models.CharField("Graduação", max_length=3, choices=Graduacao.choices, default=Graduacao.SD)
    nome_guerra = models.CharField("Nome de guerra", max_length=60, blank=True)
    administrador = models.BooleanField("Administrador do sistema", default=False)
    falhas_login = models.PositiveSmallIntegerField(default=0, editable=False)
    bloqueado_ate = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    # Campos que não entram no Livro de Alterações
    audit_excluir = ("password", "last_login", "falhas_login", "bloqueado_ate")

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        nome = self.nome_guerra or self.get_full_name() or self.username
        return f"{self.get_graduacao_display()} {nome}"

    def esta_bloqueado(self):
        return self.bloqueado_ate is not None and self.bloqueado_ate > timezone.now()

    def delete(self, using=None, keep_parents=False):
        """'Excluir' desativa o usuário e preserva todo o histórico dele."""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()
        return 1, {self._meta.label: 1}
