"""Adaptador analítico OLAP en memoria usando DuckDB."""
from typing import Any, List, Optional
import duckdb

from sgb.domain.datos_abiertos.entities import (
    BibliotecaPublica,
    CruceDivipolaResultado,
    DepartamentoConteo,
    EstadisticasBibliotecas,
    EstadisticasDescriptivas,
    MunicipioConteo,
    MunicipioDivipola,
)
from sgb.domain.datos_abiertos.ports import AnalisisPort


def normalizar_municipio(texto: str) -> str:
    """Normaliza un nombre de municipio a mayúsculas y sin acentos."""
    if not texto:
        return ""
    s = texto.strip().upper()
    for con_tilde, sin_tilde in (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ü", "U")):
        s = s.replace(con_tilde, sin_tilde)
    return s


def _parse_float_lat_lon(val: Optional[str]) -> Optional[float]:
    """Parsea coordenadas geográficas que pueden venir con coma decimal."""
    if not val:
        return None
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


class DuckDBAnalisisAdapter(AnalisisPort):
    """Adaptador de infraestructura que ejecuta consultas analíticas en DuckDB."""

    def __init__(self, connection: Optional[Any] = None) -> None:
        self._con = connection or duckdb.connect(":memory:")

    def _cargar_bibliotecas(self, bibliotecas: List[BibliotecaPublica], tabla: str = "temp_bibliotecas") -> None:
        self._con.execute(f"CREATE OR REPLACE TEMP TABLE {tabla} ("
                          "nombre VARCHAR, municipio VARCHAR, municipio_norm VARCHAR, "
                          "correo VARCHAR, telefono VARCHAR)")
        if bibliotecas:
            filas = [
                (
                    b.nombre,
                    b.municipio,
                    normalizar_municipio(b.municipio),
                    b.correo or "",
                    b.telefono or "",
                )
                for b in bibliotecas
            ]
            self._con.executemany(f"INSERT INTO {tabla} VALUES (?, ?, ?, ?, ?)", filas)

    def _cargar_divipola(self, municipios: List[MunicipioDivipola], tabla: str = "temp_divipola") -> None:
        self._con.execute(f"CREATE OR REPLACE TEMP TABLE {tabla} ("
                          "codigo_departamento VARCHAR, departamento VARCHAR, "
                          "codigo_municipio VARCHAR, municipio VARCHAR, municipio_norm VARCHAR, "
                          "tipo VARCHAR, longitud DOUBLE, latitud DOUBLE)")
        if municipios:
            filas = [
                (
                    m.codigo_departamento,
                    m.departamento,
                    m.codigo_municipio,
                    m.municipio,
                    normalizar_municipio(m.municipio),
                    m.tipo,
                    _parse_float_lat_lon(m.longitud),
                    _parse_float_lat_lon(m.latitud),
                )
                for m in municipios
            ]
            self._con.executemany(f"INSERT INTO {tabla} VALUES (?, ?, ?, ?, ?, ?, ?, ?)", filas)

    def analizar_bibliotecas(self, bibliotecas: List[BibliotecaPublica]) -> EstadisticasBibliotecas:
        """Calcula estadísticas agregadas y top municipios a partir de la lista de bibliotecas."""
        self._cargar_bibliotecas(bibliotecas, "analisis_bibliotecas")

        row = self._con.execute(
            """
            SELECT
                COUNT(*) AS total_bib,
                COUNT(DISTINCT municipio_norm) AS total_mpios,
                COUNT(CASE WHEN correo IS NOT NULL AND TRIM(correo) != '' THEN 1 END) AS con_correo
            FROM analisis_bibliotecas
            """
        ).fetchone()

        total_bib = row[0] if row else 0
        total_mpios = row[1] if row else 0
        con_correo = row[2] if row else 0
        pct_correo = round((con_correo / total_bib * 100.0), 2) if total_bib > 0 else 0.0

        top_rows = self._con.execute(
            """
            SELECT municipio_norm, COUNT(*) AS conteo
            FROM analisis_bibliotecas
            WHERE municipio_norm != ''
            GROUP BY municipio_norm
            ORDER BY conteo DESC, municipio_norm ASC
            LIMIT 10
            """
        ).fetchall()

        top_municipios = [
            MunicipioConteo(municipio=r[0], total_bibliotecas=r[1])
            for r in top_rows
        ]

        return EstadisticasBibliotecas(
            total_bibliotecas=total_bib,
            total_municipios_con_biblioteca=total_mpios,
            porcentaje_con_correo=pct_correo,
            top_municipios=top_municipios,
        )

    def cruzar_con_divipola(
        self, bibliotecas: List[BibliotecaPublica], municipios: List[MunicipioDivipola]
    ) -> CruceDivipolaResultado:
        """Cruza bibliotecas con la división político-administrativa del DANE."""
        self._cargar_bibliotecas(bibliotecas, "cruce_bib")
        self._cargar_divipola(municipios, "cruce_div")

        # 1. Filtramos departamentos significativos (> 50% del máximo de municipios coincidentes)
        #    para descartar homónimos aislados de otros departamentos.
        # 2. Asignamos cada biblioteca a un único municipio prioritario para que ninguna biblioteca
        #    se duplique y el total cruzado nunca supere el total de entrada.
        self._con.execute(
            """
            CREATE OR REPLACE TEMP TABLE cruce_mpios_agg AS
            WITH coincidencias_por_depto AS (
                SELECT
                    d.departamento,
                    COUNT(DISTINCT b.municipio_norm) AS mpios_coincidentes
                FROM cruce_div d
                INNER JOIN cruce_bib b ON d.municipio_norm = b.municipio_norm
                GROUP BY d.departamento
            ),
            max_coincidencia AS (
                SELECT COALESCE(MAX(mpios_coincidentes), 0) AS max_mpios
                FROM coincidencias_por_depto
            ),
            deptos_conservados AS (
                SELECT c.departamento, c.mpios_coincidentes
                FROM coincidencias_por_depto c
                CROSS JOIN max_coincidencia m
                WHERE c.mpios_coincidentes > 0.5 * m.max_mpios
            ),
            div_filtrada AS (
                SELECT d.*, c.mpios_coincidentes AS depto_peso
                FROM cruce_div d
                INNER JOIN deptos_conservados c ON d.departamento = c.departamento
            ),
            div_priorizada AS (
                SELECT
                    d.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.municipio_norm
                        ORDER BY d.depto_peso DESC, d.departamento ASC, d.codigo_municipio ASC
                    ) AS rn
                FROM div_filtrada d
            ),
            bib_por_mpio AS (
                SELECT
                    municipio_norm,
                    COUNT(*) AS cant_bib
                FROM cruce_bib
                GROUP BY municipio_norm
            )
            SELECT
                d.codigo_municipio,
                d.departamento,
                d.municipio_norm,
                CASE
                    WHEN d.rn = 1 THEN COALESCE(b.cant_bib, 0)
                    ELSE 0
                END AS cant_bib
            FROM div_priorizada d
            LEFT JOIN bib_por_mpio b ON d.municipio_norm = b.municipio_norm;
            """
        )

        dept_rows = self._con.execute(
            """
            SELECT
                departamento,
                SUM(cant_bib) AS total_bibliotecas
            FROM cruce_mpios_agg
            GROUP BY departamento
            HAVING SUM(cant_bib) > 0 OR COUNT(*) > 0
            ORDER BY total_bibliotecas DESC, departamento ASC
            """
        ).fetchall()

        depto_conteo = [
            DepartamentoConteo(departamento=r[0], total_bibliotecas=r[1])
            for r in dept_rows
        ]

        stats_row = self._con.execute(
            """
            SELECT
                COUNT(*) AS total_mpios,
                COUNT(CASE WHEN cant_bib = 0 THEN 1 END) AS sin_bib,
                COALESCE(ROUND(AVG(cant_bib), 2), 0.0) AS media,
                COALESCE(MEDIAN(cant_bib), 0.0) AS mediana,
                COALESCE(MIN(cant_bib), 0) AS minimo,
                COALESCE(MAX(cant_bib), 0) AS maximo
            FROM cruce_mpios_agg
            """
        ).fetchone()

        total_divipola = stats_row[0] if stats_row else 0
        sin_bib = stats_row[1] if stats_row else 0
        media = float(stats_row[2]) if stats_row else 0.0
        mediana = float(stats_row[3]) if stats_row else 0.0
        minimo = int(stats_row[4]) if stats_row else 0
        maximo = int(stats_row[5]) if stats_row else 0

        return CruceDivipolaResultado(
            bibliotecas_por_departamento=depto_conteo,
            total_municipios_divipola=total_divipola,
            municipios_sin_biblioteca=sin_bib,
            estadisticas_distribucion=EstadisticasDescriptivas(
                media=media,
                mediana=mediana,
                minimo=minimo,
                maximo=maximo,
            ),
        )

