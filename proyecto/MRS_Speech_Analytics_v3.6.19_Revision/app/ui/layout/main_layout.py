"""
============================================================
MRS Speech Analytics Professional
Layout principal
============================================================
"""

from __future__ import annotations

import customtkinter as ctk

from app.core import project_manager

from app.ui.layout.app_header import AppHeader
from app.ui.layout.sidebar import Sidebar, SidebarItem

from app.ui.themes import Theme

from app.ui.views.dashboard_view import DashboardView
from app.ui.views.new_project_view import NewProjectView
from app.ui.views.open_project_view import OpenProjectView
from app.ui.views.audio_view import AudioView
from app.ui.views.transcription_view import TranscriptionView


class MainLayout(ctk.CTkFrame):
    """
    Layout principal de MRS Speech Analytics.

    Contiene:
    - Header
    - Sidebar
    - Área de trabajo
    - Navegación entre vistas
    """

    def __init__(
        self,
        master,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
            **kwargs,
        )

        self.current_view = None

        # =====================================================
        # GRID PRINCIPAL
        # =====================================================

        self.grid_columnconfigure(
            0,
            weight=0,
        )

        self.grid_columnconfigure(
            1,
            weight=1,
        )

        self.grid_rowconfigure(
            0,
            weight=0,
        )

        self.grid_rowconfigure(
            1,
            weight=1,
        )

        # =====================================================
        # HEADER
        # =====================================================

        self.header = AppHeader(
            self
        )

        self.header.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        # =====================================================
        # MENÚ LATERAL
        # =====================================================

        sidebar_items = [

            SidebarItem(
                "home",
                "Inicio",
                "home",
                "PRINCIPAL",
                self.show_dashboard,
            ),

            SidebarItem(
                "new_project",
                "Nuevo Proyecto",
                "folder",
                "PROYECTOS",
                self.show_new_project,
            ),

            SidebarItem(
                "open_project",
                "Abrir Proyecto",
                "folder",
                "PROYECTOS",
                self.show_open_project,
            ),

            SidebarItem(
                "audio",
                "Gestión de Audios",
                "microphone",
                "ANÁLISIS",
                self.show_audio_view,
            ),

            SidebarItem(
                "transcriptions",
                "Transcripciones",
                "document",
                "ANÁLISIS",
                self.show_transcriptions,
            ),

            SidebarItem(
                "analytics",
                "Analytics de Llamadas",
                "analytics",
                "ANÁLISIS",
                self.show_not_implemented,
            ),

            SidebarItem(
                "reports",
                "Reportes",
                "reports",
                "BUSINESS INTELLIGENCE",
                self.show_not_implemented,
            ),

            SidebarItem(
                "dashboard",
                "Dashboard",
                "dashboard",
                "BUSINESS INTELLIGENCE",
                self.show_dashboard,
            ),

            SidebarItem(
                "settings",
                "Configuración",
                "settings",
                "CONFIGURACIÓN",
                self.show_not_implemented,
            ),

            SidebarItem(
                "users",
                "Usuarios",
                "users",
                "CONFIGURACIÓN",
                self.show_not_implemented,
            ),

            SidebarItem(
                "history",
                "Historial",
                "history",
                "CONFIGURACIÓN",
                self.show_not_implemented,
            ),
        ]

        self.sidebar = Sidebar(
            self,
            items=sidebar_items,
            active_key="home",
        )

        self.sidebar.grid(
            row=1,
            column=0,
            sticky="nsw",
        )

        # =====================================================
        # ÁREA DE TRABAJO
        # =====================================================

        self.workspace = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.workspace.grid(
            row=1,
            column=1,
            sticky="nsew",
        )

        self.workspace.grid_columnconfigure(
            0,
            weight=1,
        )

        self.workspace.grid_rowconfigure(
            0,
            weight=1,
        )

        # =====================================================
        # VISTA INICIAL
        # =====================================================

        self.show_dashboard()

    # =========================================================
    # UTILIDADES
    # =========================================================

    def clear_workspace(self):
        """
        Elimina la vista actualmente cargada.
        """

        if self.current_view is not None:

            try:
                self.current_view.destroy()
            except Exception:
                pass

            self.current_view = None

    def mount_view(
        self,
        view_class,
        **kwargs,
    ):
        """
        Carga una vista dentro del área de trabajo.
        """

        self.clear_workspace()

        self.current_view = view_class(
            self.workspace,
            **kwargs,
        )

        self.current_view.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    # =========================================================
    # INICIO / DASHBOARD
    # =========================================================

    def show_dashboard(self):
        """
        Muestra el Dashboard principal.
        """

        self.mount_view(
            DashboardView
        )

    # =========================================================
    # NUEVO PROYECTO
    # =========================================================

    def show_new_project(self):
        """
        Muestra la pantalla de creación de proyectos.
        """

        self.mount_view(
            NewProjectView,
            on_project_created=self.on_project_created,
        )

    def on_project_created(
        self,
        project_data,
    ):
        """
        Se ejecuta cuando un nuevo proyecto fue creado.
        """

        if project_data:

            project_manager.set_current_project(
                project_data
            )

        self.show_audio_view()

        self.set_sidebar_active(
            "audio"
        )

    # =========================================================
    # ABRIR PROYECTO
    # =========================================================

    def show_open_project(self):
        """
        Muestra la pantalla para abrir proyectos existentes.
        """

        self.mount_view(
            OpenProjectView,
            on_project_opened=self.on_project_opened,
        )

    def on_project_opened(
        self,
        project_data,
    ):
        """
        Se ejecuta cuando un proyecto existente fue abierto.
        """

        if project_data:

            project_manager.set_current_project(
                project_data
            )

        self.show_audio_view()

        self.set_sidebar_active(
            "audio"
        )

    # =========================================================
    # GESTIÓN DE AUDIOS
    # =========================================================

    def show_audio_view(self):
        """
        Muestra Gestión de Audios.
        """

        self.mount_view(
            AudioView
        )

    # =========================================================
    # TRANSCRIPCIONES
    # =========================================================

    def show_transcriptions(self):
        """
        Muestra la nueva pantalla de Transcripciones.
        """

        self.mount_view(
            TranscriptionView
        )

    # =========================================================
    # PANTALLAS PENDIENTES
    # =========================================================

    def show_not_implemented(self):
        """
        Pantalla temporal para módulos todavía
        no desarrollados.
        """

        self.clear_workspace()

        container = ctk.CTkFrame(
            self.workspace,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )

        container.grid(
            row=0,
            column=0,
            padx=30,
            pady=30,
            sticky="nsew",
        )

        container.grid_columnconfigure(
            0,
            weight=1,
        )

        container.grid_rowconfigure(
            0,
            weight=1,
        )

        label = ctk.CTkLabel(
            container,
            text=(
                "Módulo en desarrollo\n\n"
                "Esta función se habilitará "
                "en una próxima etapa."
            ),
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=18,
                weight="bold",
            ),
            justify="center",
        )

        label.grid(
            row=0,
            column=0,
        )

        self.current_view = container

    # =========================================================
    # SIDEBAR
    # =========================================================

    def set_sidebar_active(
        self,
        key,
    ):
        """
        Actualiza visualmente la opción seleccionada
        del menú lateral.
        """

        try:

            if hasattr(
                self.sidebar,
                "set_active",
            ):

                self.sidebar.set_active(
                    key
                )

        except Exception:
            pass