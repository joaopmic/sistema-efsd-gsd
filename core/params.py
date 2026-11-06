"""Parâmetros ajustáveis pelo administrador (tabela Parametro), com valores padrão."""

PADROES = {
    "limiar_fatos": ("5", "Total de fatos observados (positivos e negativos) que gera alerta"),
    "antecedencia_junta_dias": ("15", "Dias antes do término da Junta de Saúde para alertar nova junta"),
    "horas_alerta_gsau": ("6", "Horas fora no GSAU-YS que geram alerta"),
    "dias_aviso_dispensa": ("2", "Dias antes do término de uma dispensa para avisar"),
    "dias_aviso_punicao": ("2", "Dias antes do término de uma punição para avisar"),
    "modo_demo": ("0", "1 exibe a faixa DADOS DE DEMONSTRAÇÃO em todas as telas"),
}
CHAVES_NUMERICAS = {c for c in PADROES if c != "modo_demo"}


def get_param(chave):
    from .models import Parametro

    p = Parametro.objects.filter(chave=chave).first()
    if p is not None:
        return p.valor
    return PADROES.get(chave, ("", ""))[0]


def get_int(chave):
    try:
        return int(get_param(chave))
    except (TypeError, ValueError):
        return int(PADROES[chave][0])
