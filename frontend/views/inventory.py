import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class InventoryMixin:
    def setup_repo(self):
        re = self.pages['repo']
        f_init = ctk.CTkFrame(re, fg_color='#1e272e', corner_radius=12)
        f_init.pack(fill='x', pady=10, padx=10)
        ctk.CTkLabel(f_init, text='DÜKKAN ENVANTER TANIMLAMA', font=ctk.CTkFont(weight='bold')).pack(pady=10)
        r1 = ctk.CTkFrame(f_init, fg_color='transparent')
        r1.pack(pady=5)
        self.init_sym = ctk.CTkOptionMenu(r1, values=['TRY', 'GA', 'C22', 'CEYREK', 'YARIM', 'TAM', 'ATA', 'USD', 'EUR'], width=100)
        self.init_sym.pack(side='left', padx=10)
        self.init_amt = ctk.CTkEntry(r1, placeholder_text='Miktar')
        self.init_amt.pack(side='left', padx=10)
        ctk.CTkButton(r1, text='İŞLE', fg_color='#8e44ad', command=self.set_inventory).pack(side='left', padx=10)
        self.tree_vault = self.create_tree(re, ('sym', 'bal', 'upd'), ('Varlık', 'Bakiye', 'Son Güncelleme'), height=5)
        self.tree_tx = self.create_tree(re, ('side', 'symbol', 'qty', 'unit_price', 'total_price', 'ts'), ('Tür', 'Birim', 'Mkt', 'Fyt', 'Top', 'Tarih'))

    def setup_stock(self):
        st = self.pages['stock']
        f_st = ctk.CTkFrame(st, width=280)
        f_st.pack(side='left', fill='y', padx=10)
        ctk.CTkLabel(f_st, text='VİTRİNE YENİ ÜRÜN').pack(pady=15)
        self.sn = ctk.CTkEntry(f_st, placeholder_text='Ürün Adı')
        self.sn.pack(pady=5, padx=10, fill='x')
        self.sw = ctk.CTkEntry(f_st, placeholder_text='Gramaj')
        self.sw.pack(pady=5, padx=10, fill='x')
        self.sa = ctk.CTkOptionMenu(f_st, values=['0.916 (22K)', '0.585 (14K)', '0.750 (18K)', '0.995 (Has)'])
        self.sa.pack(pady=5, padx=10, fill='x')
        self.sl = ctk.CTkEntry(f_st, placeholder_text='İşçilik Bedeli')
        self.sl.pack(pady=5, padx=10, fill='x')
        ctk.CTkButton(f_st, text='VİTRİNE EKLE', fg_color='#d35400', command=self.save_stock).pack(pady=20, padx=10, fill='x')
        self.tree_st = self.create_tree(st, ('name', 'weight', 'purity', 'labor_cost', 'stock_qty'), ('Ürün', 'Gram', 'Ayar', 'İşçilik', 'Adet'))

    def show_repo(self):
        self.switch('repo')
        self.refresh_vault()
        self.refresh_repo_tx()

    def show_stock(self):
        self.switch('stock')
        self.refresh_stock()

    def set_inventory(self):
        try:
            requests.post(f'{API_URL}/vault/update', params={'symbol': self.init_sym.get(), 'amount': float(self.init_amt.get())})
            messagebox.showinfo('Tamam', 'Güncellendi.')
            self.refresh_vault()
        except:
            pass

    def save_stock(self):
        try:
            pur_val = 0.916
            sel = self.sa.get()
            if '14K' in sel:
                pur_val = 0.585
            elif '18K' in sel:
                pur_val = 0.75
            elif 'Has' in sel:
                pur_val = 0.995
            requests.post(f'{API_URL}/products', json={'name': self.sn.get(), 'weight': float(self.sw.get()), 'purity': pur_val, 'labor_cost': float(self.sl.get()), 'category': 'Vitrin'})
            self.refresh_stock()
            messagebox.showinfo('Tamam', 'Ürün vitrine eklendi.')
        except:
            pass

    def refresh_vault(self):
        try:
            self.fill_tree(self.tree_vault, requests.get(f'{API_URL}/vault').json(), ['symbol', 'balance', 'last_updated'])
        except:
            pass

    def refresh_repo_tx(self):
        try:
            self.fill_tree(self.tree_tx, requests.get(f'{API_URL}/transactions').json(), ['side', 'symbol', 'qty', 'unit_price', 'total_price', 'ts'])
        except:
            pass

    def refresh_stock(self):
        try:
            self.fill_tree(self.tree_st, requests.get(f'{API_URL}/products').json(), ['name', 'weight', 'purity', 'labor_cost', 'stock_qty'])
        except:
            pass

