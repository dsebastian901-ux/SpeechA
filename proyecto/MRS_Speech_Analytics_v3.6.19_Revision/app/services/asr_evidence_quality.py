"""Calidad de lecturas alternativas: no confundir bucles ASR con conducta real."""
import math
import re
from collections import Counter


def _number(value,default=0.0):
    try:
        value=float(value)
        return value if math.isfinite(value) else default
    except (TypeError,ValueError):return default


def reading_quality(segments):
    segments=segments or []
    warnings=[]
    for index,segment in enumerate(segments):
        text=str(segment.get('text') or '')
        tokens=re.findall(r'\w+',text.lower())
        words=segment.get('words') or []
        zero=sum(_number(w.get('end'))<=_number(w.get('start')) for w in words)
        zero_ratio=zero/len(words) if words else 0
        start=_number(segment.get('start'));end=_number(segment.get('end'))
        compression=_number(segment.get('compression_ratio'))
        dominant=max(Counter(tokens).values(),default=0)/len(tokens) if tokens else 0
        repeated=len(tokens)>=12 and dominant>=.70 and (compression>=4 or zero_ratio>=.65)
        bad_alignment=len(tokens)>=3 and compression>=3.5 and zero_ratio>=.60 and len(tokens)/max(.01,end-start)>=10
        invalid_time=start<0 or end<start
        if repeated or bad_alignment or invalid_time:
            warnings.append({'segment_index':index,'start':start,'end':end,
                'reason':('REPETICION_ASR' if repeated else 'ALINEACION_NO_CONFIABLE' if bad_alignment else 'TIEMPOS_INVALIDOS'),
                'tokens':len(tokens),'zero_duration_words':zero,'word_count':len(words),
                'compression_ratio':compression,'text':text})
    # Un bucle puede quedar partido en muchos segmentos de tres palabras.
    cursor=0;already={w['segment_index'] for w in warnings}
    while cursor<len(segments):
        key=re.findall(r'\w+',str(segments[cursor].get('text') or '').casefold())
        end=cursor+1
        while end<len(segments) and key==re.findall(r'\w+',str(segments[end].get('text') or '').casefold()):end+=1
        span=segments[cursor:end];count=len(key)*len(span)
        duration=_number(span[-1].get('end'))-_number(span[0].get('start'))
        if len(span)>=6 and count>=18 and count/max(.01,duration)>=10 and all(_number(s.get('compression_ratio'))>=3.5 for s in span):
            for index in range(cursor,end):
                if index not in already:
                    s=segments[index];warnings.append({'segment_index':index,'start':_number(s.get('start')),
                        'end':_number(s.get('end')),'reason':'REPETICION_ASR_ENTRE_SEGMENTOS',
                        'tokens':len(key),'text':s.get('text','')})
        cursor=end
    warnings.sort(key=lambda w:w['segment_index'])
    return {'degraded':bool(warnings),'warnings':warnings,'bad_segment_indices':[w['segment_index'] for w in warnings]}


def block_reading_quality(primary,tail):
    first,closing=reading_quality(primary),reading_quality(tail)
    return {'primary':first,'tail':closing,'degraded':first['degraded'] or closing['degraded'],
            'human_verified':False,'interpretation':'Advertencia técnica de lectura, no falta ni respuesta del interlocutor.'}


def usable_groups(segments):
    """No unir frases a través de un hueco de reconocimiento descartado."""
    bad=set(reading_quality(segments)['bad_segment_indices']);groups=[];current=[]
    for index,segment in enumerate(segments or []):
        if index in bad:
            if current:groups.append(' '.join(current));current=[]
            continue
        current.append(str(segment.get('text') or '').strip())
    if current:groups.append(' '.join(current))
    return groups
