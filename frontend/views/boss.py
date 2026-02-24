import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class BossMixin:
    def setup_boss(self):
        bo = self.pages['boss']
        ctk.CTkLabel(bo, text='🔐 DÜKKANIM (PATRON PANELİ)', font=ctk.CTkFont(size=26, weight='bold'), text_color='#f1c40f').pack(pady=(20, 5))
        ctk.CTkLabel(bo, text='Buradaki tüm finansal veriler canlı kurlar üzerinden anlık hesaplanır ve personelden gizlenir.', font=ctk.CTkFont(size=12, slant='italic'), text_color='#bdc3c7').pack(pady=(0, 20))
        f_cash = ctk.CTkFrame(bo, fg_color='#1e272e', corner_radius=15, border_width=1, border_color='#2ecc71')
        f_cash.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(f_cash, text='💸 NAKİT VE KÂR DURUMU', font=ctk.CTkFont(size=14, weight='bold'), text_color='#2ecc71').pack(pady=(10, 5))
        r_cash = ctk.CTkFrame(f_cash, fg_color='transparent')
        r_cash.pack(fill='x', expand=True, padx=10, pady=10)
        self.v_cash = self.stat_card(r_cash, 'KASA NAKİT (TL)', '#27ae60')
        self.v_fx = self.stat_card(r_cash, 'DÖVİZ ($ / €)', '#2980b9')
        self.v_pft = self.stat_card(r_cash, 'GÜNLÜK NET KÂR (TL)', '#8e44ad')
        f_gold = ctk.CTkFrame(bo, fg_color='#1e272e', corner_radius=15, border_width=1, border_color='#f39c12')
        f_gold.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(f_gold, text='🥇 FİZİKSEL ALTIN ENVANTERİ', font=ctk.CTkFont(size=14, weight='bold'), text_color='#f39c12').pack(pady=(10, 5))
        r_gold = ctk.CTkFrame(f_gold, fg_color='transparent')
        r_gold.pack(fill='x', expand=True, padx=10, pady=10)
        self.v_stk_raw = self.stat_card(r_gold, 'KÜLÇE / HAM BİRİKİM', '#d35400')
        self.v_stk_vit = self.stat_card(r_gold, 'VİTRİNDEKİ HAS DEĞERİ', '#e67e22')
        self.v_vit_lab = self.stat_card(r_gold, 'VİTRİN İŞÇİLİK BEDELİ', '#c0392b')
        f_val = ctk.CTkFrame(bo, fg_color='#1e272e', corner_radius=15, border_width=1, border_color='#3498db')
        f_val.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(f_val, text='🏢 ŞİRKETİN GÜNCEL DEĞERLEMESİ', font=ctk.CTkFont(size=14, weight='bold'), text_color='#3498db').pack(pady=(10, 5))
        r_val = ctk.CTkFrame(f_val, fg_color='transparent')
        r_val.pack(fill='x', expand=True, padx=10, pady=10)
        self.v_tot_ga = self.stat_card(r_val, 'TOPLAM FİZİKSEL HAS', '#f1c40f')
        self.v_cap = self.stat_card(r_val, 'TÜM VARLIKLARIN HAS KARŞILIĞI', '#e74c3c')
        self.v_ttl = self.stat_card(r_val, 'ŞİRKETİN TOPLAM DEĞERİ (TL)', '#c0392b')
        f_log = ctk.CTkFrame(bo, fg_color='#1e272e', corner_radius=15, border_width=1, border_color='#bdc3c7')
        f_log.pack(fill='both', expand=True, padx=30, pady=10)
        ctk.CTkLabel(f_log, text='📜 GÜNLÜK İŞLEM DEFTERİ', font=ctk.CTkFont(size=14, weight='bold'), text_color='#bdc3c7').pack(pady=(10, 5))
        self.tree_boss_tx = self.create_tree(f_log, ('ts', 'side', 'symbol', 'qty', 'unit_price', 'total_price', 'payment_type'), ('İşlem Saati', 'Tür', 'Birim', 'Miktar', 'Birim F.', 'Toplam (TL)', 'Ödeme Tipi'), height=6)

    def show_boss(self):
        if self.boss_unlocked:
            self.switch('boss')
            self.refresh_boss_data()
            return
        win = ctk.CTkToplevel(self)
        win.title('Güvenlik Onayı')
        win.geometry('300x200')
        win.attributes('-topmost', True)
        ctk.CTkLabel(win, text='Yönetici Şifrenizi Doğrulayın:', font=ctk.CTkFont(weight='bold')).pack(pady=20)
        pwd_entry = ctk.CTkEntry(win, placeholder_text='Şifre', show='*')
        pwd_entry.pack(pady=10)
    
        def check_pw():
            pw = pwd_entry.get()
            try:
                r = requests.post(f'{API_URL}/login', json={'username': self.user.get('username'), 'password': pw})
                if r.status_code == 200:
                    self.boss_unlocked = True
                    win.destroy()
                    self.switch('boss')
                    self.refresh_boss_data()
                else:
                    messagebox.showerror('Hata', 'Geçersiz şifre!')
            except Exception as e:
                messagebox.showerror('Hata', f'Bağlantı hatası: {e}')
        ctk.CTkButton(win, text='ONAYLA', fg_color='#e74c3c', command=check_pw).pack(pady=10)

    def refresh_boss_data(self):
        try:
            r = requests.get(f'{API_URL}/reports/kasa').json()
            daily = requests.get(f'{API_URL}/reports/daily').json()
            val = r['valuation']
            bal = r['balances']
            ps = r['product_stock']
            self.v_cash.configure(text=f'{bal.get('TRY', 0):,.2f} TL')
            self.v_fx.configure(text=f'{bal.get('USD', 0):,.2f} $ / {bal.get('EUR', 0):,.2f} €')
            self.v_tot_ga.configure(text=f'{r['total_gold_has']:,.3f} gr HAS')
            self.v_stk_raw.configure(text=f'{bal.get('GA', 0):,.3f} gr')
            self.v_stk_vit.configure(text=f'{ps['total_weight_has']:,.3f} gr HAS')
            self.v_vit_lab.configure(text=f'{ps['total_labor_tl']:,.2f} TL')
            self.v_ttl.configure(text=f'{val['TRY']:,.2f} TL')
            self.v_cap.configure(text=f'{val['GA']:,.3f} gr HAS')
            self.v_pft.configure(text=f'{daily['profit']:,.2f} TL')
            txs = daily.get('transactions', [])
            self.fill_tree(self.tree_boss_tx, txs, ['ts', 'side', 'symbol', 'qty', 'unit_price', 'total_price', 'payment_type'])
        except Exception as e:
            print(f'Boss data refresh error: {e}')

