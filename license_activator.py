import sys
import os
import requests
import customtkinter as ctk
from tkinter import messagebox

# Proje kök dizini (Arayüzde API_URL = http://127.0.0.1:8000 vb. için config içinden alınabilir)
# Burada direkt URL de girilebilir.
API_URL = "http://127.0.0.1:8000"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LicenseWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kuyumcu Pro AI - Lisans Yükseltme")
        self.geometry("400x350")
        self.eval('tk::PlaceWindow . center')
        
        ctk.CTkLabel(self, text="💎 PREMIUM YÜKSELTME", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f1c40f").pack(pady=(30, 10))
        ctk.CTkLabel(self, text="KuyumcuPro.com'dan aldığınız\nLisans (Aktivasyon) Anahtarını giriniz:", font=ctk.CTkFont(size=14)).pack(pady=10)
        
        self.license_key = ctk.CTkEntry(self, placeholder_text="XXXX-XXXX-XXXX-XXXX", height=45, font=ctk.CTkFont(size=14), justify="center")
        self.license_key.pack(pady=15, padx=40, fill="x")
        
        ctk.CTkButton(self, text="LİSANSI DOĞRULA VE AKTİF ET", height=45, fg_color="#2ecc71", font=ctk.CTkFont(size=14, weight="bold"), command=self.activate_license).pack(pady=15, padx=40, fill="x")

    def activate_license(self):
        key = self.license_key.get().strip()
        if not key:
            messagebox.showwarning("Uyarı", "Lütfen bir lisans anahtarı giriniz.")
            return
            
        # 1. Aşama: Web Sitesinden Doğrulama (Opsiyonel / İleride sunucunuzdan yapabilirsiniz)
        # Şimdilik "PRO-2026-..." veya bizim belirlediğimiz özel kod ile yerel aktivasyon yapıyoruz
        if key.startswith("PRO-") and len(key) >= 12:
            try:
                # 2. Aşama: Uygulamaya Premium Anahtarını Kaydet (Yerel API'ye bildir)
                r = requests.post(f"{API_URL}/system/activate", json={"license_key": key})
                if r.status_code == 200:
                    messagebox.showinfo("Başarılı!", "🎉 Tebrikler! Premium özellikler (Sınırsız İşlem, Boss Panel, Sınırsız Müşteri vb.) anında açıldı.\nLütfen programı kapatıp tekrar açın.")
                    self.destroy()
                else:
                    messagebox.showerror("Hata", f"Aktivasyon sunucusunda hata. Kodu kontrol edin. ({r.text})")
            except Exception as e:
                messagebox.showerror("Hata", f"Sisteme (Arka plana) bağlanılamadı. Lütfen sunucunun (kuyumcu_pro.py) açık olduğundan emin olun.\nDetay: {e}")
        else:
            messagebox.showerror("Geçersiz Anahtar", "Girdiğiniz lisans anahtarı geçersiz veya hatalı. Lütfen KuyumcuPro.com üzerinden aldığınız PRO anahtarını kontrol edin.")

if __name__ == "__main__":
    app = LicenseWindow()
    app.mainloop()
