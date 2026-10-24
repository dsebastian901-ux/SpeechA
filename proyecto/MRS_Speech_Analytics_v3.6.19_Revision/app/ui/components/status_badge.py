import customtkinter as ctk
from app.ui.themes import Theme

class SystemStatusBadge(ctk.CTkFrame):
    STATUS_STYLES = {
        "ready": (Theme.colors.SUCCESS, "Sistema listo", "Todo funcionando correctamente"),
        "processing": (Theme.colors.INFO, "Procesando", "Analizando audios"),
        "warning": (Theme.colors.WARNING, "Atención", "Requiere revisión"),
        "error": (Theme.colors.ERROR, "Error", "Se detectó un problema"),
    }

    def __init__(self, master, status="ready", width=280, height=62, **kwargs):
        super().__init__(master, width=width, height=height, fg_color=Theme.colors.SURFACE,
                         border_color=Theme.colors.BORDER_LIGHT, border_width=1,
                         corner_radius=Theme.dimensions.RADIUS_LARGE, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self.dot = ctk.CTkLabel(self, text="●", width=18,
                                font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=18, weight="bold"))
        self.dot.grid(row=0, column=0, rowspan=2, padx=(Theme.spacing.LG, Theme.spacing.SM))
        self.title_label = ctk.CTkLabel(self, text="", text_color=Theme.colors.TEXT_PRIMARY,
                                        font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=13, weight="bold"), anchor="w")
        self.title_label.grid(row=0, column=1, padx=(0, Theme.spacing.LG), pady=(10, 0), sticky="sw")
        self.detail_label = ctk.CTkLabel(self, text="", text_color=Theme.colors.TEXT_SECONDARY,
                                         font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=11), anchor="w")
        self.detail_label.grid(row=1, column=1, padx=(0, Theme.spacing.LG), pady=(0, 10), sticky="nw")
        self.set_status(status)

    def set_status(self, status, title=None, detail=None):
        color, default_title, default_detail = self.STATUS_STYLES.get(status, self.STATUS_STYLES["ready"])
        self.dot.configure(text_color=color)
        self.title_label.configure(text=title or default_title)
        self.detail_label.configure(text=detail or default_detail)
