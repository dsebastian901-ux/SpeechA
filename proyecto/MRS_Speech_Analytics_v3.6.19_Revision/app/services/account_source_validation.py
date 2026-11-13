"""Datos de origen: la identidad del nombre de salida no prueba una falta en audio."""
import re
from pathlib import PureWindowsPath


def validate_account_source(relation):
    """nombre_final y numero_de_tarjeta son campos independientes.

    El numero_de_tarjeta es referencia para la comprobacion del audio; ninguna
    diferencia con el nombre de salida constituye un conflicto de identidad.
    """
    return {"review_required": False, "reason": ""}


def corrected_account_name(relation):
    """No está permitida la corrección de nombres a partir de la tarjeta."""
    raise ValueError("nombre_final es independiente de numero_de_tarjeta.")


def apply_output_name_authority(item):
    """Compatibilidad con llamadas anteriores: nunca reescribir nombre_final."""
    return False


def write_corrected_relation_excel(source_excel, corrections, destination):
    """Solo filas confirmadas; no se cambia numero_de_tarjeta ni el original."""
    from pathlib import Path
    from openpyxl import load_workbook
    source, target = Path(source_excel), Path(destination)
    if source.resolve() == target.resolve() or target.exists():
        raise ValueError("No se sobrescribe el Excel original ni una copia existente.")
    workbook=load_workbook(source,keep_vba=source.suffix.lower()==".xlsm")
    try:
        sheet=workbook["Relacion_Audios"]
        headers={str(c.value or "").strip().lower():c.column for c in sheet[1]}
        for name in ("archivo_original","nombre_final","numero_de_tarjeta"):
            if name not in headers:raise ValueError(f"Falta la columna {name} en el Excel.")
        applied=set()
        for row in range(2,sheet.max_row+1):
            name=str(sheet.cell(row,headers["archivo_original"]).value or "")
            if name not in corrections:continue
            entry=corrections[name]
            if name in applied:raise ValueError("El Excel contiene duplicados para una cuenta revisada.")
            card=str(sheet.cell(row,headers["numero_de_tarjeta"]).value or "").strip()
            if card != entry["numero_de_tarjeta"]:
                raise ValueError("La tarjeta del Excel cambió respecto al checkpoint; revisar datos de origen.")
            sheet.cell(row,headers["nombre_final"]).value=entry["nombre_final"]
            applied.add(name)
        if applied!=set(corrections):raise ValueError("No se encontraron todas las llamadas revisadas en el Excel.")
        workbook.save(target)
    finally:
        workbook.close()
    return str(target)
