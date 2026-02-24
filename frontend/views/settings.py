import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class SettingsMixin:
    def setup_set(self):
        se = self.pages['set']
        ctk.CTkLabel(se, text='KÂR AYARLARI', font=ctk.CTkFont(size=18, weight='bold')).pack(pady=20)
        g = ctk.CTkFrame(se, fg_color='transparent')
        g.pack(pady=10)
        self.m_ins = {}
        for i, s in enumerate(['GA', 'C22', 'CEYREK', 'YARIM', 'TAM', 'ATA', 'USD', 'EUR']):
            r = i % 4
            c_offset = i // 4 * 3
            ctk.CTkLabel(g, text=s).grid(row=r, column=c_offset, padx=15, pady=8)
            bi = ctk.CTkEntry(g, width=80)
            bi.grid(row=r, column=c_offset + 1, padx=5)
            bi.insert(0, '0')
            si = ctk.CTkEntry(g, width=80)
            si.grid(row=r, column=c_offset + 2, padx=5)
            si.insert(0, '0')
            self.m_ins[s] = (bi, si)
        ctk.CTkButton(se, text='KAYDET', command=self.save_margins).pack(pady=(30, 10))
        self.sync_btn = ctk.CTkButton(se, text='BULUT SENKRONİZASYON', fg_color='#3498db', command=self.trigger_sync)
        self.sync_btn.pack(pady=10)
        
        # Aktivasyon alanı
        ctk.CTkLabel(se, text='--- SİSTEM AKTİVASYONU ---', font=ctk.CTkFont(size=14, weight='bold')).pack(pady=(40, 5))
        self.lic_entry = ctk.CTkEntry(se, placeholder_text='PRO-XXXX-XXXX', width=250, justify='center')
        self.lic_entry.pack(pady=5)
        ctk.CTkButton(se, text='LİSANSI AKTİVET ET', fg_color='#2ecc71', command=self.activate_lic).pack(pady=10)

    def activate_lic(self):
        key = self.lic_entry.get().strip()
        if not key: return
        try:
            r = requests.post(f'{API_URL}/system/activate', json={'license_key': key})
            if r.status_code == 200:
                messagebox.showinfo('Başarılı', 'Sistem başarıyla aktive edildi! Lütfen programı yeniden başlatın.')
            else:
                messagebox.showerror('Hata', 'Geçersiz lisans anahtarı.')
        except Exception as e:
            messagebox.showerror('Hata', f'Sunucu bağlantı hatası: {e}')

    def trigger_sync(self):
        try:
            r = requests.post(f'{API_URL}/system/sync')
            if r.status_code == 200:
                messagebox.showinfo('Bulut', 'Veriler merkeze başarıyla gönderildi.')
            else:
                try:
                    err_msg = r.json().get('detail', 'Senkronizasyon başarısız.')
                except:
                    err_msg = f"Sunucu hatası (Kod: {r.status_code})"
                messagebox.showerror('Hata', err_msg)
        except Exception as e:
            messagebox.showerror('Bağlantı Hatası', f'Senkronizasyon başlatılamadı. Masaüstü API (8000) açık mı? \nDetay: {e}')

    def show_set(self):
        self.switch('set')
        self.refresh_margins()

    def save_margins(self):
        for s, (be, se) in self.m_ins.items():
            requests.post(f'{API_URL}/settings/margins', params={'symbol': s, 'buy_margin': be.get(), 'sell_margin': se.get()})
        messagebox.showinfo('Tamam', 'Kaydedildi.')

    def refresh_margins(self):
        try:
            for m in requests.get(f'{API_URL}/settings/margins').json():
                if m['symbol'] in self.m_ins:
                    b, s = self.m_ins[m['symbol']]
                    b.delete(0, 'end')
                    b.insert(0, str(m['buy_margin']))
                    s.delete(0, 'end')
                    s.insert(0, str(m['sell_margin']))
        except:
            pass

