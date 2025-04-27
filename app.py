import streamlit as st
import time
import os
from scraper import fetch_page, get_all_website_links, is_valid_url, process_content, hash_content
from document_processor import create_document
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# --- Streamlit Config ---
st.set_page_config(
    page_title="Web Kazıma Aracı",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS stillerini ekleyelim
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #0D47A1;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .success-message {
        padding: 10px;
        background-color: #d4edda;
        color: #155724;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .warning-message {
        padding: 10px;
        background-color: #fff3cd;
        color: #856404;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .error-message {
        padding: 10px;
        background-color: #f8d7da;
        color: #721c24;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .info-card {
        border-left: 5px solid #1E88E5;
        padding: 15px;
        background-color: #f8f9fa;
        margin: 10px 0;
    }
    .settings-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .results-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

seen_hashes = set()

# --- Sidebar ---
with st.sidebar:
    st.image('https://www.svgrepo.com/show/374122/spider.svg', width=100)
    st.markdown("<h1 style='text-align: center;'>Ayarlar</h1>", unsafe_allow_html=True)
    
    with st.expander("📌 Genel Ayarlar", expanded=True):
        mode = st.radio("Kazıma Modu", ["Tek URL", "Tüm Site"], 
                         help="Tek bir sayfayı ya da tüm site sayfalarını kazımak için seçin")
        
        url = st.text_input("URL girin:", 
                            placeholder="https://example.com",
                            help="Kazıma işleminin başlayacağı URL")
        
        save_dir = st.text_input("Kayıt Klasörü:", 
                                 value="kazima_sonuclari",
                                 help="DOCX dosyalarının kaydedileceği klasör")
    
    with st.expander("🔍 Element Seçenekleri", expanded=True):
        col1, col2 = st.columns(2)
        opts = {}
        
        with col1:
            for lvl in range(1, 4):
                opts[f'h{lvl}'] = st.checkbox(f'H{lvl} Başlıklar', value=True, key=f'h{lvl}_header')
            opts['p'] = st.checkbox('Paragraflar', value=True, key='paragraph_option')
            opts['div'] = st.checkbox('Div İçerikleri', value=False, key='div_content_option')
            if opts['div']:
                opts['filter_divs'] = st.checkbox('Gereksiz Divleri Filtrele', 
                                                value=True,
                                                key='filter_divs_option',
                                                help="Menü, sidebar, popup gibi gereksiz içerikleri filtreler")
        
        with col2:
            for lvl in range(4, 7):
                opts[f'h{lvl}'] = st.checkbox(f'H{lvl} Başlıklar', value=False, key=f'h{lvl}_header2')
            opts['lists'] = st.checkbox('Listeler', value=True, key='lists_option')
            opts['headers'] = st.checkbox('Header', value=False, key='header_option')
            opts['footers'] = st.checkbox('Footer', value=False, key='footer_option')
            opts['span'] = st.checkbox('Span İçerikleri', value=False,
                                     key='span_content_option',
                                     help="Sadece özel içerikli span'ları alır")
        
        st.divider()
        
    
    if mode == "Tüm Site":
        with st.expander("🌐 Site Kazıma Ayarları", expanded=True):
            depth = st.slider("Link Derinliği", 1, 5, 2, 
                             help="Kaç seviye derinliğe kadar linkleri takip edeceğinizi belirler")
            maxp = st.slider("Maksimum Sayfa", 10, 500, 50, 
                            help="Kazınacak maksimum sayfa sayısı")
    
    st.divider()
    start_button = st.button("🚀 Kazımayı Başlat", use_container_width=True)
    
    st.markdown("""
    <div style="
        background-color: #333;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
    <h3>İpuçları</h3>
    <ul>
        <li>Site kazımada derinlik artışı işlem süresini uzatır</li>
        <li>Bazı siteler otomatik kazımayı engeller endişelenmeyin</li>
        <li>Benzer içerikler otomatik atlanır</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# --- Main Content ---
st.markdown("<h1 class='main-header'>🕸️ Web Kazıma Aracı</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 İşlem", "📊 Sonuçlar", "❓ Yardım"])

with tab1:
    if not start_button:
        st.info("👈 Ayarları yapılandırın ve başlatmak için soldaki butona tıklayın.")
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image("https://www.svgrepo.com/show/374116/spider-web.svg", width=300)
    
    if start_button:
        if not is_valid_url(url):
            st.error("❌ Geçerli bir URL girmelisiniz. Örnek: https://example.com")
        else:
            tasks = []
            visited = set()
            domain = urlparse(url).netloc
            
            with st.spinner("🔍 URL'ler toplanıyor..."):
                if mode == "Tek URL":
                    html = fetch_page(url)
                    if html:
                        tasks.append((url, html))
                else:
                    status_text = st.empty()
                    progress_bar = st.progress(0)
                    to_visit = [(url, 0)]
                    
                    while to_visit and len(visited) < maxp:
                        current_url, level = to_visit.pop(0)
                        if current_url in visited or level > depth:
                            continue
                            
                        visited.add(current_url)
                        status_text.text(f"🔎 İnceleniyor: {current_url}")
                        
                        html = fetch_page(current_url)
                        if html:
                            tasks.append((current_url, html))
                            
                            if level < depth:
                                new_links = get_all_website_links(current_url, domain)
                                for link in new_links:
                                    if link not in visited and is_valid_url(link):
                                        to_visit.append((link, level + 1))
                        
                        progress_bar.progress(min(1.0, len(visited)/maxp))
                        status_text.text(f"📄 Toplam {len(tasks)} sayfa bulundu ({len(visited)} URL ziyaret edildi)")
                        time.sleep(0.1)
            
            if tasks:
                st.markdown(f"### 📃 Toplam {len(tasks)} sayfa işlenecek")
                
                succ = 0
                fail = 0
                results = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                result_area = st.container()
                
                for i, (u, html) in enumerate(tasks):
                    status_text.text(f"⚙️ İşleniyor: {u}")
                    soup = BeautifulSoup(html, 'html.parser')
                    cont = process_content(soup, opts)
                    hash_val = hash_content(cont)
                    
                    if hash_val in seen_hashes:
                        results.append(("warning", f"⚠️ Benzer içerik atlandı: {u}"))
                        fail += 1
                    elif len(cont) > 1:
                        seen_hashes.add(hash_val)
                        fname = create_document(cont, save_dir, u, i)
                        results.append(("success", f"✅ Kaydedildi: {u} → {fname}"))
                        succ += 1
                    else:
                        results.append(("error", f"❌ İçerik bulunamadı: {u}"))
                        fail += 1
                    
                    progress_bar.progress((i+1)/len(tasks))
                    
                    with result_area:
                        for res_type, res_text in results[-5:]:
                            if res_type == "success":
                                st.success(res_text)
                            elif res_type == "warning":
                                st.warning(res_text)
                            else:
                                st.error(res_text)
                
                status_text.text("")
                st.balloons()
                
                st.markdown("## 📊 İşlem Özeti")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Toplam İşlenen", len(tasks))
                with col2:
                    st.metric("Başarılı", succ)
                with col3:
                    st.metric("Başarısız", fail)
                
                st.success(f"✅ İşlem tamamlandı! Dosyalar '{save_dir}' klasörüne kaydedildi.")
            else:
                st.error("❌ İşlenecek sayfa bulunamadı. Lütfen farklı bir URL deneyin.")

with tab2:
    if os.path.exists(save_dir):
        files = [f for f in os.listdir(save_dir) if f.endswith('.docx')]
        if files:
            st.markdown(f"## 📁 Kayıtlı Dosyalar ({len(files)})")
            
            file_data = []
            for i, file in enumerate(sorted(files)):
                file_size = os.path.getsize(os.path.join(save_dir, file)) / 1024
                created_time = os.path.getctime(os.path.join(save_dir, file))
                file_data.append({
                    "No": i+1,
                    "Dosya Adı": file,
                    "Boyut": f"{file_size:.1f} KB",
                    "Oluşturulma": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_time))
                })
            
            st.dataframe(file_data, use_container_width=True)
            
            st.markdown("### 📈 Dosya İstatistikleri")
            total_size = sum([os.path.getsize(os.path.join(save_dir, f)) for f in files]) / 1024
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Toplam Dosya", len(files))
            with col2:
                st.metric("Toplam Boyut", f"{total_size:.1f} KB")
        else:
            st.info("📂 Henüz kaydedilmiş dosya bulunmuyor.")
    else:
        st.info("📂 Kayıt klasörü henüz oluşturulmadı.")

with tab3:
    st.markdown("## 🔍 Web Kazıma Aracı Kullanım Kılavuzu")
    
    st.markdown("""
    ### 📌 Genel Kullanım
    1. **URL Girişi**: Kazıma yapılacak web sitesinin URL'sini girin
    2. **Kazıma Modu**: İki seçenek bulunur:
       - **Tek URL**: Sadece girilen URL'yi kazır
       - **Tüm Site**: Girilen URL'den başlayarak siteyi dolaşır ve bulduğu sayfaları kazır
    
    ### 🔧 Özelleştirme Seçenekleri
    - **Element Seçimi**: Hangi HTML elementlerinin kazınacağını seçin
      - **H1-H6**: Farklı seviyedeki başlıklar
      - **Paragraflar**: `<p>` elementleri
      - **Div İçerikleri**: `<div>` elementleri
      - **Span İçerikleri**: Özel içerikli `<span>` elementleri (soru-cevap bölümleri gibi)
      - **Listeler**: `<ul>` ve `<ol>` liste elementleri
      - **Header/Footer**: Sayfa üstü ve altı bölümler
    
    ### 📋 Sonuçlar
    - Kazınan içerikler Microsoft Word (.docx) formatında kaydedilir
    - Her sayfa için ayrı bir dosya oluşturulur
    - Dosya isimleri URL yapısına göre otomatik oluşturulur
    
    ### ⚠️ Önemli Notlar
    - Bazı siteler otomatik kazımayı engelleyebilir (CAPTCHA, IP engelleme vb.)
    - Site kazıma yasal sınırlamalara dikkat edilerek yapılmalıdır
    - Çok fazla sayfa kazımanız durumunda işlem uzun sürebilir
    - Benzer içerikler otomatik olarak atlanır
    """)
    
    with st.expander("💡 İpuçları ve Püf Noktalar"):
        st.markdown("""
        - **Site Ağacını Anlamak**: Önce tek URL modunda birkaç sayfa deneyerek içerik yapısını analiz edin
        - **Doğru Element Seçimi**: 
          - Gereksiz elementleri işaretlemeyin, bu işlemi hızlandırır
          - **Span İçerikleri** seçeneğini sadece accordion/soru-cevap bölümleri için açın
        - **Derinlik Ayarı**: Büyük sitelerde derinliği düşük tutun (1-2), aksi halde işlem çok uzayabilir
        - **URL Yapısı**: Bazı sitelerde parametre içeren URL'ler (? işareti ile başlayan) aynı içeriği farklı URL'lerle sunar
        - **Filtreleme**: Sonuç klasöründe elde edilen dosyaları içerik açısından kontrol edin
        """)
    
    with st.expander("🛠️ Sorun Giderme"):
        st.markdown("""
        - **Bağlantı Hataları**: Site erişilebilir olduğundan emin olun
        - **İçerik Bulunamadı**: 
          - Seçtiğiniz element türlerini genişletin
          - **Span içeren accordionlar** için "Span İçerikleri" seçeneğini açın
        - **Yavaş Çalışma**: Derinliği ve maksimum sayfa sayısını azaltın
        - **Boş Dosyalar**: 
          - Sitenin içerik yapısı farklı olabilir, elementleri tekrar kontrol edin
          - Özel içerikler (accordionlar) için doğru element seçimini yaptığınızdan emin olun
        - **Eksik Soru-Cevap İçeriği**:
          - "Span İçerikleri" seçeneğini açın
          - "Div İçerikleri" seçeneğiyle birlikte deneyin
          - Filtreleme seçeneklerini geçici olarak kapatıp test edin
        """)
    
    with st.expander("🔎 Özel İçerikler (Accordion/SSS) Yakalama"):
        st.markdown("""
        ### Span İçindeki Accordionlar İçin:
        1. **Span İçerikleri** seçeneğini açın
        2. **Gereksiz Divleri Filtrele** seçeneği açık kalabilir
        3. Aşağıdaki yapıları otomatik tanır:
           - Class veya ID'sinde şu kelimeler geçenler:
             - `accordion`, `faq`, `soru`, `cevap`, `sss`
             - `question`, `answer`, `collapsible`, `toggle`
             - `sıkça-sorulan`, `vs-soru`, `faq-item`
        
        ### Div İçindeki Accordionlar İçin:
        1. **Div İçerikleri** seçeneğini açın
        2. Yukarıdaki anahtar kelimeleri içeren divler otomatik alınır
        
        ### Tavsiyeler:
        - Önce tek sayfada test yapın
        - Farklı element kombinasyonlarını deneyin
        - Çok fazla span içeriği alınıyorsa, "Span İçerikleri"ni kapatıp sadece divleri deneyin
        """)

# Footer
st.markdown("---")
st.markdown("### 🛠️ Web Kazıma Aracı vSpecial :) | Geliştirici: Emir Türker")
st.caption("Bu aracı QmindLab'e özeldir.")