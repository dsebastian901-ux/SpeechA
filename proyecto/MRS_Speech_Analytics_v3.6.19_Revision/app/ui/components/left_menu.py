from __future__ import annotations
import customtkinter as ctk
from app.ui.themes import Theme
from app.services.auth_service import PERMISSIONS

class LeftMenu(ctk.CTkFrame):
    """Role-filtered, scrollable menu. All entries remain reachable on small displays."""
    def __init__(self,parent,on_home=None,on_new_project=None,on_open_project=None,on_audio=None,
                 on_transcriptions=None,on_analytics=None,on_dashboard=None,on_batch=None,
                 on_reports=None,on_settings=None,on_history=None,on_collapse=None,on_users=None,permissions=None):
        super().__init__(parent,width=238,corner_radius=0,fg_color=Theme.colors.SIDEBAR_BACKGROUND)
        self.grid_propagate(False)
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(3,weight=1)
        self.on_collapse=on_collapse
        brand=ctk.CTkFrame(self,fg_color="transparent")
        brand.grid(row=0,column=0,padx=14,pady=(12,6),sticky="ew")
        brand.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(brand,text="◉  MRS",text_color="#FFFFFF",
                     font=ctk.CTkFont("Georgia",27,"bold"),anchor="w").grid(row=0,column=0,sticky="w")
        ctk.CTkButton(brand,text="‹",width=32,height=30,corner_radius=10,fg_color="#4A2A69",
                      hover_color="#65408A",command=self.on_collapse).grid(row=0,column=1,sticky="e")
        ctk.CTkLabel(self,text="SPEECH ANALYTICS | QUALITY",text_color="#D7C6EB",
                     font=ctk.CTkFont("Segoe UI",9,"bold")).grid(row=1,column=0,padx=18,pady=(0,10),sticky="w")
        ctk.CTkLabel(self,text="MENÚ",text_color="#CDBEE0",
                     font=ctk.CTkFont("Segoe UI",12,"bold"),anchor="w").grid(row=2,column=0,padx=18,pady=(0,5),sticky="ew")
        self.menu_scroll=ctk.CTkScrollableFrame(
            self,width=210,fg_color="transparent",corner_radius=0,
            scrollbar_button_color="#64428A",scrollbar_button_hover_color="#916BC1")
        self.menu_scroll.grid(row=3,column=0,padx=(4,3),pady=(0,4),sticky="nsew")
        self.menu_scroll.grid_columnconfigure(0,weight=1)
        items=[
            ("home","⌂   Inicio",on_home),
            ("users","♙   Usuarios",on_users),
            ("projects","▣   Nuevo Proyecto",on_new_project),
            ("projects","▰   Abrir Proyecto",on_open_project),
            ("audio","♫   Gestión de Audios",on_audio),
            ("transcriptions","▤   Transcripciones",on_transcriptions),
            ("analytics","▥   Analytics de Llamadas",on_analytics),
            ("dashboard","◕   Dashboard",on_dashboard),
            ("batch","▶   Procesamiento por lotes",on_batch),
            ("reports","▧   Reportes",on_reports),
            ("settings","⚙   Configuración",on_settings),
            ("history","◷   Historial",on_history)]
        allowed=PERMISSIONS.get(permissions,frozenset())
        for permission,label,callback in items:
            if permission in allowed:
                self.create_menu_button(label,callback,selected=(permission=="home"))
        footer=ctk.CTkFrame(self,fg_color="transparent")
        footer.grid(row=4,column=0,pady=(1,7),sticky="ew")
        ctk.CTkLabel(footer,text="MRS CONSULTORES  |  USO INTERNO",
                     text_color="#D7B9E6",font=ctk.CTkFont("Segoe UI",9)).pack()

    def create_menu_button(self,text,command,selected=False):
        button=ctk.CTkButton(
            self.menu_scroll,text=text,height=35,corner_radius=9,anchor="w",
            command=command if callable(command) else self.not_available,
            fg_color=Theme.colors.SIDEBAR_SELECTED if selected else "transparent",
            hover_color=Theme.colors.SIDEBAR_HOVER,
            text_color=Theme.colors.SIDEBAR_TEXT_ACTIVE if selected else Theme.colors.SIDEBAR_TEXT,
            font=ctk.CTkFont("Segoe UI",12,"bold" if selected else "normal"))
        button.grid(row=len(self.menu_scroll.winfo_children()),column=0,padx=(6,3),pady=2,sticky="ew")
        return button

    def not_available(self):
        print("Módulo todavía no disponible.")
