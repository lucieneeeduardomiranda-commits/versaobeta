# -*- coding: utf-8 -*-
import streamlit as st
import math
from scipy.stats import nbinom

# --- CONFIGURAÇÃO DE ESTILO ---
st.set_page_config(page_title="Scanner Pro v8.1 - Simplificado", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #0066cc; color: white; font-weight: bold; }
    .stAlert { border-radius: 10px; }
    h3 { padding-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE CÁLCULO ---

def get_temporal_factor(minuto, f_inicio, f_fim1, f_ini2, f_fim2):
    if minuto <= 35: return f_inicio
    elif 36 <= minuto <= 45: return f_fim1
    elif 46 <= minuto <= 80: return f_ini2
    else: return f_fim2

def get_scenario_factor(cenario):
    """Ajusta o volume de cantos esperado baseado no estado atual do jogo."""
    fatores = {
        "Jogo Equilibrado / Estável": 1.00,
        "Favorito Perdendo (Pressão Máxima)": 1.35,
        "Favorito Empatando (Pressão Alta)": 1.15,
        "Favorito Ganhando (Ritmo Lento)": 0.80,
        "Favorito Ganhando Bem (Controle)": 0.65
    }
    return fatores.get(cenario, 1.0)

def calcular_lambda_restante(minutos_jogados, lambda_partida, f1, f2, f3, f4):
    tempo_total = 95
    taxa_base = lambda_partida / tempo_total
    lambda_restante = 0.0
    for minuto in range(minutos_jogados + 1, tempo_total + 1):
        fator = get_temporal_factor(minuto, f1, f2, f3, f4)
        lambda_restante += taxa_base * fator
    return lambda_restante

def neg_binomial_prob(k_count, mu, dispersion_param):
    """Calcula a probabilidade usando Binomial Negativa com parâmetro de dispersão fixo em k=3.0"""
    if k_count < 0: return 0.0
    n = dispersion_param
    p = n / (n + mu) if (n + mu) != 0 else 0
    return float(nbinom.pmf(k_count, n, p))

def calcular_odd_minima_para_ev(probabilidade_ganho, probabilidade_perda, ev_alvo=0.05):
    if probabilidade_ganho <= 0: return None
    return ((ev_alvo + probabilidade_perda) / probabilidade_ganho) + 1

def calcular_kelly(prob_ganho, prob_perda, odd, fracionamento=0.5):
    if prob_ganho <= 0 or odd <= 1: return 0.0
    b = odd - 1
    f_kelly = (prob_ganho * b - prob_perda) / b
    return max(0, f_kelly * fracionamento)

# --- INTERFACE - BARRA LATERAL ---

with st.sidebar:
    st.header("🎮 Parâmetros de Jogo")
    minutos = st.slider("Minutos Jogados", 0, 95, 45)
    atuais = st.number_input("Escanteios Atuais", 0, 30, 5)
    
    st.divider()
    st.subheader("📊 Média da Liga")
    media_liga = st.number_input("Média de Escanteios da Liga", 5.0, 20.0, 10.0, 0.1)
    
    st.divider()
    st.subheader("🏟️ Cenário e Comportamento")
    
    cenario_jogo = st.selectbox(
        "Estado do Jogo (Game State)", 
        [
            "Jogo Equilibrado / Estável",
            "Favorito Perdendo (Pressão Máxima)", 
            "Favorito Empatando (Pressão Alta)",
            "Favorito Ganhando (Ritmo Lento)",
            "Favorito Ganhando Bem (Controle)"
        ], index=0
    )

    st.divider()
    st.subheader("🎯 Mercado e Odds")
    linha = st.number_input("Linha de Aposta (Over)", 0.5, 20.0, 10.5, 0.5)
    odd_o = st.number_input("Odd Over", 1.01, 10.0, 1.90)
    odd_u = st.number_input("Odd Under", 1.01, 10.0, 1.90)

    with st.expander("⚙️ Ajuste Fatores Temporais"):
        f1 = st.slider("0-35 min", 0.5, 1.5, 0.90)
        f2 = st.slider("36-45 min", 0.5, 1.5, 1.10)
        f3 = st.slider("46-80 min", 0.5, 1.5, 0.95)
        f4 = st.slider("81-95 min", 0.5, 1.5, 1.20)

    st.divider()
    st.subheader("💰 Gestão de Banca")
    banca_total = st.number_input("Saldo da Banca (R$)", 0.0, 1000000.0, 1000.0)
    agressividade = st.slider("Fator Kelly", 0.1, 1.0, 0.5, help="0.5 (Half Kelly) é o mais equilibrado.")

# --- CORPO PRINCIPAL ---

st.title("⚽ Analisador de Escanteios v8.1 (Simplificado)")

st.info(f"**Média da Liga:** {media_liga:.2f} escanteios | **Modelo:** Binomial Negativa (k=3.0)")

if st.button("CALCULAR ANÁLISE PROFISSIONAL"):
    # 1. Cálculo do Lambda Base pelo Tempo
    lambda_base = calcular_lambda_restante(minutos, media_liga, f1, f2, f3, f4)
    
    # 2. Aplicação do Fator de Cenário (Game State)
    f_cenario = get_scenario_factor(cenario_jogo)
    lambda_r = lambda_base * f_cenario
    
    # 3. Definição do Alvo
    target_over = math.floor(linha) + 1 - atuais
    
    # 4. Cálculo de Probabilidades (Binomial Negativa com k=3.0)
    k_fixed = 3.0  # Parâmetro de dispersão fixo para corrigir o viés
    is_half = (linha * 10) % 10 != 0
    if is_half:
        p_under = sum(neg_binomial_prob(k, lambda_r, k_fixed) for k in range(max(0, int(target_over))))
        p_over = 1.0 - p_under
        p_push = 0.0
    else:
        p_push = neg_binomial_prob(target_over, lambda_r, k_fixed)
        p_under = sum(neg_binomial_prob(k, lambda_r, k_fixed) for k in range(max(0, int(target_over))))
        p_over = 1.0 - p_push - p_under

    p_perda_over = 1.0 - p_over - p_push
    p_perda_under = 1.0 - p_under - p_push
    
    # 5. Cálculos de Valor (EV)
    ev_o = (p_over * (odd_o - 1)) - (p_perda_over * 1)
    ev_u = (p_under * (odd_u - 1)) - (p_perda_under * 1)

    # --- RESULTADOS VISUAIS ---
    st.divider()
    
    col_res1, col_res2 = st.columns([2, 1])
    
    with col_res1:
        st.subheader("📊 Probabilidades e Valor")
        p_col1, p_col2, p_col3 = st.columns(3)
        p_col1.metric("Probabilidade Over", f"{p_over:.1%}")
        p_col2.metric("Probabilidade Under", f"{p_under:.1%}")
        p_col3.metric("Probabilidade Push", f"{p_push:.1%}" if not is_half else "N/A")

        ev_col1, ev_col2 = st.columns(2)
        ev_col1.metric("EV Over", f"{ev_o:.3f}", delta=f"{(ev_o*100):.1f}%" if ev_o > 0 else None)
        ev_col2.metric("EV Under", f"{ev_u:.3f}", delta=f"{(ev_u*100):.1f}%" if ev_u > 0 else None)

    with col_res2:
        st.subheader("💰 Gestão de Stake")
        # Decisão de Kelly baseada no EV positivo
        if ev_o > 0.10:
            f_k = calcular_kelly(p_over, p_perda_over, odd_o, agressividade)
            st.success(f"**ENTRADA: OVER {linha}**")
            st.write(f"Stake Sugerida: **R$ {banca_total * f_k:.2f}**")
            st.caption(f"({f_k:.2%} da banca)")
        elif ev_u > 0.10:
            f_k = calcular_kelly(p_under, p_perda_under, odd_u, agressividade)
            st.info(f"**ENTRADA: UNDER {linha}**")
            st.write(f"Stake Sugerida: **R$ {banca_total * f_k:.2f}**")
            st.caption(f"({f_k:.2%} da banca)")
        else:
            st.error("**SEM ENTRADA**")
            st.write("EV abaixo do alvo de 0.05")

    # --- ODD MÍNIMA ---
    st.divider()
    st.subheader("💰 Odds Mínimas (Filtro de Valor)")
    odd_min_over = calcular_odd_minima_para_ev(p_over, p_perda_over, ev_alvo=0.10)
    odd_min_under = calcular_odd_minima_para_ev(p_under, p_perda_under, ev_alvo=0.10)
    
    col_odd1, col_odd2 = st.columns(2)
    with col_odd1:
        if odd_min_over:
            st.metric(f"Mínima Over {linha}", f"{odd_min_over:.2f}", f"Atual: {odd_o:.2f}")
    with col_odd2:
        if odd_min_under:
            st.metric(f"Mínima Under {linha}", f"{odd_min_under:.2f}", f"Atual: {odd_u:.2f}")

    # --- DETALHES TÉCNICOS ---
    with st.expander("🔍 Memória de Cálculo Professional"):
        st.write(f"**Lambda Base (Temporal):** {lambda_base:.2f}")
        st.write(f"**Lambda Ajustado (com Cenário):** {lambda_r:.2f}")
        st.write(f"**Impacto do Cenário:** {f_cenario:.2f}x no volume")
        st.write(f"**Parâmetro de Dispersão (k):** {k_fixed} (Fixo para corrigir viés)")
        st.markdown("""
        **Mudanças na v8.1:**
        1. **Simplificação:** Removida a Média Ponderada. Agora usa apenas a Média da Liga como input.
        2. **Correção do Viés:** Parâmetro de dispersão (k) fixado em **3.0** para corrigir o viés para Under.
        3. **Fórmula de Lambda:** Lambda Ajustado = (Média da Liga / 95 * Minutos Restantes * Fatores Temporais) * Fator de Cenário.
        4. **Probabilidade:** Calculada via Distribuição Binomial Negativa (k=3.0) para melhor distribuição.
        """)

