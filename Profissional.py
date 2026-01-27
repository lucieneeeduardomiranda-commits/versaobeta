# -*- coding: utf-8 -*-
import streamlit as st
import math
from scipy.stats import nbinom

# --- CONFIGURAÇÃO DE ESTILO ---
[cite_start]st.set_page_config(page_title="Scanner Pro v9.1 - Otimizado (EV > 0.10)", page_icon="⚽", layout="wide") [cite: 1]

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #0066cc; color: white; font-weight: bold; }
    .stAlert { border-radius: 10px; }
    h3 { padding-top: 10px; }
    </style>
    [cite_start]""", unsafe_allow_html=True) [cite: 1]

# --- DICIONÁRIO DE LIGAS CALIBRADAS (MLE) ---
LIGAS_K_MLE = {
    [cite_start]"🇪🇸 La Liga 2 (Espanha)": 2.78, [cite: 2]
    [cite_start]"🇮🇹 Série A (Itália)": 2.62, [cite: 2]
    [cite_start]"🇵🇹 Primeira Liga (Portugal)": 2.51, [cite: 2]
    [cite_start]"🇪🇸 La Liga (Espanha)": 2.45, [cite: 2]
    [cite_start]"🇮🇹 Série B (Itália)": 2.10, [cite: 2]
    [cite_start]"🇳🇱 Eredivisie (Holanda)": 1.94, [cite: 2]
    [cite_start]"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia": 1.85, [cite: 2]
    [cite_start]"🇫🇷 Ligue 1 (França)": 1.82, [cite: 2]
    [cite_start]"🇩🇪 Bundesliga": 1.62, [cite: 2]
    [cite_start]"🇧🇪 Pro League (Bélgica)": 1.58, [cite: 2]
    [cite_start]"🇩🇪 2. Bundesliga": 1.35, [cite: 2]
    [cite_start]"🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": 1.32, [cite: 2]
    [cite_start]"🇬🇧 Championship": 1.21, [cite: 2]
    [cite_start]"🇹🇷 Super Lig (Turquia)": 1.14, [cite: 2]
    [cite_start]"Outra / Personalizado": 2.00 [cite: 3]
}

# --- FUNÇÕES DE CÁLCULO ---

def get_temporal_factor(minuto, f_inicio, f_fim1, f_ini2, f_fim2):
    [cite_start]if minuto <= 35: return f_inicio [cite: 3]
    [cite_start]elif 36 <= minuto <= 45: return f_fim1 [cite: 3]
    [cite_start]elif 46 <= minuto <= 80: return f_ini2 [cite: 3]
    [cite_start]else: return f_fim2 [cite: 3]

def get_scenario_factor(cenario):
    fatores = {
        [cite_start]"Jogo Equilibrado / Estável": 1.00, [cite: 3]
        [cite_start]"Favorito Perdendo (Pressão Máxima)": 1.35, [cite: 3]
        [cite_start]"Favorito Empatando (Pressão Alta)": 1.15, [cite: 3]
        [cite_start]"Favorito Ganhando (Ritmo Lento)": 0.80, [cite: 4]
        [cite_start]"Favorito Ganhando Bem (Controle)": 0.65 [cite: 4]
    }
    [cite_start]return fatores.get(cenario, 1.0) [cite: 4]

def calcular_lambda_hibrido_restante(minutos_jogados, atuais, media_liga, f1, f2, f3, f4):
    [cite_start]tempo_total = 95 [cite: 4]
    if minutos_jogados > 0:
        [cite_start]ritmo_real_minuto = atuais / minutos_jogados [cite: 4]
        [cite_start]ritmo_teorico_minuto = media_liga / tempo_total [cite: 4]
        [cite_start]peso_real = minutos_jogados / tempo_total [cite: 4]
        [cite_start]taxa_base_hibrida = (ritmo_real_minuto * peso_real) + (ritmo_teorico_minuto * (1 - peso_real)) [cite: 4, 5]
    else:
        [cite_start]taxa_base_hibrida = media_liga / tempo_total [cite: 5]

    [cite_start]lambda_restante = 0.0 [cite: 5]
    for minuto in range(minutos_jogados + 1, tempo_total + 1):
        [cite_start]fator_t = get_temporal_factor(minuto, f1, f2, f3, f4) [cite: 5]
        [cite_start]lambda_restante += taxa_base_hibrida * fator_t [cite: 5]
    [cite_start]return lambda_restante, taxa_base_hibrida [cite: 5]

def neg_binomial_prob(k_count, mu, dispersion_param):
    [cite_start]if k_count < 0: return 0.0 [cite: 5]
    [cite_start]n = dispersion_param [cite: 5]
    [cite_start]p = n / (n + mu) if (n + mu) != 0 else 0 [cite: 5, 6]
    [cite_start]return float(nbinom.pmf(k_count, n, p)) [cite: 6]

def calcular_odd_minima_para_ev(probabilidade_ganho, probabilidade_perda, ev_alvo=0.10):
    [cite_start]if probabilidade_ganho <= 0: return None [cite: 6]
    [cite_start]return ((ev_alvo + probabilidade_perda) / probabilidade_ganho) + 1 [cite: 6]

def calcular_kelly(prob_ganho, prob_perda, odd, fracionamento=0.5):
    [cite_start]if prob_ganho <= 0 or odd <= 1: return 0.0 [cite: 6]
    [cite_start]b = odd - 1 [cite: 6]
    [cite_start]f_kelly = (prob_ganho * b - prob_perda) / b [cite: 6]
    [cite_start]return max(0, f_kelly * fracionamento) [cite: 6]

# --- INTERFACE - BARRA LATERAL ---

with st.sidebar:
    [cite_start]st.header("🎮 Parâmetros de Jogo") [cite: 7]
    
    [cite_start]liga_selecionada = st.selectbox("Selecione a Liga", list(LIGAS_K_MLE.keys())) [cite: 7]
    [cite_start]k_sugerido = LIGAS_K_MLE[liga_selecionada] [cite: 7]
    [cite_start]k_ajustado = st.slider("Ajuste de Dispersão (K)", 0.5, 4.0, k_sugerido, 0.01) [cite: 7]
    
    st.divider()
    [cite_start]minutos = st.slider("Minutos Jogados", 0, 95, 60) [cite: 7]
    [cite_start]atuais = st.number_input("Escanteios Atuais", 0, 30, 6) [cite: 7]
    
    st.divider()
    [cite_start]st.subheader("📊 Média da Liga") [cite: 8]
    [cite_start]media_liga = st.number_input("Média de Escanteios da Liga", 5.0, 20.0, 10.0, 0.1) [cite: 8]
    
    st.divider()
    [cite_start]st.subheader("🏟️ Cenário (Game State)") [cite: 8]
    cenario_jogo = st.selectbox(
        "Estado do Jogo", 
        ["Jogo Equilibrado / Estável", "Favorito Perdendo (Pressão Máxima)", 
         "Favorito Empatando (Pressão Alta)", "Favorito Ganhando (Ritmo Lento)", "Favorito Ganhando Bem (Controle)"]
    [cite_start]) [cite: 8]

    st.divider()
    [cite_start]st.subheader("🎯 Mercado e Odds") [cite: 8, 9]
    [cite_start]linha = st.number_input("Linha de Aposta (Over)", 0.5, 25.0, atuais + 2.5, 0.5) [cite: 9]
    [cite_start]odd_o = st.number_input("Odd Over", 1.01, 10.0, 1.90) [cite: 9]
    [cite_start]odd_u = st.number_input("Odd Under", 1.01, 10.0, 1.90) [cite: 9]

    with st.expander("⚙️ Ajuste Fatores Temporais"):
        [cite_start]f1 = st.slider("0-35 min", 0.5, 1.5, 0.90) [cite: 9]
        [cite_start]f2 = st.slider("36-45 min", 0.5, 1.5, 1.10) [cite: 9]
        [cite_start]f3 = st.slider("46-80 min", 0.5, 1.5, 0.95) [cite: 9]
        [cite_start]f4 = st.slider("81-95 min", 0.5, 1.5, 1.25) [cite: 9]

    st.divider()
    [cite_start]st.subheader("💰 Gestão") [cite: 10]
    [cite_start]banca_total = st.number_input("Saldo (R$)", 0.0, 1000000.0, 1000.0) [cite: 10]
    [cite_start]agressividade = st.slider("Fator Kelly", 0.1, 1.0, 0.5) [cite: 10]

# --- CORPO PRINCIPAL ---

[cite_start]st.title(f"⚽ Scanner Pro v9.1 - {liga_selecionada}") [cite: 10]

[cite_start]if st.button("CALCULAR ANÁLISE COM MOMENTUM"): [cite: 10]
    [cite_start]lambda_base, taxa_hibrida = calcular_lambda_hibrido_restante(minutos, atuais, media_liga, f1, f2, f3, f4) [cite: 10]
    [cite_start]f_cenario = get_scenario_factor(cenario_jogo) [cite: 10]
    [cite_start]lambda_r = lambda_base * f_cenario [cite: 10]
    [cite_start]k_fixed = k_ajustado [cite: 11]
    
    [cite_start]is_half = (linha * 10) % 10 != 0 [cite: 11]
    
    if is_half:
        # MANTIDO: Lógica original para linhas quebradas (.5)
        [cite_start]target_over = math.floor(linha) + 1 - atuais [cite: 10]
        [cite_start]p_under = sum(neg_binomial_prob(k, lambda_r, k_fixed) for k in range(max(0, int(target_over)))) [cite: 11, 12]
        [cite_start]p_over = 1.0 - p_under [cite: 11]
        [cite_start]p_push = 0.0 [cite: 11]
    else:
        # CORRIGIDO: Lógica para linhas inteiras (Asiáticas)
        distancia_linha = int(linha - atuais)
        if distancia_linha < 0:
            p_over = 1.0
            p_under = 0.0
            p_push = 0.0
        else:
            p_push = neg_binomial_prob(distancia_linha, lambda_r, k_fixed)
            p_under = sum(neg_binomial_prob(k, lambda_r, k_fixed) for k in range(distancia_linha))
            p_over = 1.0 - p_push - p_under

    # Probabilidades de perda recalibradas para refletir o PUSH corretamente
    [cite_start]p_perda_over = 1.0 - p_over - p_push [cite: 12]
    [cite_start]p_perda_under = 1.0 - p_under - p_push [cite: 12]
    
    [cite_start]ev_o = (p_over * (odd_o - 1)) - (p_perda_over * 1) [cite: 12]
    [cite_start]ev_u = (p_under * (odd_u - 1)) - (p_perda_under * 1) [cite: 12]

    # --- RESULTADOS ---
    [cite_start]st.divider() [cite: 12]
    [cite_start]col_res1, col_res2 = st.columns([2, 1]) [cite: 12]
    
    with col_res1:
        [cite_start]st.subheader("📊 Probabilidades") [cite: 12, 13]
        [cite_start]p_col1, p_col2, p_col3 = st.columns(3) [cite: 13]
        [cite_start]p_col1.metric("Over", f"{p_over:.1%}") [cite: 13]
        [cite_start]p_col2.metric("Under", f"{p_under:.1%}") [cite: 13]
        [cite_start]p_col3.metric("Push", f"{p_push:.1%}" if not is_half else "N/A") [cite: 13]

        [cite_start]st.subheader("🎯 Valor Esperado (EV)") [cite: 13]
        [cite_start]ev_col1, ev_col2 = st.columns(2) [cite: 13]
        [cite_start]ev_col1.metric("EV Over", f"{ev_o:.3f}", delta=f"{(ev_o*100):.1f}%" if ev_o >= 0.10 else None) [cite: 13, 14]
        [cite_start]ev_col2.metric("EV Under", f"{ev_u:.3f}", delta=f"{(ev_u*100):.1f}%" if ev_u >= 0.10 else None) [cite: 13, 14]

    with col_res2:
        [cite_start]st.subheader("💰 Stake Sugerida") [cite: 14]
        
        [cite_start]if ev_o >= 0.10: [cite: 14]
            [cite_start]f_k = calcular_kelly(p_over, p_perda_over, odd_o, agressividade) [cite: 14]
            [cite_start]st.success(f"✅ **OVER {linha}**") [cite: 14]
            [cite_start]st.write(f"Stake: **R$ {banca_total * f_k:.2f}**") [cite: 14]
            [cite_start]st.caption(f"({f_k:.2%} da banca)") [cite: 14]
        [cite_start]elif ev_u >= 0.10: [cite: 15]
            [cite_start]f_k = calcular_kelly(p_under, p_perda_under, odd_u, agressividade) [cite: 15]
            [cite_start]st.info(f"✅ **UNDER {linha}**") [cite: 15]
            [cite_start]st.write(f"Stake: **R$ {banca_total * f_k:.2f}**") [cite: 15]
            [cite_start]st.caption(f"({f_k:.2%} da banca)") [cite: 15]
        else:
            [cite_start]st.error("❌ **SEM ENTRADA**") [cite: 15]
            [cite_start]st.warning("O valor esperado (EV) está abaixo do alvo de +0.10 (10%).") [cite: 16]

    # --- BLOCO ODDS MÍNIMAS ---
    [cite_start]st.divider() [cite: 16]
    [cite_start]st.subheader("💰 Odds Mínimas para EV +0.10") [cite: 16]
    [cite_start]odd_min_over = calcular_odd_minima_para_ev(p_over, p_perda_over, ev_alvo=0.10) [cite: 16]
    [cite_start]odd_min_under = calcular_odd_minima_para_ev(p_under, p_perda_under, ev_alvo=0.10) [cite: 16]
    
    [cite_start]col_odd1, col_odd2 = st.columns(2) [cite: 16]
    with col_odd1:
        if odd_min_over:
            [cite_start]st.metric(f"Mínima Over {linha}", f"{odd_min_over:.2f}", f"Atual: {odd_o:.2f}") [cite: 16]
    with col_odd2:
        if odd_min_under:
            [cite_start]st.metric(f"Mínima Under {linha}", f"{odd_min_under:.2f}", f"Atual: {odd_u:.2f}") [cite: 17]

    # --- MEMÓRIA DE CÁLCULO ---
    with st.expander("🔍 Memória de Cálculo (Momentum & MLE)"):
        [cite_start]st.write(f"**Liga Selecionada:** {liga_selecionada}") [cite: 17]
        [cite_start]st.write(f"**K de Dispersão Utilizado:** {k_fixed}") [cite: 17]
        [cite_start]ritmo_partida = (atuais/minutos)*95 if minutos > 0 else 0 [cite: 17]
        [cite_start]st.write(f"**Ritmo desta Partida:** {ritmo_partida:.2f} cantos/95min") [cite: 17]
        [cite_start]st.write(f"**Taxa Base Híbrida (Peso Real):** {taxa_hibrida*95:.2f}") [cite: 18]
        [cite_start]st.write(f"**Lambda Final Ajustado:** {lambda_r:.2f}") [cite: 18]