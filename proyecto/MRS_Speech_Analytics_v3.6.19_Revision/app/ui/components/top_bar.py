import customtkinter as ctk
from app.config import app_info
class TopBar(ctk.CTkFrame):
    def __init__(self,parent):
        super().__init__(parent,height=44,corner_radius=0,fg_color='#321755')
        self.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text=f'◉  {app_info.APP_NAME}',text_color='white',font=ctk.CTkFont('Segoe UI',16,'bold')).grid(row=0,column=0,padx=15,pady=10,sticky='w')
        ctk.CTkLabel(self,text='●  Sistema listo',text_color='#DFF6E8',font=ctk.CTkFont('Segoe UI',11,'bold')).grid(row=0,column=1,padx=18,pady=10,sticky='e')
