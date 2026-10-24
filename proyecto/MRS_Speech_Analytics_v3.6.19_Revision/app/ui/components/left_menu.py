from __future__ import annotations
import customtkinter as ctk
from app.ui.themes import Theme

class LeftMenu(ctk.CTkFrame):
    def __init__(self,parent,on_home=None,on_new_project=None,on_open_project=None,on_audio=None,
                 on_transcriptions=None,on_analytics=None,on_dashboard=None,on_batch=None,
                 on_reports=None,on_settings=None,on_history=None,on_collapse=None):
        super().__init__(parent,width=238,corner_radius=0,fg_color=Theme.colors.SIDEBAR_BACKGROUND)
        self.grid_propagate(False); self.grid_columnconfigure(0,weight=1)
        self.on_collapse=on_collapse
        callbacks=[on_home,on_new_project,on_open_project,on_audio,on_transcriptions,on_analytics,
                   on_dashboard,on_batch,on_reports,on_settings,on_history]
        callbacks=[x if callable(x) else self.not_available for x in callbacks]
        (self.on_home,self.on_new_project,self.on_open_project,self.on_audio,self.on_transcriptions,
         self.on_analytics,self.on_dashboard,self.on_batch,self.on_reports,self.on_settings,self.on_history)=callbacks
        brand=ctk.CTkFrame(self,fg_color='transparent'); brand.grid(row=0,column=0,padx=14,pady=(17,10),sticky='ew')
        brand.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(brand,text='◉  MRS',text_color='#FFFFFF',font=ctk.CTkFont('Georgia',27,'bold'),anchor='w').grid(row=0,column=0,sticky='w')
        ctk.CTkButton(brand,text='‹',width=32,height=30,corner_radius=10,fg_color='#4A2A69',hover_color='#65408A',
                      command=self.on_collapse).grid(row=0,column=1,sticky='e')
        ctk.CTkLabel(self,text='SPEECH ANALYTICS | QUALITY',text_color='#D7C6EB',font=ctk.CTkFont('Segoe UI',9,'bold')).grid(row=1,column=0,padx=18,pady=(0,17),sticky='w')
        ctk.CTkLabel(self,text='MENÚ',text_color='#CDBEE0',font=ctk.CTkFont('Segoe UI',12,'bold'),anchor='w').grid(row=2,column=0,padx=18,pady=(0,8),sticky='ew')
        items=[('⌂   Inicio',self.on_home),('▣   Nuevo Proyecto',self.on_new_project),('▰   Abrir Proyecto',self.on_open_project),
               ('♫   Gestión de Audios',self.on_audio),('▤   Transcripciones',self.on_transcriptions),('▥   Analytics de Llamadas',self.on_analytics),
               ('◕   Dashboard',self.on_dashboard),('▶   Procesamiento por lotes',self.on_batch),('▧   Reportes',self.on_reports),
               ('⚙   Configuración',self.on_settings),('◷   Historial',self.on_history)]
        for i,(text,cmd) in enumerate(items,3): self.create_menu_button(i,text,cmd,selected=(i==3))
        self.grid_rowconfigure(14,weight=1)
        ctk.CTkLabel(self,text='⌁⌁⌁⌁⌁⌁⌁⌁⌁',text_color='#B77DD7',font=ctk.CTkFont('Segoe UI',18)).grid(row=15,column=0,pady=(4,2))
        ctk.CTkLabel(self,text='MRS CONSULTORES',text_color='#FFFFFF',font=ctk.CTkFont('Segoe UI',11,'bold')).grid(row=16,column=0)
        ctk.CTkLabel(self,text='USO INTERNO',text_color='#BDA9D2',font=ctk.CTkFont('Segoe UI',9)).grid(row=17,column=0,pady=(2,2))
        ctk.CTkLabel(self,text='“Del audio a las oportunidades”',text_color='#D7B9E6',font=ctk.CTkFont(family='Segoe UI', size=10, slant='italic')).grid(row=18,column=0,pady=(2,15))
    def create_menu_button(self,row,text,command,selected=False):
        b=ctk.CTkButton(self,text=text,height=38,corner_radius=9,anchor='w',command=command,
            fg_color=Theme.colors.SIDEBAR_SELECTED if selected else 'transparent',
            hover_color=Theme.colors.SIDEBAR_HOVER,text_color=Theme.colors.SIDEBAR_TEXT_ACTIVE if selected else Theme.colors.SIDEBAR_TEXT,
            font=ctk.CTkFont('Segoe UI',12,'bold' if selected else 'normal'))
        b.grid(row=row,column=0,padx=12,pady=2,sticky='ew'); return b
    def not_available(self): print('Módulo todavía no disponible.')
