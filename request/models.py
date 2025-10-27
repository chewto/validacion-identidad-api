from typing import Optional
import datetime

from sqlalchemy import DateTime, Enum, Index, String, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, MEDIUMBLOB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class ComprobacionProceso(Base):
    __tablename__ = 'comprobacion_proceso'

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    id_proceso: Mapped[str] = mapped_column(String(25), nullable=False)
    estado: Mapped[str] = mapped_column(String(25), nullable=False)
    id_validacion: Mapped[Optional[str]] = mapped_column(String(50))


class DocumentoUsuario(Base):
    __tablename__ = 'documento_usuario'
    __table_args__ = (
        Index('Índice 2', 'id_usuario_efirma'),
        Index('Índice 3', 'id_evidencias_adicionales'),
        Index('Índice 4', 'id_evidencias')
    )

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    nombres: Mapped[str] = mapped_column(String(50), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(50), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    id_evidencias: Mapped[int] = mapped_column(INTEGER(11), nullable=False)
    id_evidencias_adicionales: Mapped[int] = mapped_column(INTEGER(11), nullable=False)
    id_usuario_efirma: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    id_usuario: Mapped[Optional[str]] = mapped_column(String(255))
    tipo_validacion: Mapped[Optional[int]] = mapped_column(INTEGER(11))


class EvidenciasAdicionales(Base):
    __tablename__ = 'evidencias_adicionales'

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    estado_verificacion: Mapped[Optional[str]] = mapped_column(String(500))
    dispositivo: Mapped[Optional[str]] = mapped_column(String(500))
    navegador: Mapped[Optional[str]] = mapped_column(String(500))
    ip_privada: Mapped[Optional[str]] = mapped_column(String(500))
    latitud: Mapped[Optional[str]] = mapped_column(String(500))
    longitud: Mapped[Optional[str]] = mapped_column(String(500))
    hora: Mapped[Optional[str]] = mapped_column(String(500))
    fecha: Mapped[Optional[str]] = mapped_column(String(500))
    ip_publica: Mapped[Optional[str]] = mapped_column(String(500))
    validacion_nombre_ocr: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    validacion_apellido_ocr: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    validacion_documento_ocr: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    nombre_ocr: Mapped[Optional[str]] = mapped_column(String(500))
    apellido_ocr: Mapped[Optional[str]] = mapped_column(String(500))
    documento_ocr: Mapped[Optional[str]] = mapped_column(String(500))
    id_carpeta_entidad: Mapped[Optional[str]] = mapped_column(String(50))
    id_carpeta_usuario: Mapped[Optional[str]] = mapped_column(String(50))
    validacion_vida: Mapped[Optional[str]] = mapped_column(String(10))
    proveedor_validacion: Mapped[Optional[str]] = mapped_column(String(100))
    mrz: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    codigo_barras: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    checks_json: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    verificacion_manual: Mapped[Optional[str]] = mapped_column(String(255))
    video_hash: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    intentos_reverso: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    intentos_anverso: Mapped[Optional[int]] = mapped_column(INTEGER(11))


class EvidenciasUsuario(Base):
    __tablename__ = 'evidencias_usuario'

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    anverso_documento: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    reverso_documento: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    foto_usuario: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    estado_verificacion: Mapped[str] = mapped_column(String(10), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(50), nullable=False)


class Pais(Base):
    __tablename__ = 'pais'

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    nombre: Mapped[Optional[str]] = mapped_column(String(50))
    codigo: Mapped[Optional[str]] = mapped_column(String(10))
    mrz: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    barcode: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    ocr: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    tipo_documento_empresa: Mapped[Optional[str]] = mapped_column(String(100))
    tipo_documento_firmador: Mapped[Optional[str]] = mapped_column(String(100))
    tipo_documento_validacion: Mapped[Optional[str]] = mapped_column(String(100))


class ParametrosValidacion(Base):
    __tablename__ = 'parametros_validacion'

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    id_usuario: Mapped[Optional[int]] = mapped_column(BIGINT(20))
    callback: Mapped[Optional[str]] = mapped_column(String(255))
    redireccion: Mapped[Optional[str]] = mapped_column(String(255))
    parametros_hash: Mapped[Optional[str]] = mapped_column(String(255))
    nombre: Mapped[Optional[str]] = mapped_column(String(50))
    apellido: Mapped[Optional[str]] = mapped_column(String(50))
    documento: Mapped[Optional[str]] = mapped_column(String(50))
    tipo_documento: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(50))
    tipo_validacion: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    uso_modelo: Mapped[Optional[str]] = mapped_column(String(50))


class ProcesosFirma(Base):
    __tablename__ = 'procesos_firma'

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    id_firma: Mapped[int] = mapped_column(INTEGER(11), nullable=False)
    orden: Mapped[int] = mapped_column(INTEGER(11), nullable=False)
    rol: Mapped[str] = mapped_column(String(50), nullable=False)
    id_usuario: Mapped[int] = mapped_column(INTEGER(11), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    estado: Mapped[Optional[str]] = mapped_column(Enum('Pendiente', 'Aprobado', 'Rechazado'), server_default=text("'Pendiente'"))
    fecha_inicio: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('current_timestamp()'))
    fecha_aprobado: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    fecha_rechazado: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    ubicacion: Mapped[Optional[str]] = mapped_column(String(255))
    intentos_envio: Mapped[Optional[int]] = mapped_column(INTEGER(11), server_default=text('0'))


class RolesPlantilla(Base):
    __tablename__ = 'roles_plantilla'
    __table_args__ = (
        Index('id_plantilla_procesos', 'id_plantilla_procesos'),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    rol: Mapped[str] = mapped_column(String(100), nullable=False)
    orden: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    id_plantilla_procesos: Mapped[Optional[int]] = mapped_column(INTEGER(11))


class ValidacionRaw(Base):
    __tablename__ = 'validacion_raw'

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    selfie: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    anverso_documento: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    reverso_documento: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    info_validacion: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    check_validacion: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    callId: Mapped[str] = mapped_column(String(25), nullable=False)
    reglas_negocio: Mapped[Optional[str]] = mapped_column(LONGTEXT)
