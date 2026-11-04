"""Lectura y perfilado de archivos Excel / CSV."""
from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd


def normalizar(texto: str) -> str:
    """Quita acentos, espacios extra y pasa a minúsculas para comparar columnas."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.replace("_", " ").split())


def cargar_archivo(ruta: str | Path, hoja: str | int | None = None) -> pd.DataFrame:
    """Carga un archivo .xlsx, .xls o .csv y devuelve un DataFrame limpio.

    - Elimina filas y columnas completamente vacías.
    - Convierte los nombres de columna a texto.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta, sep=None, engine="python")
    elif ruta.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(ruta, sheet_name=hoja if hoja is not None else 0)
    else:
        raise ValueError(f"Formato no soportado: {ruta.suffix}. Use .xlsx, .xls o .csv")

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df.reset_index(drop=True)


def listar_hojas(ruta: str | Path) -> list[str]:
    """Devuelve los nombres de las hojas de un archivo Excel."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".csv":
        return ["csv"]
    return pd.ExcelFile(ruta).sheet_names


def perfilar(df: pd.DataFrame) -> dict:
    """Devuelve un perfil básico del DataFrame: forma, tipos, nulos y estadísticas."""
    numericas = df.select_dtypes(include="number").columns.tolist()
    categoricas = [c for c in df.columns if c not in numericas]
    perfil = {
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "columnas_numericas": numericas,
        "columnas_categoricas": categoricas,
        "nulos_por_columna": {c: int(v) for c, v in df.isna().sum().items() if v > 0},
        "estadisticas": {},
        "categorias": {},
    }
    if numericas:
        desc = df[numericas].describe().T
        perfil["estadisticas"] = {
            col: {k: round(float(v), 2) for k, v in fila.items()}
            for col, fila in desc.iterrows()
        }
    for col in categoricas:
        valores = df[col].dropna().astype(str)
        if 0 < valores.nunique() <= 25:
            perfil["categorias"][col] = {
                str(k): int(v) for k, v in valores.value_counts().head(10).items()
            }
    return perfil


def encontrar_columna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    """Busca la primera columna del DataFrame que coincida con alguno de los candidatos.

    La comparación ignora mayúsculas, acentos y guiones bajos. También acepta
    coincidencias parciales (el candidato contenido en el nombre de la columna).
    """
    mapa = {normalizar(c): c for c in df.columns}
    for cand in candidatos:
        n = normalizar(cand)
        if n in mapa:
            return mapa[n]
    for cand in candidatos:
        n = normalizar(cand)
        for norm, original in mapa.items():
            if n and (n in norm or norm in n):
                return original
    return None
