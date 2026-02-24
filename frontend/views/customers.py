import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class CustomersMixin:
    def setup_cust(self):
        cu = self.pages['cust']
        f_cu = ctk.CTkFrame(cu, width=280)
        f_cu.pack(side='left', fill='y', padx=10)
        ctk.CTkLabel(f_cu, text='YENİ MÜŞTERİ / CARİ HESAP', font=ctk.CTkFont(weight='bold')).pack(pady=15)
        self.cn = ctk.CTkEntry(f_cu, placeholder_text='Ad')
        self.cn.pack(pady=5, padx=10, fill='x')
        self.cp = ctk.CTkEntry(f_cu, placeholder_text='Tel')
        self.cp.pack(pady=5, padx=10, fill='x')
        ctk.CTkButton(f_cu, text='YENİ MÜŞTERİ KAYDET', command=self.save_cust).pack(pady=10, padx=10, fill='x')
        ctk.CTkLabel(f_cu, text='-- CARİ İŞLEMLER --').pack(pady=(15, 5))
        self.c_amt = ctk.CTkEntry(f_cu, placeholder_text='Tutar (TL)')
        self.c_amt.pack(pady=5, padx=10, fill='x')
        ctk.CTkButton(f_cu, text='TAHSİLAT (ALACAK)', fg_color='#2ecc71', command=lambda: self.process_payment('tahsilat')).pack(pady=5, padx=10, fill='x')
        ctk.CTkButton(f_cu, text='ÖDEME (BORÇ)', fg_color='#e74c3c', command=lambda: self.process_payment('odeme')).pack(pady=5, padx=10, fill='x')
        self.tree_cu = self.create_tree(cu, ('id', 'full_name', 'phone', 'balance_try', 'balance_gold'), ('ID', 'Müşteri', 'Tel', 'Bakiye (TL)', 'Bakiye (HAS)'), height=15)

    def show_cust(self):
        self.switch('cust')
        self.refresh_cust()

    def save_cust(self):
        try:
            requests.post(f'{API_URL}/customers', json={'full_name': self.cn.get(), 'phone': self.cp.get()})
            self.refresh_cust()
        except:
            pass

    def process_payment(self, p_type):
        sel = self.tree_cu.selection()
        if not sel:
            messagebox.showwarning('Uyarı', 'Lütfen listeden bir müşteri seçin.')
            return
        cid = self.tree_cu.item(sel[0])['values'][0]
        amt = self.c_amt.get()
        if not amt:
            return
        try:
            r = requests.post(f'{API_URL}/customers/{cid}/payment?amount={float(amt)}&p_type={p_type}')
            if r.status_code == 200:
                self.c_amt.delete(0, 'end')
                messagebox.showinfo('Başarılı', 'Cari işlem kaydedildi.')
                self.after(0, self.refresh_cust)
                self.after(0, self.refresh_vault)
                self.after(0, self.refresh_boss_data)
        except Exception as e:
            messagebox.showerror('Hata', f'Bağlantı hatası: {e}')

    def refresh_cust(self):
        try:
            self.fill_tree(self.tree_cu, requests.get(f'{API_URL}/customers').json(), ['id', 'full_name', 'phone', 'balance_try', 'balance_gold'])
        except:
            pass

