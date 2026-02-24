import customtkinter as ctk
import requests, time
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from frontend.core.config import API_URL

class DashboardMixin:
    def setup_dash(self):
        d = self.pages['dash']
        d.grid_columnconfigure((0, 1), weight=1)
        d.grid_rowconfigure(1, weight=1)
        self.ai_row = ctk.CTkFrame(d, fg_color='#34495e', height=40, corner_radius=15)
        self.ai_row.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='ew')
        self.ai_lbl = ctk.CTkLabel(self.ai_row, text='Kuyumcu AI: Dükkan verileri analiz ediliyor...', font=ctk.CTkFont(slant='italic'))
        self.ai_lbl.pack(side='left', padx=20, pady=10)
        self.ai_btn = ctk.CTkButton(self.ai_row, text='ÖNERİYİ UYGULA', fg_color='#9b59b6', command=self.apply_ai_suggestion)
        mid_row = ctk.CTkFrame(d, fg_color='transparent')
        mid_row.grid(row=1, column=0, columnspan=2, sticky='nsew')
        mid_row.grid_columnconfigure((0, 1), weight=1)
        f_buy = ctk.CTkFrame(mid_row, fg_color='#1a252f', corner_radius=15)
        f_buy.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        ctk.CTkLabel(f_buy, text='MÜŞTERİDEN GELEN (ALIŞ)', font=ctk.CTkFont(weight='bold'), text_color='#1abc9c').pack(pady=5)
        self.b_sym = self.create_sym_grid(f_buy, 'buy')
        r_buy = ctk.CTkFrame(f_buy, fg_color='transparent')
        r_buy.pack(pady=5)
        self.b_qty = ctk.CTkEntry(r_buy, placeholder_text='Mkt', width=70, height=32)
        self.b_qty.pack(side='left', padx=5)
        self.b_prc = ctk.CTkEntry(r_buy, placeholder_text='Fyt', width=100, height=32)
        self.b_prc.pack(side='left', padx=5)
        ctk.CTkButton(r_buy, text='+ EKLE', width=70, height=32, font=ctk.CTkFont(weight='bold'), fg_color='#1abc9c', command=self.add_to_buy).pack(side='left', padx=5)
        self.b_qf = ctk.CTkFrame(f_buy, fg_color='transparent')
        self.b_qf.pack(pady=2)
        self.tree_buy = self.create_tree(f_buy, ('Birim', 'Mkt', 'Fiyat', 'Top'), ('Birim', 'Mkt', 'Fiyat', 'Top'), height=8)
        f_sell = ctk.CTkFrame(mid_row, fg_color='#2c3e50', corner_radius=15)
        f_sell.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        ctk.CTkLabel(f_sell, text='MÜŞTERİYE VERİLEN (SATIŞ)', font=ctk.CTkFont(weight='bold'), text_color='#3498db').pack(pady=5)
        self.s_sym = self.create_sym_grid(f_sell, 'sell')
        r_sell = ctk.CTkFrame(f_sell, fg_color='transparent')
        r_sell.pack(pady=5)
        self.s_qty = ctk.CTkEntry(r_sell, placeholder_text='Mkt', width=70, height=32)
        self.s_qty.pack(side='left', padx=5)
        self.s_prc = ctk.CTkEntry(r_sell, placeholder_text='Fyt', width=100, height=32)
        self.s_prc.pack(side='left', padx=5)
        ctk.CTkButton(r_sell, text='+ EKLE', width=70, height=32, font=ctk.CTkFont(weight='bold'), fg_color='#3498db', command=self.add_to_sell).pack(side='left', padx=5)
        self.s_qf = ctk.CTkFrame(f_sell, fg_color='transparent')
        self.s_qf.pack(pady=2)
        self.tree_sell = self.create_tree(f_sell, ('Birim', 'Mkt', 'Fiyat', 'Top'), ('Birim', 'Mkt', 'Fiyat', 'Top'), height=8)
        self.tree_buy.bind("<Double-1>", lambda e: self.remove_item('buy'))
        self.tree_sell.bind("<Double-1>", lambda e: self.remove_item('sell'))

        f_bot = ctk.CTkFrame(d, corner_radius=15, fg_color='#1e272e')
        f_bot.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
        self.lbl_net = ctk.CTkLabel(f_bot, text='HESAP: 0.00 TL', font=ctk.CTkFont(size=24, weight='bold'), text_color='#f1c40f')
        self.lbl_net.pack(pady=10)
        c_row = ctk.CTkFrame(f_bot, fg_color='transparent')
        c_row.pack(pady=5)
        ctk.CTkLabel(c_row, text='Müşteri:').pack(side='left', padx=5)
        self.dash_cust = ctk.CTkOptionMenu(c_row, values=['Müşteri Yok (Perakende)'], width=200)
        self.dash_cust.pack(side='left', padx=5)
        ctk.CTkLabel(c_row, text='Ödeme/Bakiye Durumu:').pack(side='left', padx=(15, 5))
        self.dash_pay = ctk.CTkOptionMenu(c_row, values=['Peşin / Kredi Kartı (Kasa)', 'Açık Hesap / Veresiye (Cari)'], width=200)
        self.dash_pay.pack(side='left', padx=5)
        btn_box = ctk.CTkFrame(f_bot, fg_color='transparent')
        btn_box.pack(pady=10)
        ctk.CTkButton(btn_box, text='TEMİZLE', fg_color='#e74c3c', width=100, command=self.clear_terazi).pack(side='left', padx=10)
        ctk.CTkButton(btn_box, text='İŞLEMİ BİTİR', fg_color='#2ecc71', width=200, height=40, command=self.finish_transaction).pack(side='left', padx=10)
        self.update_quick_buttons('buy')
        self.update_quick_buttons('sell')

    def show_dash(self):
        self.switch('dash')
        self.auto_fill_terazi('buy')
        self.auto_fill_terazi('sell')
        self.check_ai()
        self.refresh_cust_list_dash()

    def refresh_cust_list_dash(self):
        try:
            r = requests.get(f'{API_URL}/customers').json()
            self.customers_list = ['Müşteri Yok (Perakende)']
            self.cust_map = {}
            for c in r:
                name = f'{c['full_name']} - {c['phone']}'
                self.customers_list.append(name)
                self.cust_map[name] = c['id']
            self.dash_cust.configure(values=self.customers_list)
        except:
            pass

    def on_sym_change(self, side):
        sym = self.b_sym.get() if side == 'buy' else self.s_sym.get()
        if sym == 'ÜRÜN':
            self.show_product_selector(side)
        else:
            self.auto_fill_terazi(side)
            self.update_quick_buttons(side)

    def update_quick_buttons(self, side):
        f = self.b_qf if side == 'buy' else self.s_qf
        sym = self.b_sym.get() if side == 'buy' else self.s_sym.get()
        ent = self.b_qty if side == 'buy' else self.s_qty
        for w in f.winfo_children():
            w.destroy()
        if sym == 'ÜRÜN':
            return
        if sym in ['USD', 'EUR']:
            vals = [10, 50, 100, 200, 500]
        elif sym in ['CEYREK', 'YARIM', 'TAM', 'ATA']:
            vals = [1, 2, 5, 10, 20]
        else:
            vals = [1, 5, 0.25, 0.5, 10]
        for v in vals:
            ctk.CTkButton(f, text=str(v), width=35, height=22, fg_color='#34495e', command=lambda x=v, e=ent: (e.delete(0, 'end'), e.insert(0, str(x)))).pack(side='left', padx=2)

    def auto_fill_terazi(self, side):
        try:
            sym = self.b_sym.get() if side == 'buy' else self.s_sym.get()
            if sym == 'ÜRÜN':
                return
            r = requests.get(f'{API_URL}/prices/smart', timeout=1.5).json()
            p = r[sym]['suggested_buy'] if side == 'buy' else r[sym]['suggested_sell']
            (self.b_prc if side == 'buy' else self.s_prc).delete(0, 'end')
            (self.b_prc if side == 'buy' else self.s_prc).insert(0, str(p))
        except:
            pass

    def add_to_buy(self):
        try:
            sym = self.b_sym.get()
            qty_str = self.b_qty.get()
            prc_str = self.b_prc.get()
            if not qty_str or not prc_str:
                messagebox.showwarning("Uyarı", "Miktar ve fiyat girmelisiniz.")
                return
            qty = float(qty_str)
            entered_prc = float(prc_str)
            if sym == 'ÜRÜN':
                u_prc = entered_prc / qty if qty > 0 else 0
                t_prc = entered_prc
            else:
                u_prc = entered_prc
                t_prc = qty * entered_prc
            item = {'side': 'buy', 'symbol': sym, 'qty': qty, 'unit_price': u_prc, 'total_price': t_prc}
            if sym == 'ÜRÜN':
                item['product_id'] = self.b_prod_id
            self.buy_basket.append(item)
            self.b_prod_id = None
            self.update_terazi_display()
            self.b_qty.delete(0, 'end')
        except ValueError:
            messagebox.showwarning("Hata", "Lütfen geçerli sayısal değerler giriniz.")
        except Exception as e:
            messagebox.showerror("Hata", f"Beklenmedik hata: {e}")


    def add_to_sell(self):
        try:
            sym = self.s_sym.get()
            qty_str = self.s_qty.get()
            prc_str = self.s_prc.get()
            if not qty_str or not prc_str:
                messagebox.showwarning("Uyarı", "Miktar ve fiyat girmelisiniz.")
                return
            qty = float(qty_str)
            entered_prc = float(prc_str)
            if sym == 'ÜRÜN':
                u_prc = entered_prc / qty if qty > 0 else 0
                t_prc = entered_prc
            else:
                u_prc = entered_prc
                t_prc = qty * entered_prc
            item = {'side': 'sell', 'symbol': sym, 'qty': qty, 'unit_price': u_prc, 'total_price': t_prc}
            if sym == 'ÜRÜN':
                item['product_id'] = self.s_prod_id
            self.sell_basket.append(item)
            self.s_prod_id = None
            self.update_terazi_display()
            self.s_qty.delete(0, 'end')
        except ValueError:
            messagebox.showwarning("Hata", "Lütfen geçerli sayısal değerler giriniz.")
        except Exception as e:
            messagebox.showerror("Hata", f"Beklenmedik hata: {e}")


    def update_terazi_display(self):
        for t, b in [(self.tree_buy, self.buy_basket), (self.tree_sell, self.sell_basket)]:
            for i in t.get_children():
                t.delete(i)
            for x in b:
                t.insert('', 'end', values=(x['symbol'], x['qty'], x['unit_price'], round(x['total_price'], 2)))
        net = sum((x['total_price'] for x in self.sell_basket)) - sum((x['total_price'] for x in self.buy_basket))
        if net > 0:
            self.lbl_net.configure(text=f'MÜŞTERİ ÖDEMELİ: {net:,.2f} TL', text_color='#f1c40f')
        elif net < 0:
            self.lbl_net.configure(text=f'MÜŞTERİYE İADE: {abs(net):,.2f} TL', text_color='#1abc9c')
        else:
            self.lbl_net.configure(text='HESAP BAŞABAŞ (0.00 TL)', text_color='white')

    def finish_transaction(self):
        if not self.buy_basket and (not self.sell_basket):
            return
        try:
            cust_name = self.dash_cust.get()
            pay_type = 'Debt' if 'Veresiye' in self.dash_pay.get() else 'Cash'
            cid = self.cust_map.get(cust_name)
            for i in self.buy_basket + self.sell_basket:
                if cid:
                    i['customer_id'] = cid
                i['payment_type'] = pay_type
                requests.post(f'{API_URL}/transactions', json=i)
            messagebox.showinfo('Tamam', 'İşlem bitti.')
            self.clear_terazi()
            self.after(0, self.refresh_boss_data)
            self.after(0, self.refresh_vault)
            self.after(0, self.refresh_stock)
            self.after(0, self.refresh_repo_tx)
            self.after(0, self.refresh_cust)
        except Exception as e:
            messagebox.showerror('Hata', f'İşlem tamamlanamadı: {e}')

    def clear_terazi(self):
        self.buy_basket = []
        self.sell_basket = []
        self.update_terazi_display()
        self.dash_cust.set('Müşteri Yok (Perakende)')
        self.dash_pay.set('Peşin / Kredi Kartı (Kasa)')

    def remove_item(self, side):
        tree = self.tree_buy if side == 'buy' else self.tree_sell
        basket = self.buy_basket if side == 'buy' else self.sell_basket
        sel = tree.selection()
        if not sel: return
        idx = tree.index(sel[0])
        if 0 <= idx < len(basket):
            basket.pop(idx)
            self.update_terazi_display()


    def show_product_selector(self, side):
        """Stoktaki ürünleri seçmek için pencere açar"""
        win = ctk.CTkToplevel(self)
        win.title('Vitrinden Ürün Seç')
        win.geometry('500x400')
        win.attributes('-topmost', True)
        tree = self.create_tree(win, ('id', 'name', 'weight', 'purity', 'labor'), ('ID', 'Ürün', 'Gram', 'Ayar', 'İşçilik'), height=10)
        prods = requests.get(f'{API_URL}/products').json()
        self.fill_tree(tree, prods, ['id', 'name', 'weight', 'purity', 'labor_cost'])
    
        def select():
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])['values']
            if side == 'buy':
                self.b_prod_id = int(item[0])
            else:
                self.s_prod_id = int(item[0])
            qty_ent = self.b_qty if side == 'buy' else self.s_qty
            prc_ent = self.b_prc if side == 'buy' else self.s_prc
            qty_ent.delete(0, 'end')
            qty_ent.insert(0, '1')
            live = requests.get(f'{API_URL}/prices/smart').json()
            base_p = live['GA']['suggested_buy' if side == 'buy' else 'suggested_sell']
            total_p = float(item[2]) * base_p * float(item[3]) + float(item[4])
            prc_ent.delete(0, 'end')
            prc_ent.insert(0, str(round(total_p, 2)))
            win.destroy()
        ctk.CTkButton(win, text='SEÇ VE DOLDUR', command=select).pack(pady=10)

