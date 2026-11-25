import json
from app.services.conversation_evidence import holder_confirmation,assess_home_recovery_warning
from app.services.contact_evidence_graph import nonholder_context
from app.services.payment_lifecycle import financial_response_events
from app.services.payment_intent_frames import payment_frames
from app.services.current_payment_amounts import explicit_current_amounts
from app.services.balance_context_evidence import balance_scope
from app.services.payment_instruction_validation import transfer_is_option_listing
from app.services.installment_validation import unresolved_accepted_plan
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
r={}
s='Buen día Mecumonico con Marina Robles. Habla MRS. Yo no tengo dinero para pagar mi tarjeta.'
r['C01_nominal_asr_identified']=holder_confirmation(s)['confirmed']
s='¿Me comunica con Marina Robles? Sí, dígame. Habla MRS. Mi aplicación muestra mi pago. ¿Recuerda la fecha del pago? No, pero si me permite lo busco.'
r['C02_financial_search_is_intermediary']=nonholder_context(s)
s='Me comunico con Marina Robles, el motivo de mi llamada es su tarjeta. Habla MRS. Voy a saldar el total de la tarjeta.'
r['C03_own_financial_context_identified']=holder_confirmation(s)['confirmed']
r['C04_immediate_recap_accepted']=bool(financial_response_events('¿Sería un pago de 900 pesos el día de hoy? Así es.'))
s='Gestor: Me podría indicar el monto y la fecha de su pago, por favor? Titular: Sería el monto es 900, el día 20 de noviembre.'
r['C05_joint_reply_accepted']=any(f['accepted']for f in payment_frames(s));r['C05_joint_reply_amounts']=sorted({v['amount']for v in explicit_current_amounts(s)})
s='Cubra 5000 que es su saldo vencido o los 2400 que es el mínimo requerido.';at=s.index('2400');r['C07_minimum_scope']=balance_scope(s,[],at,at+4)
s='Yo ahorita consulté saldo y tengo un saldo de 34 pesos.';at=s.index('34');r['C08_own_app_scope']=balance_scope(s,[],at,at+2)
r['C09_bank_enum_listing']=transfer_is_option_listing('Alternativas: transferencia por medio de Santander, BBVA o Banamex.',[],['KIOSKO'])
s='Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante. En la llamada anterior me trataron mal.'
m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'sample.wav','texto':s,'duracion_segundos':90,'segmentos':[]}),{'estatus_grabacion':'CONVENIO','pago_minimo':800}).metadata
r['C10_confirmed_complaint']=m['shared_classification']['clasificacion']
r['C11_unattributed_asset_warning_review']=assess_home_recovery_warning('Los abogados van a recuperar el monto en bienes y muebles.',mora='5PV')['review_required']
s='Entonces confirma pago de 500 pesos para mañana y 11500 estaría aplicando para el día lunes 23. Sí, pero mañana primero voy a depositar.'
r['C15_incomplete_two_payment_recap_review']=unresolved_accepted_plan(s,{'amounts':[]},[])['review_required']
print(json.dumps(r,ensure_ascii=False,indent=2))
