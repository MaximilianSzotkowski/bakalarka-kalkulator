import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# -----------------------------------------------------------------------------
# 1. NASTAVENÍ STRÁNKY A DESIGN
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Kalkulátor KZS | VUT Brno",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. HLAVIČKA (Přesně podle vašeho Excelu)
col_logo, col_header = st.columns([1, 5])

with col_header:
    st.title("ANALÝZA SOUVRSTVÍ KZS U NÍZKOENERGETICKÝCH DOMŮ")
    st.markdown("""
    **Autor:** Maximilian Szotkowski | **Vedoucí:** Ing. et Ing. Martin Tuscher, Ph.D.  
    **Škola:** Vysoké učení technické v Brně | Fakulta stavební | Ústav stavební ekonomiky a řízení  
    **Akademický rok:** 2025/2026
    """)
    st.caption("© 2026 Maximilian Szotkowski. Aplikace pro multikriteriální porovnání variant zateplení.")

st.markdown("---")

# -----------------------------------------------------------------------------
# 3. MOZEK APLIKACE (Simulace databáze)
# -----------------------------------------------------------------------------
# Zde simulujeme vaše CSV tabulky, aby to fungovalo hned bez načítání souborů
def get_cihla_data(nazev):
    data = {
        "Porotherm 44 Profi (Jednovrstvé)": {"U": 0.19, "Cena": 2850, "GWP": 42.0, "Tloustka": 440},
        "Heluz Family 50 2in1 (Jednovrstvé)": {"U": 0.11, "Cena": 3400, "GWP": 38.5, "Tloustka": 500},
        "Ytong Lambda YQ 450 (Jednovrstvé)": {"U": 0.18, "Cena": 2600, "GWP": 28.0, "Tloustka": 450},
        "Stará Plná Cihla 450mm (Rekonstrukce)": {"U": 1.45, "Cena": 0, "GWP": 0, "Tloustka": 450}, # Cena 0 protože už stojí
        "Porotherm 30 Profi (Nosné pro ETICS)": {"U": 0.50, "Cena": 1600, "GWP": 25.0, "Tloustka": 300},
    }
    return data.get(nazev, data["Porotherm 30 Profi (Nosné pro ETICS)"])

def get_etics_data(typ, tloustka):
    # Ceny jsou orientační součet (Izolant + Lepidlo + Hmoždinky + Omítka)
    base_price = 0
    lambda_val = 0.039
    gwp_base = 5.0
    
    if typ == "EPS 70F (Polystyren)":
        base_price = 1100 + (tloustka * 2.5)
        lambda_val = 0.039
        gwp_base = 10 + (tloustka * 0.1)
    elif typ == "MWF (Minerální vata)":
        base_price = 1400 + (tloustka * 4.0)
        lambda_val = 0.036
        gwp_base = 12 + (tloustka * 0.15)
    elif typ == "Fenolická pěna":
        base_price = 2100 + (tloustka * 5.0)
        lambda_val = 0.022
        gwp_base = 20 + (tloustka * 0.2)
        
    return {"Cena_m2": base_price, "Lambda": lambda_val, "GWP_m2": gwp_base}

# -----------------------------------------------------------------------------
# 4. BOČNÍ PANEL (Vstupy pro ekonomiku)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Globální nastavení")
    
    # Přepínač Referenční varianty
    rezim = st.selectbox(
        "Referenční scénář:",
        ("Porovnat s JZ (Novostavba)", "Rekonstrukce (Stávající stav)")
    )
    
    st.subheader("Energie a Ekonomika")
    cena_energie = st.number_input("Cena energie [Kč/kWh]", value=5.0, step=0.1)
    hdd = st.number_input("Počet denostupňů (HDD)", value=3800)
    doba_hodnoceni = st.slider("Doba hodnocení [roky]", 10, 50, 30)
    
    st.info("ℹ️ Toto nastavení ovlivňuje výpočet návratnosti.")

# -----------------------------------------------------------------------------
# 5. HLAVNÍ VÝBĚR SKLADEB (To je váš Dashboard)
# -----------------------------------------------------------------------------

col_ref, col_arrow, col_navrh = st.columns([10, 1, 10])

# --- LEVÝ SLOUPEC (REFERENCE / NOSNÉ ZDIVO) ---
with col_ref:
    st.subheader("🧱 A) Nosné zdivo / Reference")
    
    if rezim == "Rekonstrukce (Stávající stav)":
        cihla_nazev = st.selectbox("Typ stávajícího zdiva:", ["Stará Plná Cihla 450mm (Rekonstrukce)"])
        # Pro rekonstrukci nevolíme ETICS vlevo
        izolant_nazev_ref = "Žádný (Původní stav)"
        tloustka_izolace_ref = 0
        
    else: # Novostavba
        cihla_nazev = st.selectbox("Vyberte Zdivo:", [
            "Porotherm 44 Profi (Jednovrstvé)",
            "Heluz Family 50 2in1 (Jednovrstvé)",
            "Ytong Lambda YQ 450 (Jednovrstvé)",
            "Porotherm 30 Profi (Nosné pro ETICS)"
        ])
        # V režimu novostavba se levá strana bere jako "Referenční Jednovrstvé" nebo "Nosné pod ETICS"
        izolant_nazev_ref = "Žádný (Bez zateplení)"
        tloustka_izolace_ref = 0

    # Načtení dat cihly
    cihla_data = get_cihla_data(cihla_nazev)
    
    # Výpočet hodnot Reference
    ref_U = cihla_data["U"]
    ref_Cena = cihla_data["Cena"]
    ref_GWP = cihla_data["GWP"]
    ref_Tloustka = cihla_data["Tloustka"]

    # Karta s výsledky
    with st.container(border=True):
        st.markdown(f"**{cihla_nazev}**")
        c1, c2 = st.columns(2)
        c1.metric("Cena investice", f"{ref_Cena:.0f} Kč/m²")
        c2.metric("Součinitel U", f"{ref_U:.2f} W/m²K")
        st.metric("Tloušťka stěny", f"{ref_Tloustka} mm")

# --- PROSTŘEDNÍ SLOUPEC (ŠIPKA) ---
with col_arrow:
    st.markdown("<br><br><br><div style='text-align: center; font-size: 40px;'>🆚</div>", unsafe_allow_html=True)

# --- PRAVÝ SLOUPEC (NÁVRH ETICS) ---
with col_navrh:
    st.subheader("🛡️ B) Návrh ETICS (Zateplení)")
    
    # Výběr izolantu
    izolant_typ = st.selectbox("Materiál izolantu:", 
                               ["EPS 70F (Polystyren)", "MWF (Minerální vata)", "Fenolická pěna"])
    
    tloustka_etics = st.slider("Tloušťka izolace [mm]:", 0, 300, 160, step=20)
    
    # Pokud je vlevo vybráno nosné zdivo (300mm), použijeme ho jako podklad.
    # Pokud je vlevo JZ (500mm), srovnáváme ho s nějakou standardní zdí (např. 300mm + ETICS).
    # Pro zjednodušení ukázky: Vždy přičteme ETICS k "Porotherm 30 Profi" jako podkladu.
    podklad_data = get_cihla_data("Porotherm 30 Profi (Nosné pro ETICS)")
    etics_data = get_etics_data(izolant_typ, tloustka_etics)
    
    # Výpočet U pro ETICS (Zjednodušený)
    # R_celkem = R_zdiva + R_izolace + R_prechod
    r_zdiva = 1 / podklad_data["U"]
    r_izolace = (tloustka_etics / 1000) / etics_data["Lambda"]
    u_novy = 1 / (r_zdiva + r_izolace + 0.17)
    
    navrh_Cena = podklad_data["Cena"] + etics_data["Cena_m2"]
    navrh_GWP = podklad_data["GWP"] + etics_data["GWP_m2"]
    navrh_Tloustka = podklad_data["Tloustka"] + tloustka_etics

    # Karta s výsledky (Dynamická barva delty)
    with st.container(border=True):
        st.markdown(f"**{izolant_typ} {tloustka_etics} mm** + Nosné zdivo")
        nc1, nc2 = st.columns(2)
        
        # Delta: Pokud je návrh levnější, je to zelené (invertujeme logiku delta_color)
        nc1.metric("Cena investice", f"{navrh_Cena:.0f} Kč/m²", 
                   f"{ref_Cena - navrh_Cena:.0f} Kč", delta_color="normal") 
        
        # Delta: Pokud je U menší, je to zelené (inverse)
        nc2.metric("Součinitel U", f"{u_novy:.3f} W/m²K", 
                   f"{u_novy - ref_U:.3f} W/m²K", delta_color="inverse")
        
        st.metric("Tloušťka stěny", f"{navrh_Tloustka} mm", 
                  f"{navrh_Tloustka - ref_Tloustka} mm", delta_color="off")

# -----------------------------------------------------------------------------
# 6. EKONOMICKÁ NÁVRATNOST (ROI)
# -----------------------------------------------------------------------------
st.subheader("💰 Ekonomická analýza a Návratnost")

# Výpočet nákladů na energii
# Q = U * 24 * HDD / 1000 (kwh)
spotreba_ref = ref_U * 24 * hdd / 1000
naklady_ref_rok = spotreba_ref * cena_energie

spotreba_navrh = u_novy * 24 * hdd / 1000
naklady_navrh_rok = spotreba_navrh * cena_energie

uspora_rok = naklady_ref_rok - naklady_navrh_rok
investice_navic = navrh_Cena - ref_Cena

# Výpis textový
col_eco1, col_eco2, col_eco3 = st.columns(3)
col_eco1.metric("Roční náklady (Reference)", f"{naklady_ref_rok:.0f} Kč/m²")
col_eco1.metric("Roční náklady (ETICS)", f"{naklady_navrh_rok:.0f} Kč/m²")

col_eco2.metric("Roční úspora", f"{uspora_rok:.0f} Kč/m²")

# Návratnost
if uspora_rok > 0:
    # Pokud je ETICS dražší na investici
    if investice_navic > 0:
        navratnost = investice_navic / uspora_rok
        col_eco3.metric("Prostá návratnost", f"{navratnost:.1f} let")
    else:
        col_eco3.metric("Návratnost", "Ihned (Investice je nižší)")
else:
    col_eco3.metric("Návratnost", "Nenastane (Proděláváte)")

# -----------------------------------------------------------------------------
# 7. GRAFY (Altair)
# -----------------------------------------------------------------------------
st.subheader("📊 Grafické porovnání")
tab1, tab2 = st.tabs(["Vývoj nákladů (TCO)", "Struktura ceny"])

with tab1:
    # Data pro graf
    chart_data = []
    cum_ref = ref_Cena
    cum_navrh = navrh_Cena
    
    for rok in range(doba_hodnoceni + 1):
        chart_data.append({"Rok": rok, "Náklady": cum_ref, "Varianta": "Reference"})
        chart_data.append({"Rok": rok, "Náklady": cum_navrh, "Varianta": "Návrh ETICS"})
        
        cum_ref += naklady_ref_rok
        cum_navrh += naklady_navrh_rok
        
    df_chart = pd.DataFrame(chart_data)
    
    c = alt.Chart(df_chart).mark_line(point=True).encode(
        x='Rok',
        y='Náklady',
        color='Varianta',
        tooltip=['Rok', 'Náklady', 'Varianta']
    ).interactive()
    
    st.altair_chart(c, use_container_width=True)

with tab2:
    # Porovnání ceny
    df_bar = pd.DataFrame({
        "Varianta": ["Reference", "Návrh ETICS"],
        "Cena Investice": [ref_Cena, navrh_Cena],
        "Cena Provozu (30 let)": [naklady_ref_rok*30, naklady_navrh_rok*30]
    })
    st.bar_chart(df_bar.set_index("Varianta"))

# -----------------------------------------------------------------------------
# 8. PATIČKA
# -----------------------------------------------------------------------------
st.markdown("---")
st.success("✅ Všechny výpočty proběhly úspěšně.")
st.caption("Aplikace vygenerována pomocí Streamlit v rámci BP.")