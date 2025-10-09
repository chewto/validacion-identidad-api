def _formatDocumentNumber(documentNumber):
    """Normaliza un número de identificación de forma genérica:
    - Si numero_documento es falsy, devuelve tal cual (None o '').
    - Si existe, elimina todo espacio en blanco dentro del string y lo devuelve.
    Esta versión es agnóstica al país/tipo y útil como utilidad global.
    """
    if not documentNumber:
        return documentNumber
    # eliminar cualquier espacio en blanco (espacios, tabulaciones, nuevas líneas)
    return ''.join(str(documentNumber).split())