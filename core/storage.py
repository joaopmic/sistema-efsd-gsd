from django.conf import settings
from django.core.files.storage import FileSystemStorage


def get_private_storage():
    """Armazenamento privado: fora do diretório público e sem URL direta.
    Os arquivos só são entregues por views autenticadas."""
    return FileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT), base_url=None)
