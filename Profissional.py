# -*- coding: utf-8 -*-
import streamlit as st
import math
from scipy.stats import nbinom

# --- CONFIGURAÇÃO DE ESTILO ---
st.set_page_config(page_title="Scanner Pro v9.1 - Profissional", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #0066cc; color: white; font-weight: bold; }
    .stAlert { border-radius: 10px; }
    h3 { padding-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- DICIONÁRIO DE LIGAS (K e Médias Atualizadas) ---
LIGAS_DATA = {
    "🇮🇹 Série A (Itália)": {"k": 2.62, "media": 8.81},
    "🇵🇹 Primeira Liga (Portugal)": {"k": 2.51, "media": 9.10},
    "🇲🇽 México": {"k": 2.50, "media": 9.33},
    "🇨🇴 Colômbia": {"k": 2.50, "media": 8.62},
    "🇸🇦 Arábia Saudita": {"k": 2.50, "media": 10.08},
    "🇮🇹 Série B (Itália)": {"k": 2.10, "media": 9.55},
    "🇫🇷 Ligue 1 (França)": {"k": 1.82, "media": 9.24},
    "🇩🇪 Bundesliga": {"k": 1.62, "media": 9.63},
    "🇩🇪 2. Bundesliga": {"k": 1.35, "media": 10.15},
    "🇬🇧 Championship": {"k": 1.21, "media": 10.19},
    "🇹🇷 Super Lig (Turquia)": {"k": 1.14, "media": 9.47},
    "Outra / Personalizado": {"k": 2.00, "media": 10.00}
}

# --- FUNÇÕES DE CÁLCULO ---

def get_temporal_factor(minuto, f1, f2, f3, f4):
    if minuto <= 35: return f1
    elif 36 <= minuto <= 45: return f2
    elif 46 <= minuto <= 80: return f3
    else: return f4

def get_scenario_factor(cenario):
    fatores = {
        "Jogo Equilibrado / Estável": 1.00,
        "Favorito Perdendo (Pressão Máxima)": 1.35,
        "Favorito Empatando (Pressão Alta)": 1.15,
        "Favorito Ganhando (Ritmo Lento)": 0.80,
        "Favorito Ganhando Bem (Controle)": 0.65
    }
    return fatores.get(cenario, 1.0) [cite: 4]

def calcular_lambda_hibrido_restante(minutos_jogados, atuais, media_liga, f1, f2, f3, f4):
    tempo_total = 95
    if minutos_jogados > 0:
        ritmo_real_minuto = atuais / minutos_jogados
        ritmo_teorico_minuto = media_liga / tempo_total
        peso_real = minutos_jogados / tempo_total
        taxa_base_hibrida = (ritmo_real_minuto * peso_real) + (ritmo_teorico_minuto * (1 - peso_real))
    else:
        taxa_base_hibrida = media_liga / tempo_total

    lambda_restante = 0.0
    for minuto in range(minutos_jogados + 1, tempo_total + 1):
        fator_t = get_temporal_factor(minuto, f1, f2, f3, f4)
        lambda_restante += taxa_base_hibrida * fator_t
    return lambda_restante, taxa_base_hibrida [cite: 5]

def neg_binomial_prob(k_count, mu, dispersion_param):
    if k_count < 0: return 0.0
    n = dispersion_param
    p = n / (n + mu) if (n + mu) != 0 else 0
    return float(nbinom.pmf(k_count, n, p)) [cite: 6]

def calcular_odd_minima_para_ev(probabilidade_ganho, probabilidade_perda, ev_alvo=0.10):
    if probabilidade_ganho <= 0: return None
    return ((ev_alvo + probabilidade_perda) / probabilidade_ganho) + 1 [cite: 6]

def calcular_kelly(prob_ganho, prob_perda, odd, fracionamento=0.5):
    if prob_ganho <= 0 or odd <= 1: return 0.0
    b = odd - 1
    f_kelly = (prob_ganho * b - prob_perda) / b
    return max(0, f_kelly * fracionamento) [cite: 6]

# --- INTERFACE - BARRA LATERAL ---

with st.sidebar:
    st.header("🎮 Parâmetros de Jogo")
    
    liga_selecionada = st.selectbox("Selecione a Liga", list(LIGAS_DATA.keys()))
    dados_liga = LIGAS_DATA[liga_selecionada]
    
    k_ajustado = st.slider("Ajuste de Dispersão (K)", 0.5, 4.0, dados_liga["k"], 0.01) [cite: 7]
    
    st.divider()
    minutos = st.slider("Minutos Jogados", 0, 95, 60)
    atuais = st.number_input("Escanteios Atuais", 0, 30, 6)
    
    st.divider()
    st.subheader("📊 Média da Liga")
    media_liga = st.number_input("Média de Escanteios da Liga", 5.0, 20.0, dados_liga["media"], 0.01) [cite: 8]
    
    st.divider()
    st.subheader("🏟️ Cenário (Game State)")
    cenario_jogo = st.selectbox(
        "Estado do Jogo", 
        ["Jogo Equilibrado / Estável", "Favorito Perdendo (Pressão Máxima)", 
         "Favorito Empatando (Pressão Alta)", "Favorito Ganhando (Ritmo Lento)", "Favorito Ganhando Bem (Controle)"]
    ) [cite: 8]

    st.divider()
    st.subheader("🎯 Mercado e Odds")
    linha = st.number_input("Linha de Aposta (Over)", 0.5, 25.0, atuais + 2.5, 0.5) [cite: 9]
    odd_o = st.number_input("Odd Over", 1.01, 10.0, 1.90)
    odd_u = st.number_input("Odd Under", 1.01, 10.0, 1.90)

    with st.expander("⚙️ Ajuste Fatores Temporais"):
        f1 = st.slider("0-35 min", 0.5, 2.0, 0.90)
        f2 = st.slider("36-45 min", 0.5, 2.0, 1.10)
        f3 = st.slider("46-80 min", 0.5, 2.0, 1.25)
        f4 = st.slider("81-95 min", 0.5, 2.0, 1.45) [cite: 9]

    st.divider()
    st.subheader("💰 Gestão")
    banca_total = st.number_input("Saldo (R$)", 0.0, 1000000.0, 1000.0)
    agressividade = st.slider("Fator Kelly", 0.1, 1.0, 0.5) [cite: 10]

# --- CORPO PRINCIPAL ---

st.title(f"⚽ Scanner Pro v9.1 - {liga_selecionada}")

if st.button("CALCULAR ANÁLISE COM MOMENTUM"):
    lambda_base, taxa_hibrida = calcular_lambda_hibrido_restante(minutos, atuais, media_liga, f1, f2, f3, f4)
    f_cenario = get_scenario_factor(cenario_jogo)
    lambda_r = lambda_base * f_cenario
    target_over = math.floor(linha) + 1 - atuais
    
    k_fixed = k_ajustado 
    is_half = (linha * 10) % 10 != 0
    
    if is_half:
        p_under = sum(neg_binomial_prob(k, lambda_r, k_fixed) for k in range(max(0, int(target_over))))
        p_over = 1.0 - p_under
        p_push = 0.0
    else:
        p_push = neg_binomial_prob(target_over, lambda_r, k_fixed)
        p_under = sum(neg_binomial_prob(k, lambda_r, k_fixed) for k in range(max(0, int(target_over))))
        p_over = 1.0 - p_push - p_under [cite: 11, 12]

    p_perda_over = 1.0 - p_over - p_push
    p_perda_under = 1.0 - p_under - p_push
    ev_o = (p_over * (odd_o - 1)) - (p_perda_over * 1)
    ev_u = (p_under * (odd_u - 1)) - (p_perda_under * 1)

    # --- RESULTADOS ---
    st.divider()
    col_res1, col_res2 = st.columns([2, 1])
    
    with col_res1:
        st.subheader("📊 Probabilidades")
        p_col1, p_col2, p_col3 = st.columns(3)
        p_col1.metric("Over", f"{p_over:.1%}")
        p_col2.metric("Under", f"{p_under:.1%}")
        p_col3.metric("Push", f"{p_push:.1%}" if not is_half else "N/A") [cite: 13]

        st.subheader("🎯 Valor Esperado (EV)")
        ev_col1, ev_col2 = st.columns(2)
        ev_col1.metric("EV Over", f"{ev_o:.3f}", delta=f"{(ev_o*100):.1f}%" if 0.10 <= ev_o < 0.40 else None)
        ev_col2.metric("EV Under", f"{ev_u:.3f}", delta=f"{(ev_u*100):.1f}%" if 0.10 <= ev_u < 0.40 else None) [cite: 14]

    with col_res2:
        st.subheader("💰 Stake Sugerida")
        limite_bloqueio = 0.40
        
        if 0.10 <= ev_o < limite_bloqueio:
            f_k = calcular_kelly(p_over, p_perda_over, odd_o, agressividade)
            st.success(f"✅ **OVER {linha}**")
            st.write(f"Stake: **R$ {banca_total * f_k:.2f}**")
            st.caption(f"({f_k:.2%} da banca)")
        elif 0.10 <= ev_u < limite_bloqueio:
            f_k = calcular_kelly(p_under, p_perda_under, odd_u, agressividade)
            st.info(f"✅ **UNDER {linha}**")
            st.write(f"Stake: **R$ {banca_total * f_k:.2f}**")
            st.caption(f"({f_k:.2%} da banca)")
        elif ev_o >= limite_bloqueio or ev_u >= limite_bloqueio:
            st.warning("⚠️ **EV ATÍPICO**")
            st.write(f"Entrada bloqueada: EV superior a {limite_bloqueio:.2f}.") [cite: 15, 16]
        else:
            st.error("❌ **SEM ENTRADA**")
            st.warning("EV abaixo do alvo de +0.10.")

    # --- BLOCO ODDS MÍNIMAS ---
    st.divider()
    st.subheader("💰 Odds Mínimas para EV +0.10")
    odd_min_over = calcular_odd_minima_para_ev(p_over, p_perda_over, ev_alvo=0.10)
    odd_min_under = calcular_odd_minima_para_ev(p_under, p_perda_under, ev_alvo=0.10)
    
    col_odd1, col_odd2 = st.columns(2)
    with col_odd1:
        if odd_min_over: st.metric(f"Mínima Over {linha}", f"{odd_min_over:.2f}", f"Atual: {odd_o:.2f}")
    with col_odd2:
        if odd_min_under: st.metric(f"Mínima Under {linha}", f"{odd_min_under:.2f}", f"Atual: {odd_u:.2f}") [cite: 16, 17]

    # --- MEMÓRIA DE CÁLCULO ---
    with st.expander("🔍 Memória de Cálculo (Momentum & MLE)"):
        st.write(f"**Liga Selecionada:** {liga_selecionada}")
        st.write(f"**K de Dispersão Utilizado:** {k_fixed}")
        st.write(f"**Média Base da Liga:** {media_liga}")
        ritmo_partida = (atuais/minutos)*95 if minutos > 0 else 0
        st.write(f"**Ritmo desta Partida:** {ritmo_partida:.2f} cantos/95min")
        st.write(f"**Lambda Final Ajustado:** {lambda_r:.2f}") [cite: 17, 18]