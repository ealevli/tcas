import streamlit as st
import pandas as pd
import time
import io
import base64 # Arka planı kodlamak için

# Selenium kütüphaneleri
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

# Resim dosyasını Base64 formatına çeviren fonksiyon
@st.cache_data
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# scrape_data fonksiyonunun en güncel hali
def scrape_data(username, password, case_numbers, status_placeholder):
    scraped_data = []
    driver = None
    
    try:
        status_placeholder.info("🚀 Sunucu ortamı için tarayıcı hazırlanıyor...")
        
        # --- Headless mod için Chrome ayarları ---
        options = webdriver.ChromeOptions()
        options.add_argument("--headless") # Tarayıcıyı görünmez modda çalıştırır
        options.add_argument("--no-sandbox") # Sunucu ortamlarında gerekli bir güvenlik ayarı
        options.add_argument("--disable-dev-shm-usage") # Bellek kullanımıyla ilgili sorunları önler
        options.add_argument("--disable-gpu") # Sunucuda GPU olmadığı için kapatılır
        
        # Servis ve ayarları birleştirerek sürücüyü başlat
        driver = webdriver.Chrome(options=options)
        
        # --------------------------------------------------
        
        driver.maximize_window() # Headless modda bu satırın etkisi olmayabilir ama kalmasında zarar yok
        
        LOGIN_URL = "https://dtag.tcas.cloud.tbintra.net/siebel/app/callcenter/enu/"
        
        try:
            status_placeholder.info(f"🔗 Ana giriş sayfasına gidiliyor...")
            driver.get(LOGIN_URL)
        except WebDriverException as e:
            if "net::" in str(e) or "timeout" in str(e):
                status_placeholder.error("❌ HATA: Yetkisiz Bilgisayar / VPN'i kontrol edin")
                return []
            else:
                raise e

        # ... fonksiyonun geri kalanı (giriş yapma, arama, veri çekme) aynı kalacak ...
        wait = WebDriverWait(driver, 20)
        
        status_placeholder.info("1/3: 'Daimler Truck Account' ile giriş butonu aranıyor...")
        daimler_login_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(., 'Login with Daimler Truck Account')]")
        ))
        daimler_login_button.click()

        status_placeholder.info("2/3: Kullanıcı adı alanı aranıyor...")
        userid_field = wait.until(EC.presence_of_element_located((By.NAME, "login_id")))
        userid_field.send_keys(username)
        
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='İleri']")))
        next_button.click()

        status_placeholder.info("3/3: Şifre alanı aranıyor...")
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.send_keys(password)
        
        final_login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Oturum aç']")))
        final_login_button.click()
        
        status_placeholder.success("✅ Giriş yapıldı, ana sayfa bekleniyor...")
        
        wait.until(EC.presence_of_element_located((By.ID, "dashsearchinp")))
        
        for i, case_number in enumerate(case_numbers):
            status_placeholder.info(f"🔄 Vaka ({i+1}/{len(case_numbers)}) işleniyor: {case_number}")
            try:
                search_box = driver.find_element(By.ID, "dashsearchinp")
                search_box.clear()
                search_box.send_keys(case_number)
                
                search_button = driver.find_element(By.ID, "dashsearchbut")
                search_button.click()
                
                status_placeholder.info(f"Veriler aranıyor...")

                customer_name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label='Driver Name']")))
                phone_number_element = driver.find_element(By.CSS_SELECTOR, "input[aria-label='Driver Phone']")
                
                customer_name = customer_name_element.get_attribute('value')
                phone_number = phone_number_element.get_attribute('value')
                
                scraped_data.append({
                    "Vaka Numarası": case_number, "Müşteri Adı": customer_name, "Telefon Numarası": phone_number, "Durum": "Başarılı"
                })
                status_placeholder.info(f"👍 Veri başarıyla çekildi: {customer_name}")

            except Exception as e:
                st.warning(f"⚠️ {case_number} işlenirken hata oluştu. Hata: {str(e)[:100]}")
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

# --- STREAMLIT ARAYÜZ KISMI ---
st.set_page_config(page_title="S24H Veri Çekme Aracı", layout="wide")

# Arka plan resmini ayarla
def set_bg_from_local(image_file):
    image_as_base64 = get_base64_of_bin_file(image_file)
    bg_image_style = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{image_as_base64}");
        background-size: cover;
    }}
    </style>
    """
    st.markdown(bg_image_style, unsafe_allow_html=True)

# assets klasöründeki arka plan resmini kullan
set_bg_from_local("assets/background.png")


# Logoyu ortalamak için sütunlar oluştur ve logoyu ekle
col1, col2, col3 = st.columns([2,3,2])
with col2:
    # assets klasöründeki logoyu kullan
    st.image("assets/logo.png")

# Başlığı ortalamak için markdown kullan
st.markdown("<h1 style='text-align: center; color: white;'>S24H Veri Çekme Otomasyon Aracı</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: white;'>Bu araç, bir Excel dosyasından okuduğu vaka numaralarına ait bilgileri otomatik olarak çeker.</p>", unsafe_allow_html=True)

st.warning("**ÖNEMLİ:** Bu uygulamayı çalıştırmadan önce **şirket VPN bağlantınızın aktif olduğundan** emin olun!")

# Form ve dosya yükleme kısmı
uploaded_file = st.file_uploader(
    "Vaka numaralarını içeren Excel dosyasını yükleyin (.xlsx, .xls)", 
    type=["xlsx", "xls"]
)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Excel dosyası başarıyla okundu. İşte ilk 5 satır:")
        st.dataframe(df.head())
        
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
                case_list = df[selected_column].dropna().astype(str).tolist()
                
                if not case_list:
                    st.error("Seçtiğiniz sütunda hiç vaka numarası bulunamadı.")
                else:
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
