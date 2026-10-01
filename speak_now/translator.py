"""Traducción de texto offline usando Argos Translate."""

import os
from pathlib import Path

from speak_now import config

# Argos lee esta variable al importarse, así que debe definirse antes.
os.environ.setdefault(
    "ARGOS_PACKAGES_DIR", str(Path(config.ARGOS_PACKAGES_DIR).resolve())
)

import argostranslate.package  # noqa: E402
import argostranslate.translate  # noqa: E402


def install_language_pair(from_code, to_code):
    """Descarga e instala el paquete de idioma si aún no está instalado."""
    installed = argostranslate.package.get_installed_packages()
    if any(p.from_code == from_code and p.to_code == to_code for p in installed):
        return

    print(f"Descargando paquete de traducción {from_code} -> {to_code}...")
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    package = next(
        (p for p in available if p.from_code == from_code and p.to_code == to_code),
        None,
    )
    if package is None:
        raise RuntimeError(f"No existe paquete de Argos para {from_code} -> {to_code}")
    argostranslate.package.install_from_path(package.download())


class Translator:
    """Traduce texto de un idioma a otro (por ejemplo "en" -> "es").

    Uso:
        t = Translator("en", "es")
        t.translate("Hello world")  # "Hola mundo"
    """

    def __init__(self, from_code="en", to_code="es"):
        self.from_code = from_code
        self.to_code = to_code
        install_language_pair(from_code, to_code)
        # Guardamos el objeto de traducción para no buscarlo en cada frase.
        self._translation = argostranslate.translate.get_translation_from_codes(
            from_code, to_code
        )
        # La primera traducción carga el modelo en memoria (tarda varios
        # segundos). La hacemos ahora para que la primera frase real sea rápida.
        self._translation.translate("Hello.")

    def translate(self, text):
        text = text.strip()
        if not text:
            return ""
        return self._translation.translate(text)
