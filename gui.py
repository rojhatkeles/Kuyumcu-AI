import customtkinter as ctk
import requests, threading, time, datetime
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
API_URL = "http://127.0.0.1:8000"

class KuyumcuProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kuyumcu Pro v5.1 - Tam Envanter ve Akıllı Dahili AI")
        self.geometry("1300x950")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.buy_basket = []
        self.sell_basket = []
        self.b_prod_id = None
        self.s_prod_id = None
        self.customers_list = []
        self.cust_map = {}

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="KUYUMCU PRO AI", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=30)
        
        for text, cmd, name in [
            ("⚖️ Dashboard (Terazi)", self.show_dash, "dash"),
            ("🏦 Envanter & Kasa", self.show_repo, "repo"),
            ("📦 Stok Yönetimi", self.show_stock, "stock"),
            ("👥 Müşteri (Cari)", self.show_cust, "cust"),
            ("⚙️ Kâr Ayarları", self.show_set, "set"),
            ("📈 Grafik ve Analizler", self.show_analiz, "analiz"),
            ("🔐 Dükkanım (Boss)", self.show_boss, "boss")
        ]:
            ctk.CTkButton(self.sidebar, text=text, command=cmd, height=45, corner_radius=8, fg_color="transparent", hover_color="#1f538d", text_color="#ecf0f1", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(pady=5, padx=10, fill="x")

        # Main Container
        self.main_container = ctk.CTkFrame(self, corner_radius=15)
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Üst Panel (Canlı Fiyatlar)
        self.price_bar = ctk.CTkFrame(self.main_container, height=80, fg_color="#1e272e", corner_radius=12)
        self.price_bar.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        self.p_widgets = {}
        for s, n in [("GA", "Has Altın"), ("C22", "22 Ayar"), ("USD", "Dolar"), ("EUR", "Euro")]:
            f = ctk.CTkFrame(self.price_bar, fg_color="transparent")
            f.pack(side="left", expand=True)
            ctk.CTkLabel(f, text=n, font=ctk.CTkFont(size=12, weight="bold"), text_color="#d1d8e0").pack()
            l = ctk.CTkLabel(f, text="---", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f1c40f")
            l.pack(); self.p_widgets[s] = l

        # Sayfalar
        self.pages = {n: ctk.CTkFrame(self.main_container, fg_color="transparent") for n in ["dash", "repo", "stock", "cust", "set", "analiz", "boss"]}
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


    # --- UI HELPERS ---
    def stat_card(self, parent, title, color):
        f = ctk.CTkFrame(parent, corner_radius=12, fg_color=color, height=120)
        f.pack(side="left", expand=True, padx=8, fill="both")
        ctk.CTkLabel(f, text=title, text_color="white", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(12,0))
        l = ctk.CTkLabel(f, text="0.00", text_color="white", font=ctk.CTkFont(size=20, weight="bold"))
        l.pack(pady=8); return l

    def create_tree(self, parent, cols, heads, height=10):
        # Modern Treeview Styling for CTk Dark Mode
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#2b2b2b", foreground="#ecf0f1",
                        rowheight=35, fieldbackground="#2b2b2b",
                        bordercolor="#343638", borderwidth=0, font=("Inter", 12))
        style.map('Treeview', background=[('selected', '#2980b9')])
        style.configure("Treeview.Heading",
                        background="#1a252f", foreground="#ecf0f1",
                        relief="flat", font=("Inter", 12, "bold"), padding=(0, 5))
        style.map("Treeview.Heading", background=[('active', '#2c3e50')])

        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=10, pady=5)
        
        scroll_y = ctk.CTkScrollbar(f, orientation="vertical")
        scroll_y.pack(side="right", fill="y")
        
        t = ttk.Treeview(f, columns=cols, show="headings", height=height, yscrollcommand=scroll_y.set)
        scroll_y.configure(command=t.yview)
        
        for c, h in zip(cols, heads): 
            t.heading(c, text=h)
            t.column(c, width=110, anchor="center")
        t.pack(side="left", fill="both", expand=True)
        return t

    def fill_tree(self, tree, data, keys):
        for i in tree.get_children(): tree.delete(i)
        for row in data:
            vals = [row.get(k, "") for k in keys]
            if "ts" in keys:
                idx = keys.index("ts")
                vals[idx] = str(vals[idx])[:16].replace("T", " ")
            tree.insert("", "end", values=vals)

    # --- PAGE SETUPS ---

    def setup_dash(self):
        d = self.pages["dash"]; d.grid_columnconfigure((0,1), weight=1)
        d.grid_rowconfigure(1, weight=1)

        # AI Bildirim Alanı
        self.ai_row = ctk.CTkFrame(d, fg_color="#34495e", height=40, corner_radius=15)
        self.ai_row.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.ai_lbl = ctk.CTkLabel(self.ai_row, text="Kuyumcu AI: Dükkan verileri analiz ediliyor...", font=ctk.CTkFont(slant="italic"))
        self.ai_lbl.pack(side="left", padx=20, pady=10)
        self.ai_btn = ctk.CTkButton(self.ai_row, text="ÖNERİYİ UYGULA", fg_color="#9b59b6", command=self.apply_ai_suggestion)

        # TERAZİ
        mid_row = ctk.CTkFrame(d, fg_color="transparent")
        mid_row.grid(row=1, column=0, columnspan=2, sticky="nsew")
        mid_row.grid_columnconfigure((0,1), weight=1)

        # SOL: ALIŞ
        f_buy = ctk.CTkFrame(mid_row, fg_color="#1a252f", corner_radius=15)
        f_buy.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(f_buy, text="MÜŞTERİDEN GELEN (ALIŞ)", font=ctk.CTkFont(weight="bold"), text_color="#1abc9c").pack(pady=5)
        
        r_buy = ctk.CTkFrame(f_buy, fg_color="transparent")
        r_buy.pack(pady=5, fill="x")
        self.b_sym = ctk.CTkOptionMenu(r_buy, values=["GA", "C22", "USD", "EUR", "ÜRÜN"], width=90, command=lambda v: self.on_sym_change("buy"))
        self.b_sym.pack(side="left", padx=5)
        self.b_qty = ctk.CTkEntry(r_buy, placeholder_text="Mkt", width=60); self.b_qty.pack(side="left", padx=2)
        self.b_prc = ctk.CTkEntry(r_buy, placeholder_text="Fyt", width=80); self.b_prc.pack(side="left", padx=2)
        ctk.CTkButton(r_buy, text="+", width=30, command=self.add_to_buy).pack(side="left", padx=2)
        
        self.b_qf = ctk.CTkFrame(f_buy, fg_color="transparent"); self.b_qf.pack(pady=2, fill="x")
        self.tree_buy = self.create_tree(f_buy, ("Birim", "Mkt", "Fiyat", "Top"), ("Birim", "Mkt", "Fiyat", "Top"), height=8)

        # SAĞ: SATIŞ
        f_sell = ctk.CTkFrame(mid_row, fg_color="#2c3e50", corner_radius=15)
        f_sell.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(f_sell, text="MÜŞTERİYE VERİLEN (SATIŞ)", font=ctk.CTkFont(weight="bold"), text_color="#3498db").pack(pady=5)
        
        r_sell = ctk.CTkFrame(f_sell, fg_color="transparent")
        r_sell.pack(pady=5, fill="x")
        self.s_sym = ctk.CTkOptionMenu(r_sell, values=["GA", "C22", "USD", "EUR", "ÜRÜN"], width=90, command=lambda v: self.on_sym_change("sell"))
        self.s_sym.pack(side="left", padx=5)
        self.s_qty = ctk.CTkEntry(r_sell, placeholder_text="Mkt", width=60); self.s_qty.pack(side="left", padx=2)
        self.s_prc = ctk.CTkEntry(r_sell, placeholder_text="Fyt", width=80); self.s_prc.pack(side="left", padx=2)
        ctk.CTkButton(r_sell, text="+", width=30, command=self.add_to_sell).pack(side="left", padx=2)

        self.s_qf = ctk.CTkFrame(f_sell, fg_color="transparent"); self.s_qf.pack(pady=2, fill="x")
        self.tree_sell = self.create_tree(f_sell, ("Birim", "Mkt", "Fiyat", "Top"), ("Birim", "Mkt", "Fiyat", "Top"), height=8)

        # NET PANEL VE CARİ SEÇİMİ
        f_bot = ctk.CTkFrame(d, corner_radius=15, fg_color="#1e272e")
        f_bot.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.lbl_net = ctk.CTkLabel(f_bot, text="HESAP: 0.00 TL", font=ctk.CTkFont(size=24, weight="bold"), text_color="#f1c40f")
        self.lbl_net.pack(pady=10)
        
        # Müşteri ve Ödeme Tipi
        c_row = ctk.CTkFrame(f_bot, fg_color="transparent")
        c_row.pack(pady=5)
        ctk.CTkLabel(c_row, text="Müşteri:").pack(side="left", padx=5)
        self.dash_cust = ctk.CTkOptionMenu(c_row, values=["Müşteri Yok (Perakende)"], width=200)
        self.dash_cust.pack(side="left", padx=5)
        ctk.CTkLabel(c_row, text="Ödeme/Bakiye Durumu:").pack(side="left", padx=(15, 5))
        self.dash_pay = ctk.CTkOptionMenu(c_row, values=["Peşin / Kredi Kartı (Kasa)", "Açık Hesap / Veresiye (Cari)"], width=200)
        self.dash_pay.pack(side="left", padx=5)

        btn_box = ctk.CTkFrame(f_bot, fg_color="transparent")
        btn_box.pack(pady=10)
        ctk.CTkButton(btn_box, text="TEMİZLE", fg_color="#e74c3c", width=100, command=self.clear_terazi).pack(side="left", padx=10)
        ctk.CTkButton(btn_box, text="İŞLEMİ BİTİR", fg_color="#2ecc71", width=200, height=40, command=self.finish_transaction).pack(side="left", padx=10)
        self.update_quick_buttons("buy"); self.update_quick_buttons("sell")

    def show_analiz(self):
        self.switch("analiz")
        self.refresh_analiz_data()

    def refresh_analiz_data(self):
        try:
            r = requests.get(f"{API_URL}/reports/analytics").json()
            vol = r.get("volume", {})
            cats = r.get("category_sales", {})
            
            # Canvas Temizliği
            for widget in self.chart_frame.winfo_children():
                widget.destroy()

            fig = Figure(figsize=(10, 4), dpi=100)
            fig.patch.set_facecolor('#2b2b2b')
            
            # Hacim Bar Chart
            ax1 = fig.add_subplot(121)
            ax1.set_facecolor('#2b2b2b')
            ax1.tick_params(colors='white')
            bar_labels = ['Alış', 'Satış']
            bar_values = [vol.get("buy", 0), vol.get("sell", 0)]
            ax1.bar(bar_labels, bar_values, color=['#e74c3c', '#2ecc71'])
            ax1.set_title('Son 30 Günlük İşlem Hacmi (TL)', color='white')
            
            # Kategori Pie Chart
            ax2 = fig.add_subplot(122)
            ax2.set_facecolor('#2b2b2b')
            labels = cats.get("labels", [])
            sizes = cats.get("values", [])
            if sizes:
                ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'color':"w"})
                ax2.set_title('Kategori Bazlı Satış', color='white')
            else:
                ax2.text(0.5, 0.5, 'Yeterli Satış Verisi Yok', color='white', ha='center', va='center')

            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            self.lbl_a_buy.configure(text=f"Alış: {vol.get('buy', 0):,.2f} ₺")
            self.lbl_a_sell.configure(text=f"Satış: {vol.get('sell', 0):,.2f} ₺")
            
        except Exception as e:
            print(f"Analiz veri hatası: {e}")

    def setup_analiz(self):
        pg = self.pages["analiz"]
        
        lbl_head = ctk.CTkLabel(pg, text="Grafik ve Analizler", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_head.pack(pady=20)
        
        summary_fr = ctk.CTkFrame(pg, fg_color="transparent")
        summary_fr.pack(pady=10)
        self.lbl_a_buy = ctk.CTkLabel(summary_fr, text="Alış: -- ₺", font=ctk.CTkFont(size=18, weight="bold"), text_color="#e74c3c")
        self.lbl_a_buy.pack(side="left", padx=20)
        self.lbl_a_sell = ctk.CTkLabel(summary_fr, text="Satış: -- ₺", font=ctk.CTkFont(size=18, weight="bold"), text_color="#2ecc71")
        self.lbl_a_sell.pack(side="left", padx=20)
        
        ctk.CTkButton(summary_fr, text="Yenile", command=self.refresh_analiz_data).pack(side="left", padx=20)

        self.chart_frame = ctk.CTkFrame(pg)
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
    def setup_repo(self):
        re = self.pages["repo"]
        f_init = ctk.CTkFrame(re, fg_color="#1e272e", corner_radius=12)
        f_init.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(f_init, text="DÜKKAN ENVANTER TANIMLAMA", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        r1 = ctk.CTkFrame(f_init, fg_color="transparent"); r1.pack(pady=5)
        self.init_sym = ctk.CTkOptionMenu(r1, values=["TRY", "GA", "USD", "EUR"], width=100)
        self.init_sym.pack(side="left", padx=10)
        self.init_amt = ctk.CTkEntry(r1, placeholder_text="Miktar")
        self.init_amt.pack(side="left", padx=10)
        ctk.CTkButton(r1, text="İŞLE", fg_color="#8e44ad", command=self.set_inventory).pack(side="left", padx=10)
        self.tree_vault = self.create_tree(re, ("sym", "bal", "upd"), ("Varlık", "Bakiye", "Son Güncelleme"), height=5)
        self.tree_tx = self.create_tree(re, ("side", "symbol", "qty", "unit_price", "total_price", "ts"), ("Tür", "Birim", "Mkt", "Fyt", "Top", "Tarih"))

    def setup_stock(self):
        st = self.pages["stock"]; f_st = ctk.CTkFrame(st, width=280); f_st.pack(side="left", fill="y", padx=10)
        ctk.CTkLabel(f_st, text="VİTRİNE YENİ ÜRÜN").pack(pady=15)
        self.sn = ctk.CTkEntry(f_st, placeholder_text="Ürün Adı"); self.sn.pack(pady=5, padx=10, fill="x")
        self.sw = ctk.CTkEntry(f_st, placeholder_text="Gramaj"); self.sw.pack(pady=5, padx=10, fill="x")
        self.sa = ctk.CTkOptionMenu(f_st, values=["0.916 (22K)", "0.585 (14K)", "0.750 (18K)", "0.995 (Has)"]); self.sa.pack(pady=5, padx=10, fill="x")
        self.sl = ctk.CTkEntry(f_st, placeholder_text="İşçilik Bedeli"); self.sl.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(f_st, text="VİTRİNE EKLE", fg_color="#d35400", command=self.save_stock).pack(pady=20, padx=10, fill="x")
        self.tree_st = self.create_tree(st, ("name", "weight", "purity", "labor_cost", "stock_qty"), ("Ürün", "Gram", "Ayar", "İşçilik", "Adet"))


    def setup_cust(self):
        cu = self.pages["cust"]; f_cu = ctk.CTkFrame(cu, width=280); f_cu.pack(side="left", fill="y", padx=10)
        ctk.CTkLabel(f_cu, text="YENİ MÜŞTERİ / CARİ HESAP", font=ctk.CTkFont(weight="bold")).pack(pady=15)
        self.cn = ctk.CTkEntry(f_cu, placeholder_text="Ad"); self.cn.pack(pady=5, padx=10, fill="x")
        self.cp = ctk.CTkEntry(f_cu, placeholder_text="Tel"); self.cp.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(f_cu, text="YENİ MÜŞTERİ KAYDET", command=self.save_cust).pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(f_cu, text="-- CARİ İŞLEMLER --").pack(pady=(15, 5))
        self.c_amt = ctk.CTkEntry(f_cu, placeholder_text="Tutar (TL)"); self.c_amt.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(f_cu, text="TAHSİLAT (ALACAK)", fg_color="#2ecc71", command=lambda: self.process_payment("tahsilat")).pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(f_cu, text="ÖDEME (BORÇ)", fg_color="#e74c3c", command=lambda: self.process_payment("odeme")).pack(pady=5, padx=10, fill="x")

        self.tree_cu = self.create_tree(cu, ("id", "full_name", "phone", "balance_try", "balance_gold"), ("ID", "Müşteri", "Tel", "Bakiye (TL)", "Bakiye (HAS)"), height=15)


    def setup_set(self):
        se = self.pages["set"]; ctk.CTkLabel(se, text="KÂR AYARLARI", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        g = ctk.CTkFrame(se, fg_color="transparent"); g.pack(pady=10)
        self.m_ins = {}
        for i, s in enumerate(["GA", "C22", "USD", "EUR"]):
            ctk.CTkLabel(g, text=s).grid(row=i, column=0, padx=15, pady=8)
            bi = ctk.CTkEntry(g, width=100); bi.grid(row=i, column=1, padx=5); bi.insert(0,"0")
            si = ctk.CTkEntry(g, width=100); si.grid(row=i, column=2, padx=5); si.insert(0,"0")
            self.m_ins[s] = (bi, si)
        ctk.CTkButton(se, text="KAYDET", command=self.save_margins).pack(pady=30)

    def setup_boss(self):
        bo = self.pages["boss"]
        ctk.CTkLabel(bo, text="🔐 DÜKKANIM (PATRON PANELİ)", font=ctk.CTkFont(size=26, weight="bold"), text_color="#f1c40f").pack(pady=(20, 5))
        ctk.CTkLabel(bo, text="Buradaki tüm finansal veriler canlı kurlar üzerinden anlık hesaplanır ve personelden gizlenir.", font=ctk.CTkFont(size=12, slant="italic"), text_color="#bdc3c7").pack(pady=(0, 20))
        
        # 1. NAKİT & KÂR (CASH & PROFIT)
        f_cash = ctk.CTkFrame(bo, fg_color="#1e272e", corner_radius=15, border_width=1, border_color="#2ecc71")
        f_cash.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f_cash, text="💸 NAKİT VE KÂR DURUMU", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2ecc71").pack(pady=(10, 5))
        
        r_cash = ctk.CTkFrame(f_cash, fg_color="transparent")
        r_cash.pack(fill="x", expand=True, padx=10, pady=10)
        self.v_cash = self.stat_card(r_cash, "KASA NAKİT (TL)", "#27ae60")
        self.v_fx = self.stat_card(r_cash, "DÖVİZ ($ / €)", "#2980b9")
        self.v_pft = self.stat_card(r_cash, "DÖNEM NET KÂRI (TL)", "#8e44ad")

        # 2. FİZİKSEL ALTIN VARLIKLARI (GOLD INVENTORY)
        f_gold = ctk.CTkFrame(bo, fg_color="#1e272e", corner_radius=15, border_width=1, border_color="#f39c12")
        f_gold.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f_gold, text="🥇 FİZİKSEL ALTIN ENVANTERİ", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f39c12").pack(pady=(10, 5))
        
        r_gold = ctk.CTkFrame(f_gold, fg_color="transparent")
        r_gold.pack(fill="x", expand=True, padx=10, pady=10)
        self.v_stk_raw = self.stat_card(r_gold, "KÜLÇE / HAM BİRİKİM", "#d35400")
        self.v_stk_vit = self.stat_card(r_gold, "VİTRİNDEKİ HAS DEĞERİ", "#e67e22")
        self.v_vit_lab = self.stat_card(r_gold, "VİTRİN İŞÇİLİK BEDELİ", "#c0392b")

        # 3. ŞİRKET DEĞERLEMESİ (TOTAL VALUATION)
        f_val = ctk.CTkFrame(bo, fg_color="#1e272e", corner_radius=15, border_width=1, border_color="#3498db")
        f_val.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f_val, text="🏢 ŞİRKETİN GÜNCEL DEĞERLEMESİ", font=ctk.CTkFont(size=14, weight="bold"), text_color="#3498db").pack(pady=(10, 5))

        r_val = ctk.CTkFrame(f_val, fg_color="transparent")
        r_val.pack(fill="x", expand=True, padx=10, pady=10)
        self.v_tot_ga = self.stat_card(r_val, "TOPLAM FİZİKSEL HAS", "#f1c40f")
        self.v_cap = self.stat_card(r_val, "TÜM VARLIKLARIN HAS KARŞILIĞI", "#e74c3c")
        self.v_ttl = self.stat_card(r_val, "ŞİRKETİN TOPLAM DEĞERİ (TL)", "#c0392b")


    def show_boss(self):
        dialog = ctk.CTkInputDialog(text="PIN Kodunu Giriniz:", title="Güvenlik")
        pw = dialog.get_input()
        if pw == "1234":
            self.switch("boss"); self.refresh_boss_data()
        else:
            if pw is not None: messagebox.showerror("Hata", "Geçersiz şifre!")

    def refresh_boss_data(self):
        try:
            r = requests.get(f"{API_URL}/reports/kasa").json()
            p = requests.get(f"{API_URL}/reports/pnl").json()
            val = r["valuation"]; bal = r["balances"]; ps = r["product_stock"]
            
            self.v_cash.configure(text=f"{bal.get('TRY', 0):,.2f} TL")
            self.v_fx.configure(text=f"{bal.get('USD', 0):,.2f} $ / {bal.get('EUR', 0):,.2f} €")
            self.v_tot_ga.configure(text=f"{r['total_gold_has']:,.3f} gr HAS")
            
            self.v_stk_raw.configure(text=f"{bal.get('GA', 0):,.3f} gr")
            self.v_stk_vit.configure(text=f"{ps['total_weight_has']:,.3f} gr HAS")
            self.v_vit_lab.configure(text=f"{ps['total_labor_tl']:,.2f} TL")
            
            self.v_ttl.configure(text=f"{val['TRY']:,.2f} TL")
            self.v_cap.configure(text=f"{val['GA']:,.3f} gr HAS")
            self.v_pft.configure(text=f"{p['profit']:,.2f} TL")
        except Exception as e:
            print(f"Boss data refresh error: {e}")


    # --- LOGIC ---

    def refresh_cust_list_dash(self):
        try:
            r = requests.get(f"{API_URL}/customers").json()
            self.customers_list = ["Müşteri Yok (Perakende)"]
            self.cust_map = {}
            for c in r:
                name = f"{c['full_name']} - {c['phone']}"
                self.customers_list.append(name)
                self.cust_map[name] = c['id']
            self.dash_cust.configure(values=self.customers_list)
        except: pass

    def switch(self, name):
        for p in self.pages.values(): p.grid_forget()
        self.pages[name].grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

    def show_dash(self): self.switch("dash"); self.auto_fill_terazi("buy"); self.auto_fill_terazi("sell"); self.check_ai(); self.refresh_cust_list_dash()
    def show_repo(self): self.switch("repo"); self.refresh_vault(); self.refresh_repo_tx()
    def show_stock(self): self.switch("stock"); self.refresh_stock()
    def show_cust(self): self.switch("cust"); self.refresh_cust()
    def show_set(self): self.switch("set"); self.refresh_margins()

    def set_inventory(self):
        try:
            requests.post(f"{API_URL}/vault/update", params={"symbol":self.init_sym.get(), "amount":float(self.init_amt.get())})
            messagebox.showinfo("Tamam", "Güncellendi."); self.refresh_vault()
        except: pass

    def on_sym_change(self, side):
        sym = self.b_sym.get() if side == "buy" else self.s_sym.get()
        if sym == "ÜRÜN":
            self.show_product_selector(side)
        else:
            self.auto_fill_terazi(side)
            self.update_quick_buttons(side)

    def show_product_selector(self, side):
        """Stoktaki ürünleri seçmek için pencere açar"""
        win = ctk.CTkToplevel(self)
        win.title("Vitrinden Ürün Seç")
        win.geometry("500x400")
        win.attributes("-topmost", True)
        
        tree = self.create_tree(win, ("id", "name", "weight", "purity", "labor"), ("ID", "Ürün", "Gram", "Ayar", "İşçilik"), height=10)
        prods = requests.get(f"{API_URL}/products").json()
        self.fill_tree(tree, prods, ["id", "name", "weight", "purity", "labor_cost"])
        
        def select():
            sel = tree.selection()
            if not sel: return
            item = tree.item(sel[0])["values"]
            if side == "buy": self.b_prod_id = int(item[0])
            else: self.s_prod_id = int(item[0])
            
            qty_ent = self.b_qty if side == "buy" else self.s_qty
            prc_ent = self.b_prc if side == "buy" else self.s_prc
            
            qty_ent.delete(0, 'end'); qty_ent.insert(0, "1")
            # Fiyat: (Gram * Live Has * Ayar) + İşçilik
            live = requests.get(f"{API_URL}/prices/smart").json()
            base_p = live["GA"]["suggested_buy" if side == "buy" else "suggested_sell"]
            total_p = (float(item[2]) * base_p * float(item[3])) + float(item[4])
            prc_ent.delete(0, 'end'); prc_ent.insert(0, str(round(total_p, 2)))

            win.destroy()

        ctk.CTkButton(win, text="SEÇ VE DOLDUR", command=select).pack(pady=10)

    def update_quick_buttons(self, side):
        f = self.b_qf if side == "buy" else self.s_qf; sym = (self.b_sym.get() if side == "buy" else self.s_sym.get()); ent = (self.b_qty if side == "buy" else self.s_qty)
        for w in f.winfo_children(): w.destroy()
        if sym == "ÜRÜN": return
        vals = [10, 50, 100, 200, 500] if sym in ["USD", "EUR"] else [1, 5, 0.25, 0.50, 10]
        for v in vals: ctk.CTkButton(f, text=str(v), width=35, height=22, fg_color="#34495e", command=lambda x=v, e=ent: (e.delete(0,'end'), e.insert(0,str(x)))).pack(side="left", padx=2)

    def auto_fill_terazi(self, side):
        try:
            sym = self.b_sym.get() if side == "buy" else self.s_sym.get()
            if sym == "ÜRÜN": return
            r = requests.get(f"{API_URL}/prices/smart", timeout=1.5).json()
            p = r[sym]["suggested_buy"] if side == "buy" else r[sym]["suggested_sell"]
            (self.b_prc if side=="buy" else self.s_prc).delete(0,'end'); (self.b_prc if side=="buy" else self.s_prc).insert(0,str(p))
        except: pass

    def add_to_buy(self):
        try:
            sym = self.b_sym.get()
            qty = float(self.b_qty.get())
            entered_prc = float(self.b_prc.get())
            
            if sym == "ÜRÜN":
                u_prc = entered_prc / qty if qty > 0 else 0
                t_prc = entered_prc
            else:
                u_prc = entered_prc
                t_prc = qty * entered_prc
                
            item = {"side":"buy", "symbol":sym, "qty":qty, "unit_price":u_prc, "total_price":t_prc}
            if sym == "ÜRÜN": item["product_id"] = self.b_prod_id
            self.buy_basket.append(item); self.b_prod_id = None; self.update_terazi_display()
        except: pass

    def add_to_sell(self):
        try:
            sym = self.s_sym.get()
            qty = float(self.s_qty.get())
            entered_prc = float(self.s_prc.get())
            
            if sym == "ÜRÜN":
                u_prc = entered_prc / qty if qty > 0 else 0
                t_prc = entered_prc
            else:
                u_prc = entered_prc
                t_prc = qty * entered_prc
                
            item = {"side":"sell", "symbol":sym, "qty":qty, "unit_price":u_prc, "total_price":t_prc}
            if sym == "ÜRÜN": item["product_id"] = self.s_prod_id
            self.sell_basket.append(item); self.s_prod_id = None; self.update_terazi_display()
        except: pass

    def update_terazi_display(self):
        for t, b in [(self.tree_buy, self.buy_basket), (self.tree_sell, self.sell_basket)]:
            for i in t.get_children(): t.delete(i)
            for x in b: t.insert("", "end", values=(x["symbol"], x["qty"], x["unit_price"], round(x["total_price"], 2)))
        net = sum(x["total_price"] for x in self.sell_basket) - sum(x["total_price"] for x in self.buy_basket)
        if net > 0: self.lbl_net.configure(text=f"MÜŞTERİ ÖDEMELİ: {net:,.2f} TL", text_color="#f1c40f")
        elif net < 0: self.lbl_net.configure(text=f"MÜŞTERİYE İADE: {abs(net):,.2f} TL", text_color="#1abc9c")
        else: self.lbl_net.configure(text="HESAP BAŞABAŞ (0.00 TL)", text_color="white")

    def finish_transaction(self):
        if not self.buy_basket and not self.sell_basket: return
        
        try:
            cust_name = self.dash_cust.get()
            pay_type = "Debt" if "Veresiye" in self.dash_pay.get() else "Cash"
            cid = self.cust_map.get(cust_name)
            
            for i in self.buy_basket + self.sell_basket:
                if cid: i["customer_id"] = cid
                i["payment_type"] = pay_type
                requests.post(f"{API_URL}/transactions", json=i)
                
            messagebox.showinfo("Tamam", "İşlem bitti."); self.clear_terazi()
            self.after(0, self.refresh_boss_data)
            self.after(0, self.refresh_vault)
            self.after(0, self.refresh_stock)
            self.after(0, self.refresh_repo_tx)
            self.after(0, self.refresh_cust) # Müşteri bakiyesi değişmiş olabilir
        except Exception as e:
            messagebox.showerror("Hata", f"İşlem tamamlanamadı: {e}")


    def clear_terazi(self): 
        self.buy_basket = []; self.sell_basket = []; self.update_terazi_display()
        self.dash_cust.set("Müşteri Yok (Perakende)")
        self.dash_pay.set("Peşin / Kredi Kartı (Kasa)")

    def refresh_valuation(self):
        try:
            r = requests.get(f"{API_URL}/reports/kasa").json()
            val = r["valuation"]; bal = r["balances"]; ps = r["product_stock"]
            
            # Ana değerleri güncelle (thread-safe after çağrısı start_loops'da yapılıyor)
            self.v_cash.configure(text=f"{bal.get('TRY', 0):,.2f} TL")
            self.v_fx.configure(text=f"{bal.get('USD', 0):,.2f} $ / {bal.get('EUR', 0):,.2f} €")
            self.v_stk_raw.configure(text=f"{bal.get('GA', 0):,.3f} gr")
            self.v_stk_vit.configure(text=f"{ps['total_weight_has']:,.3f} gr HAS")
            self.v_ttl.configure(text=f"{val['TRY']:,.2f} TL")
            self.v_cap.configure(text=f"{val['GA']:,.3f} gr HAS")
            self.v_tot_ga.configure(text=f"{r['total_gold_has']:,.3f} gr HAS")
        except: pass



    def refresh_vault(self):
        try: self.fill_tree(self.tree_vault, requests.get(f"{API_URL}/vault").json(), ["symbol", "balance", "last_updated"])
        except: pass

    def refresh_repo_tx(self):
        try: self.fill_tree(self.tree_tx, requests.get(f"{API_URL}/transactions").json(), ["side", "symbol", "qty", "unit_price", "total_price", "ts"])
        except: pass

    def refresh_stock(self):
        try: self.fill_tree(self.tree_st, requests.get(f"{API_URL}/products").json(), ["name", "weight", "purity", "labor_cost", "stock_qty"])
        except: pass


    def refresh_cust(self):
        try: self.fill_tree(self.tree_cu, requests.get(f"{API_URL}/customers").json(), ["id", "full_name", "phone", "balance_try", "balance_gold"])
        except: pass

    def process_payment(self, p_type):
        sel = self.tree_cu.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen listeden bir müşteri seçin.")
            return
        
        cid = self.tree_cu.item(sel[0])["values"][0]
        amt = self.c_amt.get()
        if not amt: return
        
        try:
            r = requests.post(f"{API_URL}/customers/{cid}/payment?amount={float(amt)}&p_type={p_type}")
            if r.status_code == 200:
                self.c_amt.delete(0, 'end')
                messagebox.showinfo("Başarılı", "Cari işlem kaydedildi.")
                self.after(0, self.refresh_cust)
                self.after(0, self.refresh_vault)
                self.after(0, self.refresh_boss_data)
        except Exception as e:
            messagebox.showerror("Hata", f"Bağlantı hatası: {e}")

    def refresh_margins(self):
        try:
            for m in requests.get(f"{API_URL}/settings/margins").json():
                if m["symbol"] in self.m_ins:
                    b, s = self.m_ins[m["symbol"]]; b.delete(0,'end'); b.insert(0,str(m["buy_margin"])); s.delete(0,'end'); s.insert(0,str(m["sell_margin"]))
        except: pass

    def check_ai(self):
        try:
            r = requests.get(f"{API_URL}/ai/suggestions", timeout=1.5).json()
            if r:
                s = r[0]; self.active_ai_sug = s
                self.ai_lbl.configure(text=s["msg"], text_color="#f1c40f"); self.ai_btn.pack(side="right", padx=10)
            else:
                self.ai_lbl.configure(text="Kuyumcu AI: Dükkan verileri uyumlu.", text_color="white"); self.ai_btn.pack_forget()
        except: pass

    def apply_ai_suggestion(self):
        if not self.active_ai_sug: return
        try:
            s = self.active_ai_sug; requests.post(f"{API_URL}/settings/margins", params={"symbol":s["symbol"], "buy_margin":0, "sell_margin":s["suggested"]})
            messagebox.showinfo("AI", "Öneri uygulandı."); self.ai_btn.pack_forget(); self.auto_fill_terazi("buy"); self.auto_fill_terazi("sell")
        except: pass

    def save_stock(self):
        try:
            pur_val = 0.916
            sel = self.sa.get()
            if "14K" in sel: pur_val = 0.585
            elif "18K" in sel: pur_val = 0.750
            elif "Has" in sel: pur_val = 0.995
            
            requests.post(f"{API_URL}/products", json={
                "name":self.sn.get(), 
                "weight":float(self.sw.get()), 
                "purity":pur_val,
                "labor_cost":float(self.sl.get()), 
                "category":"Vitrin"
            })
            self.refresh_stock(); messagebox.showinfo("Tamam", "Ürün vitrine eklendi.")
        except: pass


    def save_cust(self):
        try: requests.post(f"{API_URL}/customers", json={"full_name":self.cn.get(), "phone":self.cp.get()}); self.refresh_cust()
        except: pass

    def save_margins(self):
        for s, (be, se) in self.m_ins.items(): requests.post(f"{API_URL}/settings/margins", params={"symbol":s, "buy_margin":be.get(), "sell_margin":se.get()})
        messagebox.showinfo("Tamam", "Kaydedildi.")

    def start_loops(self):
        def loop():
            while True:
                try:
                    p = requests.get(f"{API_URL}/prices", timeout=2).json()
                    # UI güncellemelerini ana thread'e taşıyalım
                    self.after(0, lambda: self.update_price_widgets(p))
                    self.after(0, self.refresh_valuation)
                    self.after(0, self.check_ai)
                except Exception as e:
                    print(f"Background loop error: {e}")
                time.sleep(15)
        threading.Thread(target=loop, daemon=True).start()

    def update_price_widgets(self, prices):
        for s, l in self.p_widgets.items():
            if s in prices: l.configure(text=f"{prices[s]['sell']:,.2f} TL")


if __name__ == "__main__":
    app = KuyumcuProApp()
    app.mainloop()
