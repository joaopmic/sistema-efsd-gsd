import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .exceptions import TurmaArquivadaError
from .middleware import get_current_user
from .storage import get_private_storage


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        total = 0
        for obj in list(self):
            obj.delete()
            total += 1
        return total, {self.model._meta.label: total}


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager padrão: esconde registros com exclusão lógica."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """Base de todos os modelos: chave UUID, trilha de criação/alteração e exclusão lógica.
    Registros de turma arquivada não podem ser alterados."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def _turma_do_registro(self):
        """Sobrescrito pelos modelos ligados a uma turma."""
        return None

    def save(self, *args, **kwargs):
        if not getattr(self, "_ignorar_arquivada", False):
            turma = self._turma_do_registro()
            if turma is not None and turma.status == "ARQUIVADA":
                raise TurmaArquivadaError(
                    f"A turma {turma.nome} está arquivada e é somente leitura."
                )
        user = get_current_user()
        if user is not None:
            if self._state.adding and self.created_by_id is None:
                self.created_by = user
            self.updated_by = user
            campos = kwargs.get("update_fields")
            if campos is not None:
                kwargs["update_fields"] = list(campos) + ["updated_by", "updated_at"]
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Exclusão lógica: nada é apagado do banco."""
        self.deleted_at = timezone.now()
        self.save()
        return 1, {self._meta.label: 1}

    @property
    def anexos(self):
        ct = ContentType.objects.get_for_model(self)
        return Anexo.objects.filter(content_type=ct, object_id=self.pk)


class Turma(BaseModel):
    class Status(models.TextChoices):
        FORMACAO = "FORMACAO", "Em formação"
        ARQUIVADA = "ARQUIVADA", "Arquivada"

    nome = models.CharField("Nome", max_length=80)
    data_praca = models.DateField("Data de praça")
    data_formatura = models.DateField("Data de formatura")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.FORMACAO, editable=False)
    arquivada_em = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-data_praca"]
        constraints = [
            models.UniqueConstraint(
                fields=["nome"], condition=Q(deleted_at__isnull=True), name="core_turma_nome_unico"
            )
        ]

    def __str__(self):
        return self.nome

    @property
    def editavel(self):
        return self.status == self.Status.FORMACAO


class Parametro(BaseModel):
    chave = models.CharField(max_length=60)
    valor = models.CharField(max_length=200)
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["chave"]
        constraints = [
            models.UniqueConstraint(
                fields=["chave"], condition=Q(deleted_at__isnull=True), name="core_parametro_chave_unica"
            )
        ]

    def __str__(self):
        return f"{self.chave} = {self.valor}"


def anexo_upload_para(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"anexos/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class Anexo(BaseModel):
    """Arquivo ligado a qualquer registro (vínculo genérico). Guardado em pasta privada."""

    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.UUIDField()
    alvo = GenericForeignKey("content_type", "object_id")
    arquivo = models.FileField(upload_to=anexo_upload_para, storage=get_private_storage, max_length=255)
    nome_original = models.CharField(max_length=200)
    tipo_mime = models.CharField(max_length=60)
    tamanho = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return self.nome_original
