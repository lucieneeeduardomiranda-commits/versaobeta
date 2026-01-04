# -*- coding: utf-8 -*-
import streamlit as st
import math
from scipy.stats import nbinom

# --- CONFIGURAÇÃO DE ESTILO ---
st.set_page_config(page_title="Scanner Pro v9.0 - Momentum Edition", page_icon="⚽", layout="wide")

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
    fatores = {
        "Jogo Equilibrado / Estável": 1.00,
        "Favorito Perdendo (Pressão Máxima)": 1.35,
        "Favorito Empatando (Pressão Alta)": 1.15,
        "Favorito Ganhando (Ritmo Lento)": 0.80,
        "Favorito Ganhando Bem (Controle)": 0.65
    }
    return fatores.get(cenario, 1.0)

def calcular_lambda_hibrido_restante(minutos_jogados, atuais, media_liga, f1, f2, f3, f4):
    """
    Calcula o Lambda restante combinando a Média da Liga com o Ritmo Real do jogo.
    """
    tempo_total = 95
    minutos_restantes = tempo_total - minutos_jogados
    
    if minutos_jogados > 0:
        # Ritmo Real: Quantos cantos por minuto ESTÃO saindo nesta partida
        ritmo_real_minuto = atuais / minutos_jogados
        # Ritmo Teórico: Quantos cantos por minuto a liga costuma ter
        ritmo_teorico_minuto = media_liga / tempo_total
        
        # PESO DINÂMICO: Quanto mais o jogo avança, mais o Ritmo Real importa.
        # Aos 60 min, o peso do que está acontecendo no campo é maior (63%) que a média da liga.
        peso_real = minutos_jogados / tempo_total
        taxa_base_hibrida = (ritmo_real_minuto * peso_real) + (ritmo_teorico_minuto * (1 - peso_real))
    else:
        taxa_base_hibrida = media_liga / tempo_total

    lambda_restante = 0.0
    for minuto in range(minutos_jogados + 1, tempo_total + 1):
        fator_t = get_temporal_factor(minuto, f1, f2, f3, f4)
        lambda_restante += taxa_base_hibrida * fator_t
        
    return lambda_restante, taxa_base_hibrida

def neg_binomial_prob(k_count, mu, dispersion_param):
    if k_count < 0: return 0.0
    n = dispersion_param
    p = n / (n + mu) if (n + mu) != 0 else 0
    return float(nbinom.pmf(k_count, n, p))

def calcular_odd_minima_para_ev(probabilidade_ganho, probabilidade_perda, ev_alvo=0.05):
    if probabilidade_ganho <= 0: return None
    return ((ev_alvo + probabilidade_perda) / probabilidade_ganho) + 1

def calcular_kelly(prob_ganho, prob_perda, odd, fracionamento=0.2):
    # Reduzi o fracionamento padrão para 0.2 (melhor para validação de método)
    if prob_ganho <= 0 or odd <= 1: return 0.0
    b = odd - 1
    f_kelly = (prob_ganho * b - prob_perda) / b
    return max(0, f_kelly * fracionamento)

# --- INTERFACE - BARRA LATERAL ---

with st.sidebar:
    st.header("🎮 Parâmetros de Jogo")
    minutos = st.slider("Minutos Jogados", 0, 95, 60)
    atuais = st.number_input("Escanteios Atuais", 0, 30, 6)
    
    st.divider()
    st.subheader("📊 Média da Liga")
    media_liga = st.number_input("Média de Escanteios da Liga", 5.0, 20.0, 10.0, 0.1)
    
    st.divider()
    st.subheader("🏟️ Cenário (Game State)")
    cenario_jogo = st.selectbox(
        "Estado do Jogo", 
        ["Jogo Equilibrado / Estável", "Favorito Perdendo (Pressão Máxima)", 
         "Favorito Empatando (Pressão Alta)", "Favorito Ganhando (Ritmo Lento)", "Favorito Ganhando Bem (Controle)"]
    )

    st.divider()
    st.subheader("🎯 Mercado e Odds")
    linha = st.number_input("Linha de Aposta (Over)", 0.5, 25.0, atuais + 2.5, 0.5)
    odd_o = st.number_input("Odd Over", 1.01, 10.0, 1.90)
    odd_u = st.number_input("Odd Under", 1.01, 10.0, 1.90)

    with st.expander("⚙️ Ajuste Fatores Temporais"):
        f1 = st.slider("0-35 min", 0.5, 1.5, 0.90)
        f2 = st.slider("36-45 min", 0.5, 1.5, 1.10)
        f3 = st.slider("46-80 min", 0.5, 1.5, 0.95)
        f4 = st.slider("81-95 min", 0.5, 1.5, 1.25) # Aumentado levemente para pressão final

    st.divider()
    st.subheader("💰 Gestão")
    banca_total = st.number_input("Saldo (R$)", 0.0, 1000000.0, 1000.0)
    agressividade = st.slider("Fator Kelly", 0.05, 0.5, 0.2, help="Recomendado 0.2 para validação.")

# --- CORPO PRINCIPAL ---

st.title("⚽ Scanner Pro v9.0 (Momentum Edition)")
st.info(f"**Análise Híbrida:** Cruzando Média da Liga ({media_liga}) com Ritmo Real do Jogo.")

if st.button("CALCULAR ANÁLISE COM MOMENTUM"):
    # 1. Cálculo do Lambda Híbrido (Liga + Real)
    lambda_base, taxa_hibrida = calcular_lambda_hibrido_restante(minutos, atuais, media_liga, f1, f2, f3, f4)
    
    # 2. Aplicação do Fator de Cenário
    f_cenario = get_scenario_factor(cenario_jogo)
    lambda_r = lambda_base * f_cenario
    
    # 3. Definição do Alvo
    target_over = math.floor(linha) + 1 - atuais
    
    # 4. Probabilidades (Binomial Negativa k=3.0)
    k_fixed = 3.0
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
    
    # 5. Valor (EV)
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
        p_col3.metric("Push (Reembolso)", f"{p_push:.1%}" if not is_half else "N/A")

        st.subheader("🎯 Valor Esperado (EV)")
        ev_col1, ev_col2 = st.columns(2)
        ev_col1.metric("EV Over", f"{ev_o:.3f}", delta=f"{(ev_o*100):.1f}%", delta_color="normal" if ev_o > 0 else "inverse")
        ev_col2.metric("EV Under", f"{ev_u:.3f}", delta=f"{(ev_u*100):.1f}%", delta_color="normal" if ev_u > 0 else "inverse")

    with col_res2:
        st.subheader("💰 Stake Sugerida")
        if ev_o > 0.05:
            f_k = calcular_kelly(p_over, p_perda_over, odd_o, agressividade)
            st.success(f"✅ **OVER {linha}**")
            st.write(f"Sugerido: **R$ {banca_total * f_k:.2f}**")
            st.caption(f"({f_k:.2%} da banca)")
        elif ev_u > 0.05:
            f_k = calcular_kelly(p_under, p_perda_under, odd_u, agressividade)
            st.info(f"✅ **UNDER {linha}**")
            st.write(f"Sugerido: **R$ {banca_total * f_k:.2f}**")
            st.caption(f"({f_k:.2%} da banca)")
        else:
            st.error("❌ **SEM ENTRADA**")
            st.write("Aguarde valor.")

    with st.expander("🔍 Memória de Cálculo (Momentum)"):
        ritmo_partida = (atuais/minutos)*95 if minutos > 0 else 0
        st.write(f"**Ritmo desta Partida:** {ritmo_partida:.2f} cantos/95min")
        st.write(f"**Média da Liga:** {media_liga:.2f} cantos/95min")
        st.write(f"**Taxa Base Híbrida (Peso Real):** {taxa_hibrida*95:.2f}")
        st.write(f"**Lambda Final Ajustado:** {lambda_r:.2f}")