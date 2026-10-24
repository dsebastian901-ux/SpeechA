import customtkinter as ctk
from app.ui.themes import Theme

class UserAvatar(ctk.CTkFrame):
    def __init__(self, master, initials="DA", name="Daniela", role="Supervisor", command=None, **kwargs):
        super().__init__(master, fg_color=Theme.colors.TRANSPARENT, corner_radius=0, **kwargs)
        self.command = command
        size = Theme.dimensions.AVATAR_SIZE
        self.avatar_button = ctk.CTkButton(self, text=initials[:2].upper(), width=size, height=size,
                                           corner_radius=size // 2, fg_color=Theme.colors.PRIMARY,
                                           hover_color=Theme.colors.PRIMARY_HOVER,
                                           text_color=Theme.colors.TEXT_ON_PRIMARY,
                                           font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=14, weight="bold"),
                                           command=self._on_click)
        self.avatar_button.grid(row=0, column=0, rowspan=2, padx=(0, Theme.spacing.SM))
        self.name_label = ctk.CTkLabel(self, text=name, text_color=Theme.colors.TEXT_PRIMARY,
                                       font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=13, weight="bold"), anchor="w")
        self.name_label.grid(row=0, column=1, sticky="sw")
        self.role_label = ctk.CTkLabel(self, text=role, text_color=Theme.colors.TEXT_SECONDARY,
                                       font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=11), anchor="w")
        self.role_label.grid(row=1, column=1, sticky="nw")
        ctk.CTkButton(self, text="⌄", width=28, height=32, fg_color=Theme.colors.TRANSPARENT,
                      hover_color=Theme.colors.PRIMARY_LIGHT, text_color=Theme.colors.TEXT_SECONDARY,
                      corner_radius=8, command=self._on_click).grid(row=0, column=2, rowspan=2, padx=(Theme.spacing.XS, 0))

    def _on_click(self):
        if callable(self.command):
            self.command()
