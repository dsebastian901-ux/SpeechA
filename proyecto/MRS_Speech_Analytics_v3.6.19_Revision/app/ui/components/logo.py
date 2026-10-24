from pathlib import Path
from typing import Optional
import customtkinter as ctk
try:
    from PIL import Image
except ImportError:
    Image = None
from app.ui.themes import Theme

class MRSLogo(ctk.CTkFrame):
    def __init__(self, master, image_path: Optional[str] = None, width: int = 320, height: int = 80, **kwargs):
        super().__init__(master, width=width, height=height, fg_color=Theme.colors.TRANSPARENT, corner_radius=0, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self._image_reference = None
        size = Theme.dimensions.LOGO_SIZE + 14
        image = self._load_logo(image_path, size)
        if image is not None:
            logo = ctk.CTkLabel(self, text="", image=image, width=size, height=size)
        else:
            logo = ctk.CTkLabel(self, text="MRS", width=size, height=size, fg_color=Theme.colors.PRIMARY_LIGHT,
                                text_color=Theme.colors.PRIMARY_DARK, corner_radius=size // 2,
                                font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=15, weight="bold"))
        logo.grid(row=0, column=0, rowspan=3, padx=(0, Theme.spacing.MD), pady=Theme.spacing.XS, sticky="w")
        ctk.CTkLabel(self, text="MRS", text_color=Theme.colors.TEXT_PRIMARY,
                     font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=26, weight="bold"), anchor="w").grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(self, text="Speech Analytics", text_color=Theme.colors.TEXT_PRIMARY,
                     font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=15), anchor="w").grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(self, text="Professional", text_color=Theme.colors.PRIMARY_DARK,
                     fg_color=Theme.colors.PRIMARY_LIGHT, corner_radius=8,
                     font=ctk.CTkFont(family=Theme.fonts.FAMILY, size=11, weight="bold"),
                     padx=8, pady=2).grid(row=2, column=1, sticky="nw", pady=(2, 0))

    def _load_logo(self, image_path: Optional[str], size: int):
        if not image_path or Image is None:
            return None
        path = Path(image_path)
        if not path.exists():
            return None
        try:
            pil_image = Image.open(path).convert("RGBA")
            image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(size, size))
            self._image_reference = image
            return image
        except Exception:
            return None
