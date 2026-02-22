import customtkinter as ctk
import requests
import threading
import time
from tkinter import messagebox, ttk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
API_URL = "http://127.0.0.1:8000"

class KuyumcuProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kuyumcu Pro v3.5 - Kesin Otomatik Fiyatlandırma")
        self.geometry("1150x850")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="KUYUMCU PRO AI", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=30)
        
        for text, cmd in [("Kontrol Paneli", self.show_dash), ("Kasa & Raporlar", self.show_repo), 
                          ("Stok Yönetimi", self.show_stock), ("Müşteriler", self.show_cust), 
                          ("Kâr Ayarları", self.show_settings)]:
            ctk.CTkButton(self.sidebar, text=text, command=cmd, height=45).pack(pady=10, padx=20)

        # Main Content
        self.main_container = ctk.CTkFrame(self, corner_radius=15)
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Top Bar
        self.price_bar = ctk.CTkFrame(self.main_container, height=80, fg_color="#1e272e", corner_radius=12)
        self.price_bar.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        self.p_widgets = {}
        for s, n in [("GA", "Has Altın"), ("C22", "22 Ayar"), ("USD", "Dolar"), ("EUR", "Euro")]:
            f = ctk.CTkFrame(self.price_bar, fg_color="transparent")
            f.pack(side="left", expand=True)
            ctk.CTkLabel(f, text=n, font=ctk.CTkFont(size=12)).pack()
            l = ctk.CTkLabel(f, text="---", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f1c40f")
            l.pack(); self.p_widgets[s] = l

        self.pages = {n: ctk.CTkFrame(self.main_container, fg_color="transparent") for n in ["dash", "repo", "stock", "cust", "set"]}
        self.setup_all_pages()
        self.show_dash()
        self.start_loops()

    def switch(self, name):
        for p in self.pages.values(): p.grid_forget()
        self.pages[name].grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def setup_all_pages(self):
        # --- DASHBOARD ---
        d = self.pages["dash"]; d.grid_columnconfigure(0, weight=1)
        self.ai_lbl = ctk.CTkLabel(d, text="AI: Piyasa izleniyor...", font=ctk.CTkFont(slant="italic"), text_color="#9b59b6")
        self.ai_lbl.pack(pady=5)
        
        box = ctk.CTkFrame(d, fg_color="#2c3e50", corner_radius=15); box.pack(pady=20, padx=40, fill="x")
        # TETİKLEYİCİ: SegmentedButton değişince fiyat dolsun
        self.t_side = ctk.CTkSegmentedButton(box, values=["ALIŞ", "SATIŞ"], command=lambda v: self.auto_fill())
        self.t_side.set("SATIŞ"); self.t_side.pack(pady=20)
        
        r1 = ctk.CTkFrame(box, fg_color="transparent"); r1.pack(pady=10)
        # TETİKLEYİCİ: OptionMenu değişince fiyat dolsun
        self.t_sym = ctk.CTkOptionMenu(r1, values=["GA", "C22", "USD", "EUR"], command=lambda v: self.auto_fill())
        self.t_sym.pack(side="left", padx=10)
        self.t_qty = ctk.CTkEntry(r1, placeholder_text="Miktar", width=120); self.t_qty.pack(side="left", padx=10)
        self.t_prc = ctk.CTkEntry(r1, placeholder_text="Fiyat", width=140); self.t_prc.pack(side="left", padx=10)
        ctk.CTkButton(box, text="İŞLEMİ KAYDET", fg_color="#3498db", height=45, command=self.save_tx).pack(pady=25)

        # Diğer sekmeler (Reports, Stock, Cust, Settings)
        self.setup_other_tabs()

    def auto_fill(self):
        """Dashboard fiyat kutusunu akıllı fiyata göre anında günceller"""
        try:
            # API'den en güncel marjlı fiyatları al
            r = requests.get(f"{API_URL}/prices/smart", timeout=1.5).json()
            sym = self.t_sym.get()
            side = "suggested_sell" if self.t_side.get() == "SATIŞ" else "suggested_buy"
            price = r[sym][side]
            
            # Kutuyu temizle ve yeni fiyatı yaz
            self.t_prc.delete(0, 'end')
            self.t_prc.insert(0, str(price))
            self.ai_lbl.configure(text=f"Kuyumcu AI: {sym} için {price} TL piyasa fiyatı uygulandı.")
        except Exception as e:
            print(f"Auto-fill Error: {e}")

    def show_dash(self): 
        self.switch("dash")
        # Sayfa her açıldığında fiyatı otomatik getir
        self.after(100, self.auto_fill)

    # --- ALTYAPI FONKSİYONLARI ---
    def setup_other_tabs(self):
        # Reports
        re = self.pages["repo"]
        cards = ctk.CTkFrame(re, fg_color="transparent"); cards.pack(fill="x", pady=10)
        self.lbl_cash = self.stat_card(cards, "NAKİT TL", "#1abc9c")
        self.lbl_gold = self.stat_card(cards, "HAS STOK gr", "#f39c12")
        self.lbl_profit = self.stat_card(cards, "GÜNLÜK KAR", "#3498db")
        self.tree_tx = self.create_tree(re, ("Tür", "Birim", "Mkt", "Fiyat", "Top", "Tarih"))
        # Settings
        se = self.pages["set"]
        ctk.CTkLabel(se, text="Kâr Marjı Ayarları").pack(pady=20)
        self.m_ins = {}
        for i, s in enumerate(["GA", "C22", "USD", "EUR"]):
            r = ctk.CTkFrame(se, fg_color="transparent"); r.pack(pady=5)
            ctk.CTkLabel(r, text=s, width=50).pack(side="left")
            bi = ctk.CTkEntry(r, width=100); bi.pack(side="left", padx=5); bi.insert(0,"0")
            si = ctk.CTkEntry(r, width=100); si.pack(side="left", padx=5); si.insert(0,"0")
            self.m_ins[s] = (bi, si)
        ctk.CTkButton(se, text="KAYDET", command=self.save_margins).pack(pady=20)
        # Stok & Cust (Basitleştirilmiş)
        self.tree_st = self.create_tree(self.pages["stock"], ("Ürün", "Ağırlık", "İşçilik"))
        self.tree_cu = self.create_tree(self.pages["cust"], ("İsim", "Tel", "TL Bak."))

    def stat_card(self, p, t, c):
        f = ctk.CTkFrame(p, corner_radius=12, fg_color=c, height=100); f.pack(side="left", expand=True, padx=10, fill="both")
        l = ctk.CTkLabel(f, text="0.00", text_color="white", font=ctk.CTkFont(size=22, weight="bold")); l.pack(pady=20); return l

    def create_tree(self, p, heads):
        f = ctk.CTkFrame(p); f.pack(fill="both", expand=True, padx=10, pady=10)
        t = ttk.Treeview(f, columns=heads, show="headings")
        for h in heads: t.heading(h, text=h); t.column(h, width=100, anchor="center")
        t.pack(fill="both", expand=True); return t

    def save_tx(self):
        try:
            q, p = float(self.t_qty.get()), float(self.t_prc.get())
            requests.post(f"{API_URL}/transactions", json={"side": "sell" if self.t_side.get() == "SATIŞ" else "buy", "qty": q, "unit_price": p, "symbol": self.t_sym.get(), "total_price": q*p})
            messagebox.showinfo("Tamam", "İşlem kaydedildi."); self.refresh_all()
        except: messagebox.showerror("Hata", "Lütfen değerleri kontrol edin.")

    def save_margins(self):
        for s, (be, se) in self.m_ins.items():
            requests.post(f"{API_URL}/settings/margins", params={"symbol":s, "buy_margin":be.get(), "sell_margin":se.get()})
        messagebox.showinfo("Başarılı", "Marjlar güncellendi."); self.auto_fill()

    def refresh_all(self):
        try:
            k = requests.get(f"{API_URL}/reports/kasa").json()
            self.lbl_cash.configure(text=f"{k['current_cash_tl']:,.2f} TL")
            self.lbl_gold.configure(text=f"{k['current_gold_stock']:,.3f} gr")
        except: pass

    def show_repo(self): self.switch("repo"); self.refresh_all()
    def show_stock(self): self.switch("stock")
    def show_cust(self): self.switch("cust")
    def show_settings(self): self.switch("set")

    def start_loops(self):
        def loop():
            while True:
                try:
                    p = requests.get(f"{API_URL}/prices", timeout=2).json()
                    for s, l in self.p_widgets.items():
                        if s in p: l.configure(text=f"{p[s]['sell']:,.2f} TL")
                except: pass
                time.sleep(10)
        threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app = KuyumcuProApp()
    app.mainloop()
