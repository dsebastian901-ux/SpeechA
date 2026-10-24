"""
============================================================
MRS Speech Analytics Professional
Ventana principal
============================================================
"""

from __future__ import annotations

import customtkinter as ctk

from app.config.settings import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)

from app.ui.components.top_bar import TopBar
from app.ui.components.left_menu import LeftMenu
from app.ui.components.status_bar import StatusBar
from app.ui.components.work_area import WorkArea


class MainWindow(ctk.CTk):
    """
    Ventana principal de MRS Speech Analytics.

    Coordina:
    - Barra superior
    - Menú lateral
    - Área de trabajo
    - Barra de estado
    """

    def __init__(self):
        super().__init__()

        self.configure_window()
        self.configure_layout()
        self.menu_expanded = True
        self._menu_hide_job = None
        self.create_components()
        self.after(2200, self.collapse_menu)

    # ========================================================
    # CONFIGURACIÓN DE VENTANA
    # ========================================================

    def configure_window(self):
        """
        Configura las propiedades principales
        de la ventana.
        """

        self.title(
            "MRS Speech Analytics Professional"
        )

        self.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )

        self.minsize(
            WINDOW_MIN_WIDTH,
            WINDOW_MIN_HEIGHT,
        )

    # ========================================================
    # LAYOUT PRINCIPAL
    # ========================================================

    def configure_layout(self):
        """
        Configura filas y columnas principales.
        """

        # Menú lateral
        self.grid_columnconfigure(
            0,
            weight=0,
        )

        # Área principal
        self.grid_columnconfigure(
            1,
            weight=1,
        )

        # Barra superior
        self.grid_rowconfigure(
            0,
            weight=0,
        )

        # Área central
        self.grid_rowconfigure(
            1,
            weight=1,
        )

        # Barra inferior
        self.grid_rowconfigure(
            2,
            weight=0,
        )

    # ========================================================
    # CREACIÓN DE COMPONENTES
    # ========================================================

    def create_components(self):
        """
        Crea los componentes principales.

        WorkArea debe crearse antes que LeftMenu,
        porque LeftMenu utiliza sus métodos como callbacks.
        """

        self.create_top_bar()

        self.create_work_area()

        self.create_left_menu()

        self.create_status_bar()

    # ========================================================
    # TOP BAR
    # ========================================================

    def create_top_bar(self):
        """Crea la barra superior."""

        self.top_bar = TopBar(
            self
        )

        self.top_bar.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
        )

    # ========================================================
    # WORK AREA
    # ========================================================

    def create_work_area(self):
        """
        Crea el área central donde se muestran
        las diferentes pantallas.
        """

        self.work_area = WorkArea(
            self
        )

        self.work_area.grid(
            row=1,
            column=1,
            sticky="nsew",
        )

    # ========================================================
    # MENÚ LATERAL
    # ========================================================

    def create_left_menu(self):
        """
        Crea el menú lateral y conecta cada botón
        con su correspondiente método de WorkArea.
        """

        self.left_menu = LeftMenu(

            self,

            # ------------------------------------------------
            # INICIO
            # ------------------------------------------------

            on_home=(
                self.work_area.show_home
            ),

            # ------------------------------------------------
            # PROYECTOS
            # ------------------------------------------------

            on_new_project=(
                self.work_area.show_new_project
            ),

            on_open_project=(
                self.work_area.show_open_project
            ),

            # ------------------------------------------------
            # AUDIOS
            # ------------------------------------------------

            on_audio=(
                self.work_area.show_audio_view
            ),

            # ------------------------------------------------
            # TRANSCRIPCIONES
            # ------------------------------------------------

            on_transcriptions=(
                self.work_area.show_transcriptions
            ),

            # ------------------------------------------------
            # ANALYTICS
            # ------------------------------------------------

            on_analytics=(
                self.work_area.show_analytics
            ),

            # ------------------------------------------------
            # DASHBOARD
            # ------------------------------------------------

            on_dashboard=(
                self.work_area.show_dashboard
            ),

            # ------------------------------------------------
            # PROCESAMIENTO POR LOTES
            # ------------------------------------------------

            on_batch=(
                self.work_area.show_batch
            ),

            # ------------------------------------------------
            # REPORTES
            # ------------------------------------------------

            on_reports=(
                self.work_area.show_reports
            ),

            # ------------------------------------------------
            # CONFIGURACIÓN
            # ------------------------------------------------

            on_settings=(
                self.work_area.show_settings
            ),

            # ------------------------------------------------
            # HISTORIAL
            # ------------------------------------------------

            on_history=(
                self.work_area.show_history
            ),
            on_collapse=self.collapse_menu,
        )

        self.left_menu.grid(row=1,column=0,sticky="nsw")
        self.left_menu.bind("<Leave>", self._schedule_hide)
        self.menu_tab = ctk.CTkButton(self, text="=", width=25, height=38, corner_radius=8,
                                      fg_color="#4B276B", hover_color="#6B3E8E",
                                      font=ctk.CTkFont("Segoe UI", 16, "bold"),
                                      command=self.expand_menu)


    def collapse_menu(self):
        if not getattr(self, "menu_expanded", False): return
        self.left_menu.grid_remove()
        self.grid_columnconfigure(0, minsize=27)
        self.menu_tab.grid(row=1,column=0,padx=(1,0),pady=(9,0),sticky="nw")
        self.menu_expanded=False

    def expand_menu(self):
        if getattr(self, "menu_expanded", False): return
        self.menu_tab.grid_remove()
        self.grid_columnconfigure(0, minsize=0)
        self.left_menu.grid(row=1,column=0,sticky="nsw")
        self.menu_expanded=True

    def _schedule_hide(self, event=None):
        if self._menu_hide_job:
            try: self.after_cancel(self._menu_hide_job)
            except Exception: pass
        self._menu_hide_job=self.after(700,self.collapse_menu)

    # ========================================================
    # STATUS BAR
    # ========================================================

    def create_status_bar(self):
        """
        Crea la barra inferior de estado.
        """

        self.status_bar = StatusBar(
            self
        )

        self.status_bar.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
        )