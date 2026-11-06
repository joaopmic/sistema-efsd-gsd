from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.exceptions import TurmaArquivadaError
from core.models import Turma
from core.services import arquivar_turma
from discipline.models import Punicao, TipoPunicao
from health.models import Dispensa
from hospital.models import IdaGSAU
from recruits.models import Recruta
from situation.services import recalcular_situacao


class FluxoBasicoTest(TestCase):
    def setUp(self):
        hoje = timezone.localdate()
        self.hoje = hoje
        self.turma = Turma.objects.create(nome="T1", data_praca=hoje, data_formatura=hoje + timedelta(days=100))
        self.r = Recruta.objects.create(turma=self.turma, numero=1, nome_completo="Fulano", nome_guerra="Fulano", pelotao=1)

    def test_ida_aberta_define_situacao(self):
        IdaGSAU.objects.create(recruta=self.r, motivo="Consulta")
        self.r.refresh_from_db()
        self.assertIsNotNone(self.r.situacao_atual)

    def test_dispensa_atual(self):
        Dispensa.objects.create(recruta=self.r, tipo="FISICA", inicio=self.hoje, termino=self.hoje + timedelta(days=3))
        self.r.refresh_from_db()
        self.assertIsNotNone(self.r.situacao_atual)

    def test_soft_delete_esconde(self):
        self.r.delete()
        self.assertFalse(Recruta.objects.filter(pk=self.r.pk).exists())
        self.assertTrue(Recruta.all_objects.filter(pk=self.r.pk).exists())

    def test_turma_arquivada_bloqueia_escrita(self):
        arquivar_turma(self.turma)
        with self.assertRaises(TurmaArquivadaError):
            Recruta.objects.create(turma=self.turma, numero=2, nome_completo="B", nome_guerra="B", pelotao=1)

    def test_log_nao_pode_ser_alterado(self):
        from audit.models import LogAuditoria
        log = LogAuditoria.objects.first()
        self.assertIsNotNone(log)
        with self.assertRaises(RuntimeError):
            log.save()
