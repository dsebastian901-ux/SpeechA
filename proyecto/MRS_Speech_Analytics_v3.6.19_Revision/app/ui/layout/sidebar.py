from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from app.ui.components.icon_factory import IconFactory
from app.ui.themes import Theme


@dataclass(frozen=True)
class SidebarItem:
    key: str
    text: str
    icon: str
    section: str
    command: Optional[Callable[[], None]] = None


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        items,
        active_key="home",
        **kwargs,
    ):
        super().__init__(
            master,
            width=Theme.dimensions.SIDEBAR_WIDTH,
            fg_color=Theme.colors.SIDEBAR_BACKGROUND,
            corner_radius=0,
            **kwargs,
        )

        self.items = list(items)
        self.active_key = active_key
        self.buttons = {}
        self.images = {}

        self.grid_propagate(False)
        self.grid_rowconfigure(0, weight=1)

        self.body = ctk.CTkScrollableFrame(
            self,
            fg_color=Theme.colors.SIDEBAR_BACKGROUND,
            corner_radius=0,
        )
        self.body.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=8,
            pady=(10, 6),
        )
        self.body.grid_columnconfigure(0, weight=1)

        current_section = None
        row = 0

        for item in self.items:
            if item.section != current_section:
                current_section = item.section

                ctk.CTkLabel(
                    self.body,
                    text=current_section,
                    text_color=Theme.colors.PRIMARY,
                    font=ctk.CTkFont(
                        family=Theme.fonts.FAMILY,
                        size=11,
                        weight="bold",
                    ),
                    anchor="w",
                ).grid(
                    row=row,
                    column=0,
                    padx=12,
                    pady=(16, 4),
                    sticky="ew",
                )
                row += 1

            button = self._create_button(item)
            button.grid(
                row=row,
                column=0,
                padx=4,
                pady=2,
                sticky="ew",
            )

            self.buttons[item.key] = button
            row += 1

        footer = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.PRIMARY_SOFT,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
        )
        footer.grid(
            row=1,
            column=0,
            padx=16,
            pady=(6, 16),
            sticky="ew",
        )

        ctk.CTkLabel(
            footer,
            text="v0.2.0",
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=16,
            pady=(12, 2),
        )

        ctk.CTkLabel(
            footer,
            text="© 2026 MRS Consultores",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=11,
            ),
        ).pack(
            anchor="w",
            padx=16,
            pady=(0, 12),
        )

    def _create_button(self, item):
        active = item.key == self.active_key

        image = IconFactory.create(
            item.icon,
            size=20,
            color=(
                Theme.colors.SIDEBAR_TEXT_ACTIVE
                if active
                else Theme.colors.SIDEBAR_TEXT
            ),
        )
        self.images[item.key] = image

        return ctk.CTkButton(
            self.body,
            text=item.text,
            image=image,
            compound="left",
            height=Theme.dimensions.SIDEBAR_ITEM_HEIGHT,
            anchor="w",
            fg_color=(
                Theme.colors.SIDEBAR_SELECTED
                if active
                else Theme.colors.TRANSPARENT
            ),
            hover_color=Theme.colors.SIDEBAR_HOVER,
            text_color=(
                Theme.colors.SIDEBAR_TEXT_ACTIVE
                if active
                else Theme.colors.SIDEBAR_TEXT
            ),
            corner_radius=Theme.dimensions.RADIUS,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
                weight="bold" if active else "normal",
            ),
            command=lambda: self._activate(item),
        )

    def _activate(self, item):
        self.set_active(item.key)

        if callable(item.command):
            item.command()

    def set_active(self, key):
        self.active_key = key

        for item in self.items:
            button = self.buttons[item.key]
            active = item.key == key

            image = IconFactory.create(
                item.icon,
                size=20,
                color=(
                    Theme.colors.SIDEBAR_TEXT_ACTIVE
                    if active
                    else Theme.colors.SIDEBAR_TEXT
                ),
            )
            self.images[item.key] = image

            button.configure(
                image=image,
                fg_color=(
                    Theme.colors.SIDEBAR_SELECTED
                    if active
                    else Theme.colors.TRANSPARENT
                ),
                text_color=(
                    Theme.colors.SIDEBAR_TEXT_ACTIVE
                    if active
                    else Theme.colors.SIDEBAR_TEXT
                ),
                font=ctk.CTkFont(
                    family=Theme.fonts.FAMILY,
                    size=13,
                    weight="bold" if active else "normal",
                ),
            )
