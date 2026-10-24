from pathlib import Path
from typing import Callable, Optional, Sequence
import customtkinter as ctk
from app.ui.components.avatar import UserAvatar
from app.ui.components.logo import MRSLogo
from app.ui.components.status_badge import SystemStatusBadge
from app.ui.themes import Theme

class HeaderSelector(ctk.CTkFrame):
    def __init__(self, master, title: str, values: Sequence[str], value="", width=170,
                 command: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, width=width, height=62, fg_color=Theme.colors.TRANSPARENT, corner_radius=0, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, text_color=Theme.colors.TEXT_SECONDARY,
                     font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=11), anchor="w").grid(
                         row=0, column=0, padx=Theme.spacing.SM, pady=(2, 0), sticky="ew")
        self.variable = ctk.StringVar(value=value or (values[0] if values else ""))
        self.menu = ctk.CTkOptionMenu(self, values=list(values) if values else [""], variable=self.variable,
                                      command=command, width=width - 12, height=34,
                                      fg_color=Theme.colors.SURFACE, button_color=Theme.colors.PRIMARY_LIGHT,
                                      button_hover_color=Theme.colors.SIDEBAR_SELECTED,
                                      text_color=Theme.colors.TEXT_PRIMARY,
                                      dropdown_fg_color=Theme.colors.SURFACE,
                                      dropdown_hover_color=Theme.colors.PRIMARY_LIGHT,
                                      dropdown_text_color=Theme.colors.TEXT_PRIMARY,
                                      font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=13, weight="bold"),
                                      dropdown_font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=12),
                                      corner_radius=Theme.dimensions.RADIUS, anchor="w")
        self.menu.grid(row=1, column=0, padx=Theme.spacing.SM, pady=(0, 4), sticky="ew")

class AppHeader(ctk.CTkFrame):
    def __init__(self, master, logo_path=None,
                 project_values=("004 - Bradescard",), client_values=("Bradescard",),
                 model_values=("small", "medium", "large-v3"),
                 selected_project="004 - Bradescard", selected_client="Bradescard",
                 selected_model="large-v3", user_name="Daniela", user_role="Supervisor",
                 user_initials="DA", **kwargs):
        super().__init__(master, height=96, fg_color=Theme.colors.HEADER_BACKGROUND, corner_radius=0, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.logo = MRSLogo(self, image_path=logo_path or self.find_default_logo())
        self.logo.grid(row=0, column=0, padx=(Theme.spacing.LG, Theme.spacing.XL), pady=Theme.spacing.SM, sticky="w")

        center = ctk.CTkFrame(self, fg_color=Theme.colors.TRANSPARENT)
        center.grid(row=0, column=1, sticky="nsew", pady=Theme.spacing.SM)
        center.grid_columnconfigure(3, weight=1)

        self.project_selector = HeaderSelector(center, "Proyecto", project_values, selected_project, 190)
        self.project_selector.grid(row=0, column=0, padx=Theme.spacing.XS)
        self.client_selector = HeaderSelector(center, "Cliente", client_values, selected_client, 150)
        self.client_selector.grid(row=0, column=1, padx=Theme.spacing.XS)
        self.model_selector = HeaderSelector(center, "Modelo Whisper", model_values, selected_model, 160)
        self.model_selector.grid(row=0, column=2, padx=Theme.spacing.XS)
        self.status_badge = SystemStatusBadge(center)
        self.status_badge.grid(row=0, column=3, padx=(Theme.spacing.LG, 0), sticky="e")

        actions = ctk.CTkFrame(self, fg_color=Theme.colors.TRANSPARENT)
        actions.grid(row=0, column=2, padx=(Theme.spacing.LG, Theme.spacing.LG), sticky="e")
        ctk.CTkButton(actions, text="☾", width=38, height=38, fg_color=Theme.colors.TRANSPARENT,
                      hover_color=Theme.colors.PRIMARY_LIGHT, text_color=Theme.colors.TEXT_SECONDARY,
                      corner_radius=Theme.dimensions.RADIUS).grid(row=0, column=0, padx=Theme.spacing.XS)
        ctk.CTkButton(actions, text="🔔", width=42, height=38, fg_color=Theme.colors.TRANSPARENT,
                      hover_color=Theme.colors.PRIMARY_LIGHT, text_color=Theme.colors.TEXT_SECONDARY,
                      corner_radius=Theme.dimensions.RADIUS).grid(row=0, column=1, padx=Theme.spacing.XS)
        self.avatar = UserAvatar(actions, initials=user_initials, name=user_name, role=user_role)
        self.avatar.grid(row=0, column=2, padx=(Theme.spacing.MD, 0))

        ctk.CTkFrame(self, height=1, fg_color=Theme.colors.HEADER_BORDER, corner_radius=0).grid(
            row=1, column=0, columnspan=3, sticky="ew")

    @staticmethod
    def find_default_logo():
        project_root = Path(__file__).resolve().parents[3]
        candidates = [
            project_root / "app" / "resources" / "logos" / "mrs_logo.png",
            project_root / "app" / "resources" / "mrs_logo.png",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None
