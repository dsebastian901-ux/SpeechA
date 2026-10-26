"""Guardar confirmaciones humanas en una copia del lote y recalcular el reporte."""
import argparse
import json
from pathlib import Path
import sys
from tkinter import Tk, BooleanVar, Checkbutton, Label, Button, Frame, Canvas, Scrollbar, filedialog, messagebox

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.asr_amount_recovery import validated_entries
from app.services.account_source_validation import validate_account_source
from app.services.checkpoint_human_review import review_checkpoint
from app.services.checkpoint_output import default_output_root


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint",type=Path)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--relation-excel",type=Path)
    args=parser.parse_args()
    root=Tk();root.withdraw()
    source=args.checkpoint
    if source is None:
        selected=filedialog.askopenfilename(title="Seleccionar checkpoint final",filetypes=[("Checkpoint JSON","*.json")])
        if not selected:root.destroy();return
        source=Path(selected)
    payload=json.loads(source.read_text(encoding="utf-8-sig"))
    root.title("Confirmar importes y datos de salida");root.geometry("900x620")
    Label(root,text="Marque únicamente lo ya comprobado en el audio o en los datos de cuenta.",wraplength=850).pack(pady=12)
    Label(root,text=f"Carpeta de resultados: {args.output_dir or default_output_root()}",wraplength=850).pack()
    container=Frame(root);container.pack(fill="both",expand=True)
    canvas=Canvas(container);bar=Scrollbar(container,orient="vertical",command=canvas.yview)
    body=Frame(canvas);body.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0,0),window=body,anchor="nw");canvas.configure(yscrollcommand=bar.set)
    canvas.pack(side="left",fill="both",expand=True);bar.pack(side="right",fill="y")
    amounts={};names={}
    for item in payload.get("items",[]):
        data=item.get("result") or {};name=item.get("file_name") or data.get("archivo")
        entries=validated_entries(data.get("texto",""),data.get("segmentos",[]),data.get("recuperacion_importes"))
        naming=validate_account_source(item.get("relation") or {})
        if not entries and not naming["review_required"]:continue
        Label(body,text=name,wraplength=850,justify="left").pack(anchor="w",padx=12,pady=(12,4))
        for entry in entries:
            variable=BooleanVar(value=False);amounts.setdefault(name,[]).append((entry["anchor_start"],variable))
            Checkbutton(body,text=f"Confirmé en el audio ${entry['amount']:g} ({entry['inicio']:g}–{entry['fin']:g} s).",variable=variable).pack(anchor="w",padx=18)
        if naming["review_required"] and naming.get("expected_last4"):
            variable=BooleanVar(value=False);names[name]=variable
            Checkbutton(body,text=f"Confirmo tarjeta ****{naming['expected_last4']}; corregir solo el identificador de nombre_final (****{naming['name_last4']}).",variable=variable,wraplength=850).pack(anchor="w",padx=18)
    result_box={}
    def save():
        confirmations={name:{"anchors":[anchor for anchor,var in values if var.get()],"audio_verified":True}
                       for name,values in amounts.items() if any(var.get() for _,var in values)}
        corrections=[name for name,var in names.items() if var.get()]
        if not confirmations and not corrections:
            messagebox.showinfo("Validación","No se marcó ninguna confirmación. Los resultados permanecen sin cambios.",parent=root);return
        excel_source=args.relation_excel or Path(payload.get("relation_excel") or "")
        if corrections and not excel_source.is_file():
            selected=filedialog.askopenfilename(title="Seleccionar Excel de cuentas para generar una copia (opcional)",filetypes=[("Excel","*.xlsx *.xlsm")])
            excel_source=Path(selected) if selected else None
        try:
            result_box.update(review_checkpoint(source,confirmations,corrections,args.output_dir,excel_source))
        except Exception as error:
            messagebox.showerror("Validación",str(error),parent=root);return
        root.destroy()
    Button(root,text="Guardar en copia y generar reporte",command=save).pack(pady=16)
    root.deiconify();root.mainloop()
    if result_box:
        print("Revisión del motor:",result_box["engine_revision"])
        print("Resultados:",result_box["outcomes"])
        print("Reporte nuevo:",result_box["report"])
        print("Checkpoint nuevo:",result_box["checkpoint"])
        if result_box.get("corrected_excel"):print("Excel de cuentas corregido en copia:",result_box["corrected_excel"])
        elif result_box.get("output_names_corrected"):print("Los nombres corregidos están en el checkpoint; no se generó copia del Excel porque no se seleccionó o localizó el original.")
        print("Se conservaron los originales. No se ejecutó Whisper ni se copiaron audios.")


if __name__=="__main__":main()
