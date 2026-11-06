import hashlib

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Anexo
from .validators import validar_arquivo


def salvar_anexo(alvo, arquivo, descricao=""):
    """Valida e grava um anexo ligado ao registro `alvo`."""
    mime = validar_arquivo(arquivo)
    h = hashlib.sha256()
    for pedaco in arquivo.chunks():
        h.update(pedaco)
    arquivo.seek(0)
    return Anexo.objects.create(
        content_type=ContentType.objects.get_for_model(alvo),
        object_id=alvo.pk,
        arquivo=arquivo,
        nome_original=arquivo.name[:200],
        tipo_mime=mime,
        tamanho=arquivo.size,
        sha256=h.hexdigest(),
        descricao=descricao[:200],
    )


@transaction.atomic
def arquivar_turma(turma):
    """Torna a turma somente leitura e encerra, com registro, os alertas e pendências em aberto."""
    from audit.services import registrar
    from handover.models import Pendencia
    from notifications.models import Notificacao

    agora = timezone.now()
    turma.status = "ARQUIVADA"
    turma.arquivada_em = agora
    turma.save()
    for n in Notificacao.objects.filter(turma=turma, estado__in=("ATIVA", "RECONHECIDA")):
        n.estado = "RESOLVIDA"
        n.resolvida_em = agora
        n._ignorar_arquivada = True
        n.save()
    for p in Pendencia.objects.filter(turma=turma, resolvida=False):
        p.resolvida = True
        p.resolvida_em = agora
        p._ignorar_arquivada = True
        p.save()
    registrar(
        "ARQUIVAR", modulo="core.Turma", registro_id=turma.pk, registro_repr=str(turma),
        justificativa="Turma arquivada; alertas e pendências em aberto foram encerrados.",
    )
