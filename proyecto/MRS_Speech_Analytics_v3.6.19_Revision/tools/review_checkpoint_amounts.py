"""Guardar confirmaciones humanas en una copia del lote y recalcular el reporte."""
import argparse
import json
from pathlib import Path
import sys
from tkinter import Tk, BooleanVar, Checkbutton, Label, Button, Frame, Canvas, Scrollbar, Entry, filedialog, messagebox

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.asr_amount_recovery import validated_entries
from app.services.account_source_validation import validate_account_source
from app.services.checkpoint_human_review import review_checkpoint, unreviewed_negotiation
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
    amounts={};names={};financial={}
    for item in payload.get("items",[]):
        data=item.get("result") or {};name=item.get("file_name") or data.get("archivo")
        entries=validated_entries(data.get("texto",""),data.get("segmentos",[]),data.get("recuperacion_importes"))
        naming=validate_account_source(item.get("relation") or {})
        negotiation=unreviewed_negotiation(item)
        balance_pending=negotiation.get("validacion_saldo_informado") in {
            "SALDO INFORMADO DIFERENTE AL SALDO TOTAL", "SALDO INFORMADO INCORRECTO - EXCEDE SALDO TOTAL"}
        plan=negotiation.get("installment_validation") or {}
        plan_pending=bool(plan.get("review_required") and plan.get("amounts") and plan.get("method")=="PARCIALIDADES_IDENTIFICADAS"
            and all(c.get("installment") for c in plan.get("conflicts", [])))
        previous=bool(item.get("financial_audio_review"))
        if not entries and not naming["review_required"] and not balance_pending and not plan_pending and not previous:continue
        Label(body,text=name,wraplength=850,justify="left").pack(anchor="w",padx=12,pady=(12,4))
        for entry in entries:
            variable=BooleanVar(value=False);amounts.setdefault(name,[]).append((entry["anchor_start"],variable))
            Checkbutton(body,text=f"Confirmé en el audio ${entry['amount']:g} ({entry['inicio']:g}–{entry['fin']:g} s).",variable=variable).pack(anchor="w",padx=18)
        if naming["review_required"] and naming.get("expected_last4"):
            variable=BooleanVar(value=False);names[name]=variable
            Checkbutton(body,text=f"Confirmo tarjeta ****{naming['expected_last4']}; corregir solo el identificador de nombre_final (****{naming['name_last4']}).",variable=variable,wraplength=850).pack(anchor="w",padx=18)
        controls={}
        if balance_pending:
            controls['balance_check']=BooleanVar(value=False)
            Checkbutton(body,text=f"Confirmé en audio el saldo informado (ASR: ${negotiation['saldo_informado_detectado']:g}). Escriba el importe comprobado:",
                variable=controls['balance_check'],wraplength=850).pack(anchor="w",padx=18)
            controls['balance_entry']=Entry(body,width=18);controls['balance_entry'].pack(anchor="w",padx=40)
        if plan_pending:
            controls['plan_check']=BooleanVar(value=False)
            summary='; '.join(f"pago {j}: ${amount:g}" for j,amount in enumerate(plan['amounts'],1))
            Checkbutton(body,text=f"Confirmé que el acuerdo final es {summary}. Se conserva la propuesta inicial en el historial.",
                variable=controls['plan_check'],wraplength=850).pack(anchor="w",padx=18)
        if previous:
            controls['revoke_check']=BooleanVar(value=False)
            Checkbutton(body,text="Revocar la confirmación financiera anterior y volver a evaluar la lectura ASR.",
                variable=controls['revoke_check'],wraplength=850).pack(anchor="w",padx=18)
        if controls:financial[name]=controls
    result_box={}
    def save():
        confirmations={name:{"anchors":[anchor for anchor,var in values if var.get()],"audio_verified":True}
                       for name,values in amounts.items() if any(var.get() for _,var in values)}
        corrections=[name for name,var in names.items() if var.get()]
        finance={}
        for name,controls in financial.items():
            entry={}
            if controls.get('balance_check') is not None and controls['balance_check'].get():
                entry['balance_amount']=controls['balance_entry'].get().strip()
            if controls.get('plan_check') is not None and controls['plan_check'].get():entry['confirm_installments']=True
            if controls.get('revoke_check') is not None and controls['revoke_check'].get():
                if entry:
                    messagebox.showerror("Validación","No se puede confirmar y revocar a la vez la misma llamada.",parent=root);return
                entry={'revoke':True}
            elif entry:entry['audio_verified']=True
            if entry:finance[name]=entry
        if not confirmations and not corrections and not finance:
            messagebox.showinfo("Validación","No se marcó ninguna confirmación. Los resultados permanecen sin cambios.",parent=root);return
        excel_source=args.relation_excel or Path(payload.get("relation_excel") or "")
        if corrections and not excel_source.is_file():
            selected=filedialog.askopenfilename(title="Seleccionar Excel de cuentas para generar una copia (opcional)",filetypes=[("Excel","*.xlsx *.xlsm")])
            excel_source=Path(selected) if selected else None
        try:
            result_box.update(review_checkpoint(source,confirmations,corrections,args.output_dir,excel_source,financial_confirmations=finance))
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
