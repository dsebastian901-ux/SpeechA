"""
============================================================
MRS Speech Analytics Professional
Componente: Work Area
============================================================
"""

import customtkinter as ctk
from pathlib import Path
from PIL import Image

from app.ui.themes import Theme

from app.ui.views.new_project_view import NewProjectView
from app.ui.views.open_project_view import OpenProjectView
from app.ui.views.audio_view import AudioView
from app.ui.views.transcription_view import TranscriptionView
from app.ui.views.analytics_view import AnalyticsView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.audio_player_view import AudioPlayerView
from app.ui.views.batch_view import BatchView
from app.ui.views.reports_view import ReportsView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView


class WorkArea(ctk.CTkFrame):
    """
    Área principal de trabajo de MRS Speech Analytics.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
            **kwargs,
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_view = None

        self.show_home()

    # =========================================================
    # LIMPIAR
    # =========================================================

    def clear(self):
        if self.current_view is not None:
            try:
                self.current_view.destroy()
            except Exception:
                pass

            self.current_view = None

        for widget in self.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

    # =========================================================
    # MONTAR VISTA
    # =========================================================

    def mount_view(self, view_class, **kwargs):
        self.clear()

        self.current_view = view_class(
            self,
            **kwargs,
        )

        self.current_view.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        return self.current_view

    # =========================================================
    # INICIO
    # =========================================================

    def show_home(self):
        self.clear()
        root = ctk.CTkFrame(self, fg_color="#F6F3FA", corner_radius=0)
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        assets_path = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_path / "mrs_logo.jpg"
        round_logo_path = assets_path / "mrs_logo_round.png"

        # Cabecera limpia de marca
        header = ctk.CTkFrame(root, fg_color="#FFFFFF", corner_radius=16,
                              border_width=1, border_color="#E7E0EE")
        header.grid(row=0, column=0, padx=20, pady=(16, 9), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        try:
            logo_img = Image.open(logo_path)
            self._home_logo = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(54, 54))
            ctk.CTkLabel(header, text="", image=self._home_logo).grid(row=0, column=0, rowspan=2, padx=(16, 10), pady=9)
        except Exception:
            ctk.CTkLabel(header, text="MRS", text_color="#6E43B7",
                         font=ctk.CTkFont("Segoe UI", 20, "bold")).grid(row=0, column=0, rowspan=2, padx=16)
        ctk.CTkLabel(header, text="MRS Speech Analytics Professional", text_color="#321755",
                     font=ctk.CTkFont("Segoe UI", 23, "bold"), anchor="w").grid(row=0, column=1, pady=(12, 0), sticky="sw")
        ctk.CTkLabel(header, text="Transcribe  |  Analiza  |  Evalúa  |  Genera resultados", text_color="#725F80",
                     font=ctk.CTkFont("Segoe UI", 10), anchor="w").grid(row=1, column=1, pady=(0, 12), sticky="nw")
        ctk.CTkLabel(header, text="La calidad nos hace mejores", text_color="#6A3A86",
                     font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic")).grid(row=0, column=2, rowspan=2, padx=18)
        badge = ctk.CTkFrame(header, fg_color="#EAF7EF", corner_radius=17)
        badge.grid(row=0, column=3, rowspan=2, padx=(0, 16), pady=15)
        ctk.CTkLabel(badge, text="●  Sistema listo", text_color="#20814C",
                     font=ctk.CTkFont("Segoe UI", 10, "bold")).pack(padx=13, pady=7)

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        body.grid_columnconfigure(0, weight=3, uniform="main")
        body.grid_columnconfigure(1, weight=2, uniform="main")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, padx=(0, 7), sticky="nsew")
        left.grid_columnconfigure(0, weight=1)

        # Hero: el logo se integra sobre el mismo fondo lavanda para evitar efecto de caja.
        hero = ctk.CTkFrame(left, fg_color="#F4ECFB", corner_radius=20,
                            border_width=1, border_color="#E1D4ED", height=236)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        hero.grid_propagate(False)
        hero.grid_columnconfigure(0, weight=3)
        hero.grid_columnconfigure(1, weight=2)
        text = ctk.CTkFrame(hero, fg_color="transparent")
        text.grid(row=0, column=0, padx=(24, 4), pady=17, sticky="nsew")
        ctk.CTkLabel(text, text="B I E N V E N I D A", text_color="#7043A2",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"), anchor="w").pack(anchor="w")
        ctk.CTkLabel(text, text="MRS Speech Analytics Professional", text_color="#321755",
                     font=ctk.CTkFont("Segoe UI", 23, "bold"), justify="left", anchor="w", wraplength=430).pack(anchor="w", pady=(7, 5))
        ctk.CTkLabel(text, text="Centro de control para el análisis de calidad en llamadas.", text_color="#654D78",
                     font=ctk.CTkFont("Segoe UI", 11), anchor="w").pack(anchor="w")

        features = ctk.CTkFrame(text, fg_color="transparent")
        features.pack(fill="x", pady=(14, 0))
        feature_data = [("transcribe", "Transcribe", "con precisión"), ("analyze", "Analiza", "con inteligencia"),
                        ("evaluate", "Evalúa", "cumplimiento"), ("results", "Genera", "resultados")]
        self._feature_icons = []
        for i, (icon_name, tit, sub) in enumerate(feature_data):
            f = ctk.CTkFrame(features, fg_color="transparent")
            f.grid(row=0, column=i, padx=(0, 13), sticky="w")
            try:
                icon_img = Image.open(assets_path / f"icon_{icon_name}.png")
                icon = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(25, 25))
                self._feature_icons.append(icon)
                icon_bg = ctk.CTkFrame(f, width=36, height=36, corner_radius=18, fg_color="#E3D5F4")
                icon_bg.pack()
                icon_bg.pack_propagate(False)
                ctk.CTkLabel(icon_bg, text="", image=icon).place(relx=.5, rely=.5, anchor="center")
            except Exception:
                ctk.CTkLabel(f, text="•", width=36, height=36, corner_radius=18, fg_color="#E3D5F4",
                             text_color="#68409B", font=ctk.CTkFont("Segoe UI", 14, "bold")).pack()
            ctk.CTkLabel(f, text=tit, text_color="#3C205F", font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(pady=(3, 0))
            ctk.CTkLabel(f, text=sub, text_color="#766485", font=ctk.CTkFont("Segoe UI", 8)).pack()

        visual = ctk.CTkFrame(hero, fg_color="#E8DCF4", corner_radius=90, width=190, height=190, border_width=1, border_color="#D9C8EA")
        visual.grid(row=0, column=1, padx=(8, 22), pady=20)
        visual.grid_propagate(False)
        try:
            logo_img2 = Image.open(round_logo_path)
            self._hero_logo = ctk.CTkImage(light_image=logo_img2, dark_image=logo_img2, size=(150, 150))
            logo_halo = ctk.CTkFrame(visual, width=164, height=164, corner_radius=82, fg_color="#EEE4F7",
                                     border_width=2, border_color="#CDB7E2")
            logo_halo.place(relx=.5, rely=.45, anchor="center")
            logo_halo.pack_propagate(False)
            ctk.CTkLabel(logo_halo, text="", image=self._hero_logo, fg_color="transparent").place(relx=.5, rely=.5, anchor="center")
            wave_frame = ctk.CTkFrame(visual, fg_color="transparent", width=120, height=24)
            wave_frame.place(relx=.5, rely=.91, anchor="center")
            wave_frame.pack_propagate(False)
            bars = (5, 10, 16, 9, 20, 13, 7, 15, 10, 5)
            for idx, bar_h in enumerate(bars):
                bar = ctk.CTkFrame(wave_frame, width=4, height=bar_h, corner_radius=2, fg_color="#8658AA")
                bar.place(x=8 + idx * 11, rely=.5, anchor="w")
        except Exception:
            ctk.CTkLabel(visual, text="MRS", text_color="#5E328C",
                         font=ctk.CTkFont("Segoe UI", 28, "bold")).place(relx=.5, rely=.5, anchor="center")

        cards = ctk.CTkFrame(left, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 9))
        for c in range(3): cards.grid_columnconfigure(c, weight=1, uniform="cards")
        data = [("PR", "PROYECTOS", "Organiza tus análisis", "#EFE7FA", "#6F47A8", self.show_open_project),
                ("AU", "AUDIOS", "Gestiona grabaciones", "#FAE9F1", "#B84F7F", self.show_audio_view),
                ("CA", "CALIDAD", "Consulta resultados", "#E8F0FC", "#467DC4", self.show_dashboard)]
        for c, (ico, title, sub, bg, accent, cmd) in enumerate(data):
            card = ctk.CTkButton(cards, text=f"{ico}   {title}\n       {sub}", command=cmd, fg_color=bg,
                                 hover_color="#F8F4FB", text_color=accent, height=82, corner_radius=15,
                                 anchor="w", font=ctk.CTkFont("Segoe UI", 12, "bold"), border_width=1,
                                 border_color="#E5DDEA")
            card.grid(row=0, column=c, padx=4, sticky="ew")

        flow = ctk.CTkFrame(left, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E7E0EE")
        flow.grid(row=2, column=0, sticky="ew", pady=(0, 9))
        ctk.CTkLabel(flow, text="Flujo de trabajo", text_color="#321755",
                     font=ctk.CTkFont("Segoe UI", 14, "bold")).pack(anchor="w", padx=17, pady=(11, 6))
        steps = ctk.CTkFrame(flow, fg_color="transparent")
        steps.pack(fill="x", padx=15, pady=(0, 11))
        for i, label in enumerate(("Abre o crea\nun proyecto", "Carga\naudios", "Procesa\nel lote", "Revisa Analytics\ny reportes"), 1):
            steps.grid_columnconfigure(i-1, weight=1)
            box = ctk.CTkFrame(steps, fg_color="transparent")
            box.grid(row=0, column=i-1, sticky="ew")
            ctk.CTkLabel(box, text=str(i), width=32, height=32, corner_radius=16,
                         fg_color=("#E5D6FA", "#E9DDFB", "#F5DDEB", "#DDE9FF")[i-1],
                         text_color="#542C82", font=ctk.CTkFont("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(box, text=label, text_color="#44324F", font=ctk.CTkFont("Segoe UI", 9),
                         justify="left").pack(side="left")

        insight = ctk.CTkFrame(left, fg_color="#3A185E", corner_radius=16, height=62)
        insight.grid(row=3, column=0, sticky="ew")
        insight.grid_propagate(False)
        insight.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(insight, text="ANALIZAR HOY  |  CONSTRUIR UN MEJOR MAÑANA", text_color="#FFFFFF",
                     font=ctk.CTkFont("Segoe UI", 11, "bold")).grid(row=0, column=0, padx=18, pady=(12, 1), sticky="w")
        ctk.CTkLabel(insight, text="Speech Analytics · Calidad · Mejora continua", text_color="#D8C7E8",
                     font=ctk.CTkFont("Segoe UI", 9)).grid(row=1, column=0, padx=18, pady=(0, 10), sticky="w")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, padx=(7, 0), sticky="nsew")
        right.grid_columnconfigure((0, 1), weight=1)

        quick = ctk.CTkFrame(right, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E7E0EE")
        quick.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 9))
        quick.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(quick, text="ACCIONES RÁPIDAS", text_color="#321755",
                     font=ctk.CTkFont("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 7), sticky="w")
        buttons = [("+  Nuevo Proyecto", self.show_new_project, "#7850C6", "#6942B5"),
                   ("Abrir Proyecto", self.show_open_project, "#4E86C6", "#3E74B2"),
                   ("Procesar por lotes", self.show_batch, "#459763", "#378653"),
                   ("Ver Dashboard", self.show_dashboard, "#D9873D", "#C6762E")]
        for i, (label, cmd, color, hover) in enumerate(buttons):
            ctk.CTkButton(quick, text=label, command=cmd, height=61, fg_color=color, hover_color=hover,
                          corner_radius=12, font=ctk.CTkFont("Segoe UI", 11, "bold")).grid(row=1+i//2, column=i%2, padx=6, pady=5, sticky="ew")
        ctk.CTkFrame(quick, fg_color="transparent", height=5).grid(row=3, column=0)

        state = ctk.CTkFrame(right, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E7E0EE")
        state.grid(row=1, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(state, text="Estado del sistema", text_color="#321755",
                     font=ctk.CTkFont("Segoe UI", 14, "bold")).pack(anchor="w", padx=17, pady=(13, 7))
        for label in ("Motor de transcripción disponible", "Analytics de calidad disponible",
                      "Procesamiento por lotes disponible", "Generación de reportes disponible"):
            ctk.CTkLabel(state, text="●   " + label, text_color="#278A52",
                         font=ctk.CTkFont("Segoe UI", 9)).pack(anchor="w", padx=19, pady=4)
        ctk.CTkLabel(state, text="MRS Consultores  |  Uso interno  |  v0.1.0", text_color="#8A7898",
                     font=ctk.CTkFont("Segoe UI", 8)).pack(anchor="w", padx=19, pady=(9, 12))

        footer = ctk.CTkFrame(right, fg_color="#F1E9F7", corner_radius=16, border_width=1, border_color="#E2D5EC")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(9, 0))
        ctk.CTkLabel(footer, text="MRS  |  SPEECH ANALYTICS  |  QUALITY", text_color="#63377F",
                     font=ctk.CTkFont("Segoe UI", 10, "bold")).pack(pady=(9, 2))
        ctk.CTkLabel(footer, text="La calidad nos hace mejores", text_color="#9279A2",
                     font=ctk.CTkFont(family="Segoe UI", size=9, slant="italic")).pack(pady=(0, 9))
        self.current_view = root

    # =========================================================
    # NUEVO PROYECTO
    # =========================================================

    def show_new_project(self):
        self.mount_view(
            NewProjectView,
            on_project_created=self.on_project_created,
        )

    def on_project_created(self, project_data):
        self.show_home()

    # =========================================================
    # ABRIR PROYECTO
    # =========================================================

    def show_open_project(self):
        self.mount_view(
            OpenProjectView,
            on_project_opened=self.on_project_opened,
        )

    def on_project_opened(self, project_data):
        self.show_home()

    # =========================================================
    # AUDIOS
    # =========================================================

    def show_audio_view(self):
        self.mount_view(
            AudioView
        )

    def show_audio(self):
        self.show_audio_view()

    # =========================================================
    # TRANSCRIPCIONES
    # =========================================================

    def show_transcriptions(self):
        self.mount_view(
            TranscriptionView
        )

    def show_transcription_view(self):
        self.show_transcriptions()

    # =========================================================
    # ANALYTICS
    # =========================================================

    def show_analytics(self):
        self.mount_view(
            AnalyticsView
        )

    def show_analytics_view(self):
        self.show_analytics()

    # =========================================================
    # DASHBOARD
    # =========================================================

    def show_dashboard(self):
        self.mount_view(
            DashboardView
        )

    def show_dashboard_view(self):
        self.show_dashboard()

    def show_audio_player(self, records=None, title="Audios filtrados"):
        self.mount_view(AudioPlayerView, records=records or [], title=title)

    # =========================================================
    # PROCESAMIENTO POR LOTES
    # =========================================================

    def show_batch(self):
        self.mount_view(
            BatchView
        )

    # =========================================================
    # REPORTES
    # =========================================================

    def show_reports(self):
        self.mount_view(
            ReportsView
        )

    # =========================================================
    # HISTORIAL
    # =========================================================

    def show_history(self):
        self.mount_view(
            HistoryView
        )

    # =========================================================
    # CONFIGURACIÓN
    # =========================================================

    def show_settings(self):
        self.mount_view(
            SettingsView
        )

    # =========================================================
    # USUARIOS
    # =========================================================

    def show_users(self):
        self.show_placeholder(
            title="Usuarios",
            subtitle=(
                "El módulo de usuarios "
                "se encuentra en preparación."
            ),
        )

    # =========================================================
    # PLACEHOLDER
    # =========================================================

    def show_placeholder(
        self,
        title,
        subtitle="",
    ):
        self.clear()

        container = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        container.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(
            container,
            fg_color=Theme.colors.SURFACE,
            corner_radius=18,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        card.grid(
            row=0,
            column=0,
            padx=40,
            pady=40,
            sticky="nsew",
        )

        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        content = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )

        content.grid(
            row=0,
            column=0,
            padx=40,
            pady=40,
        )

        ctk.CTkLabel(
            content,
            text=title,
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=26,
                weight="bold",
            ),
        ).pack(
            pady=(0, 8)
        )

        ctk.CTkLabel(
            content,
            text=subtitle,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
            ),
        ).pack()

        self.current_view = container