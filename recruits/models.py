from django.db import models
from django.db.models import Q
from django.urls import reverse

from core.fields import EncryptedTextField, indice_cego
from core.models import BaseModel
from core.storage import get_private_storage


def foto_upload_para(instance, filename):
    import os
    import uuid

    return f"fotos/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


class Recruta(BaseModel):
    PELOTOES = [(1, "1º Pelotão"), (2, "2º Pelotão")]

    turma = models.ForeignKey("core.Turma", on_delete=models.PROTECT, related_name="recrutas", editable=False)
    numero = models.PositiveSmallIntegerField("Número")
    nome_completo = models.CharField("Nome completo", max_length=150)
    nome_guerra = models.CharField("Nome de guerra", max_length=60, db_index=True)
    pelotao = models.PositiveSmallIntegerField("Pelotão", choices=PELOTOES)
    grupo = models.CharField("Grupo", max_length=20, blank=True)
    saram = models.CharField("SARAM", max_length=20, blank=True)
    cpf = EncryptedTextField("CPF", blank=True)
    cpf_hash = models.CharField(max_length=64, blank=True, editable=False)
    data_nascimento = models.DateField("Data de nascimento", null=True, blank=True)
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    email_pessoal = models.EmailField("E-mail", blank=True)
    nome_pai = models.CharField("Nome do pai", max_length=150, blank=True)
    nome_mae = models.CharField("Nome da mãe", max_length=150, blank=True)
    telefone_responsavel = models.CharField("Telefone do responsável", max_length=30, blank=True)
    endereco = models.TextField("Endereço", blank=True)
    foto = models.ImageField("Foto 3x4", upload_to=foto_upload_para, storage=get_private_storage, blank=True, null=True)

    # Situação principal (calculada pelo app situation; não editável à mão)
    situacao_atual = models.ForeignKey(
        "situation.TipoSituacao", null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    situacao_motivo = models.CharField(max_length=500, blank=True, editable=False)

    # Filhos que acompanham a exclusão lógica do recruta
    FILHOS = ("dispensas", "juntas", "idas", "retornos", "fatos", "punicoes", "condicoes_manuais", "checklist")

    class Meta:
        ordering = ["numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["turma", "numero"], condition=Q(deleted_at__isnull=True), name="recruits_numero_unico_turma"
            ),
            models.UniqueConstraint(
                fields=["saram"], condition=Q(deleted_at__isnull=True) & ~Q(saram=""), name="recruits_saram_unico"
            ),
            models.UniqueConstraint(
                fields=["cpf_hash"], condition=Q(deleted_at__isnull=True) & ~Q(cpf_hash=""), name="recruits_cpf_unico"
            ),
        ]

    def __str__(self):
        return f"{self.numero:03d} · {self.nome_guerra} — {self.nome_completo}"

    @property
    def rotulo_curto(self):
        return f"{self.numero:03d} {self.nome_guerra}"

    def _turma_do_registro(self):
        return self.turma

    @property
    def cpf_formatado(self):
        d = self.cpf or ""
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else d

    def get_absolute_url(self):
        return reverse("recruits:ficha", args=[self.pk])

    def save(self, *args, **kwargs):
        self.cpf_hash = indice_cego(self.cpf) if self.cpf else ""
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        for nome in self.FILHOS:
            gerenciador = getattr(self, nome, None)
            if gerenciador is not None:
                for filho in gerenciador.all():
                    filho.delete()
        saude = DadosSaude.objects.filter(recruta=self).first()
        if saude is not None:
            saude.delete()
        return super().delete(using=using, keep_parents=keep_parents)


class DadosSaude(BaseModel):
    """Seção protegida de saúde. Todos os campos ficam criptografados; cada consulta é registrada."""

    TIPOS_SANGUINEOS = [(t, t) for t in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")]

    recruta = models.OneToOneField(Recruta, on_delete=models.PROTECT, related_name="saude")
    tipo_sanguineo = EncryptedTextField("Tipo sanguíneo", blank=True)
    alergias = EncryptedTextField("Alergias", blank=True)
    observacoes = EncryptedTextField("Observações de saúde", blank=True)

    def __str__(self):
        return f"Saúde de {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma


class ChecklistDocumento(BaseModel):
    DOCUMENTOS = [
        ("RG", "RG"),
        ("CPF", "CPF"),
        ("COMP_RESIDENCIA", "Comprovante de residência"),
        ("CERTIDAO", "Certidão (nascimento/casamento)"),
        ("EXTRATO", "Extrato"),
        ("PORTAL", "Cadastro no portal do militar"),
    ]

    recruta = models.ForeignKey(Recruta, on_delete=models.PROTECT, related_name="checklist")
    documento = models.CharField(max_length=20, choices=DOCUMENTOS)
    entregue = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recruta", "documento"], condition=Q(deleted_at__isnull=True),
                name="recruits_checklist_unico",
            )
        ]

    def __str__(self):
        return f"{self.get_documento_display()} — {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma
