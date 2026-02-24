import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
import requests, threading, time
from tkinter import messagebox, ttk

from frontend.core.config import API_URL, apply_theme
from frontend.views.dashboard import DashboardMixin
from frontend.views.boss import BossMixin
from frontend.views.analytics import AnalyticsMixin
from frontend.views.inventory import InventoryMixin
from frontend.views.customers import CustomersMixin
from frontend.views.settings import SettingsMixin
from frontend.views.aiagent import AiAgentMixin

apply_theme()

class LoginWindow(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title('Kuyumcu Pro AI - Giriş')
        self.geometry('400x500')
        self.eval('tk::PlaceWindow . center')
        ctk.CTkLabel(self, text='🛡️ GÜVENLİ GİRİŞ', font=ctk.CTkFont(size=24, weight='bold'), text_color='#f1c40f').pack(pady=(40, 20))
        self.username = ctk.CTkEntry(self, placeholder_text='Kullanıcı Adı', height=45, font=ctk.CTkFont(size=14))
        self.username.pack(pady=10, padx=40, fill='x')
        self.password = ctk.CTkEntry(self, placeholder_text='Şifre', show='*', height=45, font=ctk.CTkFont(size=14))
        self.password.pack(pady=10, padx=40, fill='x')
        ctk.CTkButton(self, text='GİRİŞ YAP', height=45, fg_color='#2ecc71', font=ctk.CTkFont(size=16, weight='bold'), command=self.do_login).pack(pady=30, padx=40, fill='x')
        self.lbl_msg = ctk.CTkLabel(self, text='Sistem başlatılıyor...', text_color='#bdc3c7')
        self.lbl_msg.pack(pady=10)
        self.after(500, self.check_api_and_admin)

    def check_api_and_admin(self):
        try:
            r = requests.get(f'{API_URL}/users/ensure_admin', timeout=2)
            if r.status_code == 200:
                self.lbl_msg.configure(text='Sistem Hazır. (Varsayılan Admin: admin/admin123)', text_color='#2ecc71')
        except Exception as e:
            self.lbl_msg.configure(text='Sunucuya bağlanılamadı!', text_color='#e74c3c')
            self.after(2000, self.check_api_and_admin)

    def do_login(self):
        usr = self.username.get()
        pwd = self.password.get()
        if not usr or not pwd:
            messagebox.showwarning('Uyarı', 'Kullanıcı adı ve şifre giriniz.')
            return
        try:
            r = requests.post(f'{API_URL}/login', json={'username': usr, 'password': pwd})
            if r.status_code == 200:
                user_data = r.json()['user']
                self.destroy()
                app = KuyumcuProApp(user_data)
                app.mainloop()
            else:
                messagebox.showerror('Hata', 'Hatalı kullanıcı adı veya şifre!')
        except Exception as e:
            messagebox.showerror('Hata', f'Bağlantı hatası: {e}')

class KuyumcuProApp(ctk.CTk, DashboardMixin, BossMixin, AnalyticsMixin, InventoryMixin, CustomersMixin, SettingsMixin, AiAgentMixin):
    def __init__(self, user):
        super().__init__()
        self.user = user
        role_label = 'YÖNETİCİ' if self.user.get('role') == 'admin' else 'KASİYER'
        self.title(f'Kuyumcu Pro v6.0 - [{self.user.get('username').upper()} - {role_label}]')
        self.geometry('1300x950')
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.buy_basket = []
        self.sell_basket = []
        self.b_prod_id = None
        self.s_prod_id = None
        self.customers_list = []
        self.cust_map = {}
        self.boss_unlocked = False
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        ctk.CTkLabel(self.sidebar, text='KUYUMCU PRO AI', font=ctk.CTkFont(size=22, weight='bold')).pack(pady=30)
        # Get License Tier
        try:
            self.license_tier = requests.get(f"{API_URL}/system/tier").json().get("tier", "NORMAL")
        except:
            self.license_tier = "NORMAL"

        pages_to_show = [('⚖️ Dashboard (Terazi)', self.show_dash, 'dash'), ('🏦 Envanter & Kasa', self.show_repo, 'repo'), ('📦 Stok Yönetimi', self.show_stock, 'stock'), ('👥 Müşteri (Cari)', self.show_cust, 'cust')]
        
        if self.user.get('role') == 'admin':
            pages_to_show.append(('⚙️ Kâr Ayarları', self.show_set, 'set'))
            if self.license_tier == "PREMIUM":
                pages_to_show.extend([('📈 Grafik ve Analizler', self.show_analiz, 'analiz'), ('🔐 Dükkanım (Boss)', self.show_boss, 'boss')])

        for text, cmd, name in pages_to_show:
            ctk.CTkButton(self.sidebar, text=text, command=cmd, height=45, corner_radius=8, fg_color='transparent', hover_color='#1f538d', text_color='#ecf0f1', font=ctk.CTkFont(size=14, weight='bold'), anchor='w').pack(pady=5, padx=10, fill='x')

        if self.license_tier == "NORMAL":
            ctk.CTkLabel(self.sidebar, text="---", text_color="gray").pack(pady=10)
            ctk.CTkButton(self.sidebar, text="💎 PREMIUM'A GEÇ", command=self.open_upgrade_window, height=40, fg_color="#f39c12", hover_color="#e67e22", text_color="white", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=20, padx=15, fill="x")

        self.main_container = ctk.CTkFrame(self, corner_radius=15)
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky='nsew')
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.price_bar = ctk.CTkFrame(self.main_container, fg_color='#1e272e', corner_radius=12)
        self.price_bar.grid(row=0, column=0, padx=15, pady=15, sticky='ew')
        for i in range(4):
            self.price_bar.grid_columnconfigure(i, weight=1)
        self.p_widgets = {}
        instruments = [('GA', 'Has Altın'), ('C22', '22 Ayar'), ('CEYREK', 'Çeyrek'), ('YARIM', 'Yarım'), ('TAM', 'Tam'), ('ATA', 'Ata'), ('USD', 'Dolar'), ('EUR', 'Euro')]
        for idx, (s, n) in enumerate(instruments):
            r = idx // 4
            c = idx % 4
            f = ctk.CTkFrame(self.price_bar, fg_color='transparent')
            f.grid(row=r, column=c, padx=5, pady=8, sticky='nsew')
            ctk.CTkLabel(f, text=n, font=ctk.CTkFont(size=14, weight='bold'), text_color='#d1d8e0').pack(pady=(0, 2))
            p_fr = ctk.CTkFrame(f, fg_color='transparent')
            p_fr.pack()
            l_buy = ctk.CTkLabel(p_fr, text='Alış: ---', font=ctk.CTkFont(size=13, weight='bold'), text_color='#e74c3c')
            l_buy.pack(side='left', padx=5)
            l_sell = ctk.CTkLabel(p_fr, text='Satış: ---', font=ctk.CTkFont(size=13, weight='bold'), text_color='#2ecc71')
            l_sell.pack(side='left', padx=5)
            self.p_widgets[s] = (l_buy, l_sell)
        self.pages = {n: ctk.CTkFrame(self.main_container, fg_color='transparent') for n in ['dash', 'repo', 'stock', 'cust', 'set', 'analiz']}
        self.pages['boss'] = ctk.CTkScrollableFrame(self.main_container, fg_color='transparent')
        self.active_ai_sug = None
        self.setup_dash()
        self.setup_repo()
        self.setup_stock()
        self.setup_cust()
        self.setup_set()
        self.setup_analiz()
        self.setup_boss()
        self.show_dash()
        self.start_loops()

    def stat_card(self, parent, title, color):
        f = ctk.CTkFrame(parent, corner_radius=12, fg_color=color, height=120)
        f.pack(side='left', expand=True, padx=8, fill='both')
        ctk.CTkLabel(f, text=title, text_color='white', font=ctk.CTkFont(size=11, weight='bold')).pack(pady=(12, 0))
        l = ctk.CTkLabel(f, text='0.00', text_color='white', font=ctk.CTkFont(size=20, weight='bold'))
        l.pack(pady=8)
        return l

    def create_sym_grid(self, parent, side):
        f = ctk.CTkFrame(parent, fg_color='transparent')
        f.pack(pady=5)
        symbols = ['USD', 'EUR', 'GA', 'C22', 'CEYREK', 'YARIM', 'TAM', 'ATA', 'ÜRÜN']
        display_map = {'USD': '$ USD', 'EUR': '€ EUR'}
        btns = []
        var_val = ['USD']
    
        def on_click(s):
            var_val[0] = s
            for b, sym in zip(btns, symbols):
                b.configure(fg_color='#2980b9' if sym == s else '#34495e')
            self.on_sym_change(side)
        for i, s in enumerate(symbols):
            disp = display_map.get(s, s)
            b = ctk.CTkButton(f, text=disp, width=54, height=35, font=ctk.CTkFont(size=11, weight='bold'), fg_color='#2980b9' if s == 'USD' else '#34495e', command=lambda v=s: on_click(v))
            b.grid(row=i // 5, column=i % 5, padx=2, pady=2)
            btns.append(b)
    
        class PosProxy:
    
            def get(self):
                return var_val[0]
    
            def set(self, val):
                var_val[0] = val
                for b, sym in zip(btns, symbols):
                    b.configure(fg_color='#2980b9' if sym == val else '#34495e')
        return PosProxy()

    def create_tree(self, parent, cols, heads, height=10):
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Treeview', background='#2b2b2b', foreground='#ecf0f1', rowheight=35, fieldbackground='#2b2b2b', bordercolor='#343638', borderwidth=0, font=('Inter', 12))
        style.map('Treeview', background=[('selected', '#2980b9')])
        style.configure('Treeview.Heading', background='#1a252f', foreground='#ecf0f1', relief='flat', font=('Inter', 12, 'bold'), padding=(0, 5))
        style.map('Treeview.Heading', background=[('active', '#2c3e50')])
        f = ctk.CTkFrame(parent, fg_color='transparent')
        f.pack(fill='both', expand=True, padx=10, pady=5)
        scroll_y = ctk.CTkScrollbar(f, orientation='vertical')
        scroll_y.pack(side='right', fill='y')
        t = ttk.Treeview(f, columns=cols, show='headings', height=height, yscrollcommand=scroll_y.set)
        scroll_y.configure(command=t.yview)
        for c, h in zip(cols, heads):
            t.heading(c, text=h)
            t.column(c, width=110, anchor='center')
        t.pack(side='left', fill='both', expand=True)
        return t

    def fill_tree(self, tree, data, keys):
        for i in tree.get_children():
            tree.delete(i)
        for row in data:
            vals = [row.get(k, '') for k in keys]
            if 'ts' in keys:
                idx = keys.index('ts')
                vals[idx] = str(vals[idx])[:16].replace('T', ' ')
            tree.insert('', 'end', values=vals)

    def switch(self, name):
        for p in self.pages.values():
            p.grid_forget()
        self.pages[name].grid(row=1, column=0, sticky='nsew', padx=15, pady=15)

    def refresh_valuation(self):
        try:
            r = requests.get(f'{API_URL}/reports/kasa').json()
            val = r['valuation']
            bal = r['balances']
            ps = r['product_stock']
            self.v_cash.configure(text=f'{bal.get('TRY', 0):,.2f} TL')
            self.v_fx.configure(text=f'{bal.get('USD', 0):,.2f} $ / {bal.get('EUR', 0):,.2f} €')
            self.v_stk_raw.configure(text=f'{bal.get('GA', 0):,.3f} gr')
            self.v_stk_vit.configure(text=f'{ps['total_weight_has']:,.3f} gr HAS')
            self.v_ttl.configure(text=f'{val['TRY']:,.2f} TL')
            self.v_cap.configure(text=f'{val['GA']:,.3f} gr HAS')
            self.v_tot_ga.configure(text=f'{r['total_gold_has']:,.3f} gr HAS')
        except:
            pass

    def start_loops(self):
    
        def loop():
            while True:
                try:
                    raw_prices = requests.get(f'{API_URL}/prices', timeout=2).json()
                    self.after(0, lambda: self.update_price_widgets(raw_prices))
                    self.after(0, self.refresh_valuation)
                    self.after(0, self.check_ai)
                except Exception as e:
                    print(f'Background loop error: {e}')
                time.sleep(15)
        threading.Thread(target=loop, daemon=True).start()

    def update_price_widgets(self, prices):
        for s, (lb, ls) in self.p_widgets.items():
            if s in prices:
                lb.configure(text=f"Alış: {prices[s]['buy']:,.2f}")
                ls.configure(text=f"Satış: {prices[s]['sell']:,.2f}")

    def open_upgrade_window(self):
        # license_activator.py is a separate tool, but we can also just show a Toplevel here
        win = ctk.CTkToplevel(self)
        win.title("Kuyumcu Pro AI - Lisans Yükseltme")
        win.geometry("400x350")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text="💎 PREMIUM YÜKSELTME", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f1c40f").pack(pady=(30, 10))
        ctk.CTkLabel(win, text="KuyumcuPro.com'dan aldığınız\nLisans (Aktivasyon) Anahtarını giriniz:", font=ctk.CTkFont(size=14)).pack(pady=10)
        
        l_key = ctk.CTkEntry(win, placeholder_text="PRO-XXXX-XXXX", height=45, font=ctk.CTkFont(size=14), justify="center")
        l_key.pack(pady=15, padx=40, fill="x")
        
        def activate():
            key = l_key.get().strip()
            try:
                r = requests.post(f"{API_URL}/system/activate", json={"license_key": key})
                if r.status_code == 200:
                    messagebox.showinfo("Başarılı!", "🎉 Premium aktif edildi. Değişikliklerin yansıması için programı kapatıp açın.")
                    win.destroy()
                else:
                    messagebox.showerror("Hata", "Geçersiz anahtar!")
            except:
                messagebox.showerror("Hata", "Sunucu hatası!")

        ctk.CTkButton(win, text="LİSANSI DOĞRULA", height=45, fg_color="#2ecc71", command=activate).pack(pady=15, padx=40, fill="x")



if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
