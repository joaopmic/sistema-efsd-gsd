import os

from django.core.exceptions import ValidationError

EXTENSOES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
ASSINATURAS = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}
TAMANHO_MAXIMO = 10 * 1024 * 1024


def validar_arquivo(arquivo):
    """Valida extensão, tamanho e conteúdo (assinatura). Devolve o tipo MIME."""
    ext = os.path.splitext(getattr(arquivo, "name", ""))[1].lower()
    if ext not in EXTENSOES:
        raise ValidationError("Tipo de arquivo não permitido. Envie PDF, JPG ou PNG.")
    if arquivo.size > TAMANHO_MAXIMO:
        raise ValidationError("O arquivo excede 10 MB.")
    arquivo.seek(0)
    inicio = arquivo.read(16)
    arquivo.seek(0)
    if not any(inicio.startswith(a) for a in ASSINATURAS[ext]):
        raise ValidationError("O conteúdo do arquivo não corresponde à extensão informada.")
    if ext in (".jpg", ".jpeg", ".png"):
        from PIL import Image

        try:
            Image.open(arquivo).verify()
        except Exception:
            raise ValidationError("Imagem inválida ou corrompida.")
        finally:
            arquivo.seek(0)
    return EXTENSOES[ext]


def validar_cpf(valor):
    """Aceita com ou sem pontuação. Devolve só os dígitos."""
    digitos = "".join(c for c in str(valor) if c.isdigit())
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        raise ValidationError("CPF inválido.")
    for n in (9, 10):
        soma = sum(int(digitos[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(digitos[n]):
            raise ValidationError("CPF inválido.")
    return digitos
