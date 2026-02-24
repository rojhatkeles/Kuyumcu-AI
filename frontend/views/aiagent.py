import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class AiAgentMixin:
    def check_ai(self):
        try:
            r = requests.get(f'{API_URL}/ai/suggestions', timeout=1.5).json()
            if r:
                s = r[0]
                self.active_ai_sug = s
                self.ai_lbl.configure(text=s['msg'], text_color='#f1c40f')
                self.ai_btn.pack(side='right', padx=10)
            else:
                self.ai_lbl.configure(text='Kuyumcu AI: Dükkan verileri uyumlu.', text_color='white')
                self.ai_btn.pack_forget()
        except:
            pass

    def apply_ai_suggestion(self):
        if not self.active_ai_sug:
            return
        try:
            s = self.active_ai_sug
            requests.post(f'{API_URL}/settings/margins', params={'symbol': s['symbol'], 'buy_margin': 0, 'sell_margin': s['suggested']})
            messagebox.showinfo('AI', 'Öneri uygulandı.')
            self.ai_btn.pack_forget()
            self.auto_fill_terazi('buy')
            self.auto_fill_terazi('sell')
        except:
            pass

