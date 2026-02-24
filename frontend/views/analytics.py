import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class AnalyticsMixin:
    def setup_analiz(self):
        pg = self.pages['analiz']
        lbl_head = ctk.CTkLabel(pg, text='Grafik ve Analizler', font=ctk.CTkFont(size=24, weight='bold'))
        lbl_head.pack(pady=20)
        summary_fr = ctk.CTkFrame(pg, fg_color='transparent')
        summary_fr.pack(pady=10)
        self.lbl_a_buy = ctk.CTkLabel(summary_fr, text='Alış: -- ₺', font=ctk.CTkFont(size=18, weight='bold'), text_color='#e74c3c')
        self.lbl_a_buy.pack(side='left', padx=20)
        self.lbl_a_sell = ctk.CTkLabel(summary_fr, text='Satış: -- ₺', font=ctk.CTkFont(size=18, weight='bold'), text_color='#2ecc71')
        self.lbl_a_sell.pack(side='left', padx=20)
        ctk.CTkButton(summary_fr, text='Yenile', command=self.refresh_analiz_data).pack(side='left', padx=20)
        self.chart_frame = ctk.CTkFrame(pg)
        self.chart_frame.pack(fill='both', expand=True, padx=20, pady=20)

    def show_analiz(self):
        self.switch('analiz')
        self.refresh_analiz_data()

    def refresh_analiz_data(self):
        try:
            r = requests.get(f'{API_URL}/reports/analytics').json()
            vol = r.get('volume', {})
            cats = r.get('category_sales', {})
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            fig = Figure(figsize=(10, 4), dpi=100)
            fig.patch.set_facecolor('#2b2b2b')
            ax1 = fig.add_subplot(121)
            ax1.set_facecolor('#2b2b2b')
            ax1.tick_params(colors='white')
            bar_labels = ['Alış', 'Satış']
            bar_values = [vol.get('buy', 0), vol.get('sell', 0)]
            ax1.bar(bar_labels, bar_values, color=['#e74c3c', '#2ecc71'])
            ax1.set_title('Son 30 Günlük İşlem Hacmi (TL)', color='white')
            ax2 = fig.add_subplot(122)
            ax2.set_facecolor('#2b2b2b')
            labels = cats.get('labels', [])
            sizes = cats.get('values', [])
            if sizes:
                ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'color': 'w'})
                ax2.set_title('Kategori Bazlı Satış', color='white')
            else:
                ax2.text(0.5, 0.5, 'Yeterli Satış Verisi Yok', color='white', ha='center', va='center')
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            self.lbl_a_buy.configure(text=f'Alış: {vol.get('buy', 0):,.2f} ₺')
            self.lbl_a_sell.configure(text=f'Satış: {vol.get('sell', 0):,.2f} ₺')
        except Exception as e:
            print(f'Analiz veri hatası: {e}')

