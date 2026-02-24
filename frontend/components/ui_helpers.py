import customtkinter as ctk
from tkinter import ttk

def stat_card(parent, title, color):
    f = ctk.CTkFrame(parent, corner_radius=12, fg_color=color, height=120)
    f.pack(side="left", expand=True, padx=8, fill="both")
    ctk.CTkLabel(f, text=title, text_color="white", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(12,0))
    l = ctk.CTkLabel(f, text="0.00", text_color="white", font=ctk.CTkFont(size=20, weight="bold"))
    l.pack(pady=8)
    return l


def create_sym_grid(parent, on_sym_change_callback):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(pady=5)
    symbols = ["USD", "EUR", "GA", "C22", "CEYREK", "YARIM", "TAM", "ATA", "ÜRÜN"]
    display_map = {"USD": "$ USD", "EUR": "€ EUR"}
    btns = []
    var_val = ["USD"]
    
    def on_click(s):
        var_val[0] = s
        for b, sym in zip(btns, symbols): 
            b.configure(fg_color="#2980b9" if sym == s else "#34495e")
        on_sym_change_callback()

    for i, s in enumerate(symbols):
        disp = display_map.get(s, s)
        b = ctk.CTkButton(f, text=disp, width=54, height=35, font=ctk.CTkFont(size=11, weight="bold"),
                          fg_color="#2980b9" if s == "USD" else "#34495e",
                          command=lambda v=s: on_click(v))
        b.grid(row=i//5, column=i%5, padx=2, pady=2)
        btns.append(b)
        
    class PosProxy:
        def get(self): return var_val[0]
        def set(self, val):
            var_val[0] = val
            for b, sym in zip(btns, symbols): 
                b.configure(fg_color="#2980b9" if sym == val else "#34495e")
    return PosProxy()


def create_tree(parent, cols, heads, height=10):
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


def fill_tree(tree, data, keys):
    for i in tree.get_children(): tree.delete(i)
    for row in data:
        vals = [row.get(k, "") for k in keys]
        if "ts" in keys:
            idx = keys.index("ts")
            vals[idx] = str(vals[idx])[:16].replace("T", " ")
        tree.insert("", "end", values=vals)
