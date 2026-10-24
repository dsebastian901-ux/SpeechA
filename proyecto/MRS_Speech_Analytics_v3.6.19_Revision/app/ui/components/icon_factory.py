from __future__ import annotations
from functools import lru_cache
import math
import customtkinter as ctk
from PIL import Image, ImageDraw
from app.ui.themes import Theme

class IconFactory:
    @staticmethod
    @lru_cache(maxsize=128)
    def create(name: str, size: int = 22, color: str = Theme.colors.PRIMARY) -> ctk.CTkImage:
        scale = 4
        w = h = size * scale
        image = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        c = IconFactory._hex(color)
        stroke = max(2, int(size * 0.09)) * scale
        m = int(size * 0.18) * scale
        def line(points, width=stroke): draw.line(points, fill=c, width=width, joint='curve')
        if name == 'home':
            line([(m,h//2),(w//2,m),(w-m,h//2)])
            draw.rectangle((m*2,h//2,w-m*2,h-m), outline=c, width=stroke)
        elif name == 'microphone':
            draw.rounded_rectangle((w*.35,m,w*.65,h*.58), radius=stroke*2, outline=c, width=stroke)
            line([(w*.22,h*.43),(w*.22,h*.58),(w*.5,h*.75),(w*.78,h*.58),(w*.78,h*.43)])
            line([(w*.5,h*.75),(w*.5,h-m)]); line([(w*.34,h-m),(w*.66,h-m)])
        elif name == 'document':
            draw.rounded_rectangle((m,m,w-m,h-m), radius=stroke, outline=c, width=stroke)
            line([(w*.58,m),(w*.58,h*.35),(w-m,h*.35)])
            line([(w*.3,h*.52),(w*.7,h*.52)]); line([(w*.3,h*.67),(w*.7,h*.67)])
        elif name == 'analytics':
            for x,top in zip([.22,.38,.52,.67,.80],[.42,.68,.85,.60,.35]):
                line([(w*x,h*(1-top)/2+m),(w*x,h-(h*(1-top)/2+m))], width=max(stroke//2,2))
        elif name == 'dashboard':
            for box in [(m,m,w*.47,h*.47),(w*.53,m,w-m,h*.47),(m,h*.53,w*.47,h-m),(w*.53,h*.53,w-m,h-m)]:
                draw.rounded_rectangle(box, radius=stroke, outline=c, width=stroke)
        elif name == 'reports':
            line([(m,h-m),(w-m,h-m)])
            for x,top in [(0.28,.55),(.50,.35),(.72,.20)]:
                draw.rounded_rectangle((w*x-stroke,h*top,w*x+stroke*2,h-m), radius=stroke, fill=c)
        elif name == 'folder':
            draw.rounded_rectangle((m,h*.30,w-m,h-m), radius=stroke, outline=c, width=stroke)
            line([(m*1.2,h*.30),(w*.40,h*.30),(w*.50,h*.20),(w*.72,h*.20)])
        elif name == 'users':
            draw.ellipse((w*.20,m,w*.48,h*.42), outline=c, width=stroke)
            draw.ellipse((w*.55,h*.18,w*.78,h*.40), outline=c, width=stroke)
            draw.arc((m,h*.38,w*.60,h-m),190,350,fill=c,width=stroke)
            draw.arc((w*.40,h*.42,w-m,h-m),195,345,fill=c,width=stroke)
        elif name == 'settings':
            draw.ellipse((w*.34,h*.34,w*.66,h*.66), outline=c, width=stroke)
            for angle in range(0,360,45):
                a=math.radians(angle); r1=w*.28; r2=w*.43
                line([(w/2+r1*math.cos(a),h/2+r1*math.sin(a)),(w/2+r2*math.cos(a),h/2+r2*math.sin(a))])
        elif name == 'history':
            draw.arc((m,m,w-m,h-m),35,325,fill=c,width=stroke)
            line([(m*.85,h*.35),(m*.95,m),(w*.30,m*1.2)])
            line([(w/2,h/2),(w/2,h*.30)]); line([(w/2,h/2),(w*.67,h*.62)])
        elif name == 'check':
            draw.ellipse((m,m,w-m,h-m), outline=c, width=stroke)
            line([(w*.30,h*.52),(w*.45,h*.66),(w*.72,h*.36)])
        elif name == 'clock':
            draw.ellipse((m,m,w-m,h-m), outline=c, width=stroke)
            line([(w/2,h/2),(w/2,h*.30)]); line([(w/2,h/2),(w*.66,h*.60)])
        elif name == 'wave':
            for x,height in zip([.20,.32,.44,.56,.68,.80],[.25,.55,.85,.65,.45,.30]):
                line([(w*x,h*(.5-height/2)),(w*x,h*(.5+height/2))], width=max(stroke//2,2))
        elif name == 'cpu':
            draw.rectangle((w*.28,h*.28,w*.72,h*.72), outline=c, width=stroke)
            draw.rectangle((w*.40,h*.40,w*.60,h*.60), outline=c, width=stroke)
            for pos in [.34,.50,.66]:
                line([(w*pos,m),(w*pos,h*.28)], width=max(stroke//2,2)); line([(w*pos,h*.72),(w*pos,h-m)], width=max(stroke//2,2))
                line([(m,h*pos),(w*.28,h*pos)], width=max(stroke//2,2)); line([(w*.72,h*pos),(w-m,h*pos)], width=max(stroke//2,2))
        elif name == 'ram':
            draw.rounded_rectangle((m,h*.30,w-m,h*.70), radius=stroke, outline=c, width=stroke)
            for x in [.30,.43,.56,.69]: line([(w*x,h*.40),(w*x,h*.60)], width=max(stroke//2,2))
        elif name == 'search':
            draw.ellipse((m,m,w*.65,h*.65), outline=c, width=stroke); line([(w*.60,h*.60),(w-m,h-m)])
        image = image.resize((size,size), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size,size))

    @staticmethod
    def _hex(value: str):
        value=value.lstrip('#')
        return tuple(int(value[i:i+2],16) for i in (0,2,4)) + (255,)
