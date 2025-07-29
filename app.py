import streamlit as st
import pandas as pd
import time
import io

# --- SELENIUM KISMI ---
# Bu kısım öncekiyle aynı, herhangi bir değişiklik yapmanıza gerek yok.
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_data(username, password, case_numbers, status_placeholder):
    scraped_data = []
    driver = None
    
    try:
        status_placeholder.info("🚀 Tarayıcı başlatılıyor... (Bu işlem sırasında yeni bir Chrome penceresi açılacak)")
        driver = webdriver.Chrome()
        driver.maximize_window()
        
        LOGIN_URL = "https://portal.ornek-sirket.com/login" # GERÇEK GİRİŞ URL'SİNİ GİRİN
        
        status_placeholder.info(f"🔗 Giriş sayfasına gidiliyor: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        wait = WebDriverWait(driver, 20)
        
        status_placeholder.info("🔒 Kullanıcı adı ve şifre giriliyor...")
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username_field_id"))) # GERÇEK ID'Yİ GİRİN
        username_field.send_keys(username)

        password_field = driver.find_element(By.ID, "password_field_id") # GERÇEK ID'Yİ GİRİN
        password_field.send_keys(password)

        login_button = driver.find_element(By.XPATH, "//button[@type='submit']") # GERÇEK XPATH'İ GİRİN
        login_button.click()
        
        status_placeholder.info("✅ Giriş yapıldı, ana sayfa bekleniyor...")
        
        wait.until(EC.presence_of_element_located((By.ID, "search_case_input"))) # GERÇEK ID'Yİ GİRİN
        
        for i, case_number in enumerate(case_numbers):
            status_placeholder.info(f"🔄 Vaka ({i+1}/{len(case_numbers)}) işleniyor: {case_number}")
            try:
                search_box = driver.find_element(By.ID, "search_case_input") # GERÇEK ID'Yİ GİRİN
                search_box.clear()
                search_box.send_keys(case_number)
                
                search_button = driver.find_element(By.ID, "search_button_id") # GERÇEK ID'Yİ GİRİN
                search_button.click()
                
                customer_name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".customer-name-class")))
                phone_number_element = driver.find_element(By.CSS_SELECTOR, "#customer-phone-div > span")
                
                customer_name = customer_name_element.text
                phone_number = phone_number_element.text
                
                scraped_data.append({
                    "Vaka Numarası": case_number, "Müşteri Adı": customer_name, "Telefon Numarası": phone_number, "Durum": "Başarılı"
                })

            except Exception as e:
                st.warning(f"⚠️ {case_number} işlenirken hata oluştu. Devam ediliyor. Hata: {str(e)[:100]}")
                scraped_data.append({
                    "Vaka Numarası": case_number, "Müşteri Adı": "HATA", "Telefon Numarası": "HATA", "Durum": "Hata"
                })
                continue
        
        status_placeholder.success("🎉 Tüm işlemler başarıyla tamamlandı!")
        return scraped_data

    except Exception as e:
        status_placeholder.error(f"❌ Genel bir hata oluştu: {e}")
        return scraped_data
    
    finally:
        if driver:
            driver.quit()

# --- STREAMLIT ARAYÜZ KISMI (DEĞİŞİKLİKLER BURADA) ---

st.set_page_config(page_title="S24H Veri Çekme Aracı", layout="wide")

st.title("S24H Veri Çekme Otomasyon Aracı")
st.markdown("Bu araç, bir Excel dosyasından okuduğu vaka numaralarına ait müşteri ve telefon bilgilerini otomatik olarak çeker.")

st.warning("**ÖNEMLİ:** Bu uygulamayı çalıştırmadan önce **şirket VPN bağlantınızın aktif olduğundan** emin olun!")

# --- YENİ BÖLÜM: EXCEL DOSYASI YÜKLEME ---
uploaded_file = st.file_uploader(
    "Vaka numaralarını içeren Excel dosyasını yükleyin (.xlsx, .xls)", 
    type=["xlsx", "xls"]
)

# Dosya yüklendikten sonra çalışacak bölüm
if uploaded_file is not None:
    try:
        # Yüklenen excel dosyasını bir pandas DataFrame'e oku
        df = pd.read_excel(uploaded_file)
        st.success("✅ Excel dosyası başarıyla okundu. İşte ilk 5 satır:")
        st.dataframe(df.head()) # Dosyanın ilk 5 satırını kullanıcıya göster
        
        # DataFrame'deki sütunlardan birini seçmesi için kullanıcıya bir menü göster
        columns = df.columns.tolist()
        selected_column = st.selectbox("Lütfen vaka numaralarını içeren sütunu seçin:", columns)

        with st.form("input_form"):
            st.markdown("---")
            st.subheader("Giriş Bilgileri")
            username = st.text_input("TBDIR Uzantılı Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            
            submitted = st.form_submit_button("İşlemi Başlat")

        status_placeholder = st.empty()
        results_placeholder = st.empty()

        if submitted:
            if not username or not password:
                st.error("Lütfen giriş bilgilerinizi eksiksiz doldurun.")
            else:
                # Seçilen sütundaki verileri bir listeye çevir. Boş satırları atla.
                case_list = df[selected_column].dropna().astype(str).tolist()
                
                if not case_list:
                    st.error("Seçtiğiniz sütunda hiç vaka numarası bulunamadı.")
                else:
                    # Ana scraping fonksiyonunu çalıştır
                    final_data = scrape_data(username, password, case_list, status_placeholder)
                    
                    if final_data:
                        result_df = pd.DataFrame(final_data)
                        results_placeholder.dataframe(result_df)
                        
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='VakaVerileri')
                        
                        st.download_button(
                            label="📥 Sonuçları Excel Olarak İndir",
                            data=output.getvalue(),
                            file_name="vaka_verileri_sonuc.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
    except Exception as e:
        st.error(f"Excel dosyası okunurken bir hata oluştu: {e}")