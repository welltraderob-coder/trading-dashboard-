import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="Trading Dashboard Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# CSS CUSTOMIZADO - TEMA ROXO
# ===============================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0F0F23 0%, #1E1B4B 100%);
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #A78BFA;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #C4B5FD;
        font-weight: 500;
    }
    h1, h2, h3 {
        color: #DDD6FE;
        font-weight: 700;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E1B4B 0%, #0F0F23 100%);
    }
    .stButton>button {
        background: linear-gradient(90deg, #7C3AED 0%, #9333EA 100%);
        color: white;
        border: none;
        font-weight: 600;
        border-radius: 8px;
    }
    hr { border-color: #7C3AED; opacity: 0.3; }
</style>
""", unsafe_allow_html=True)

# ===============================
# CONEXÃO SUPABASE VIA REQUESTS
# ===============================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

@st.cache_data(ttl=30)
def carregar_dados(tabela):
    """Carrega dados do Supabase usando requests"""
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/{tabela}?select=*",
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            dados = response.json()
            if dados:
                return pd.DataFrame(dados)
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Erro ao carregar {tabela}: {e}")
        return pd.DataFrame()

# ===============================
# FUNÇÕES DE CÁLCULO
# ===============================
def calcular_metricas(df, tipo_analise):
    """Calcula métricas baseado no tipo de análise"""
    if df.empty:
        return None

    col_lucro = 'lucro_liquido'

    if tipo_analise == "Diário":
        df['data'] = pd.to_datetime(df['data'])
        df = df.sort_values('data')
        col_periodo = 'data'
    elif tipo_analise == "Mensal":
        col_periodo = 'mes_ano'
    else:
        df = df.sort_values('ano')
        col_periodo = 'ano'

    df = df.copy()
    df['CAPITAL_ACUM'] = df[col_lucro].cumsum()
    df['PEAK'] = df['CAPITAL_ACUM'].expanding().max()
    df['DRAWDOWN'] = df['CAPITAL_ACUM'] - df['PEAK']

    lucros = df[df[col_lucro] > 0][col_lucro].sum()
    perdas = abs(df[df[col_lucro] < 0][col_lucro].sum())
    profit_factor = lucros / perdas if perdas > 0 else 0

    total = len(df)
    positivos = len(df[df[col_lucro] > 0])
    win_rate = (positivos / total * 100) if total > 0 else 0

    avg_win = df[df[col_lucro] > 0][col_lucro].mean() if positivos > 0 else 0
    avg_loss = abs(df[df[col_lucro] < 0][col_lucro].mean()) if (total - positivos) > 0 else 0
    expectativa = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)

    retornos = df[col_lucro]
    fator = 252 if tipo_analise == "Diário" else (12 if tipo_analise == "Mensal" else 1)
    sharpe = (retornos.mean() / retornos.std()) * np.sqrt(fator) if retornos.std() > 0 else 0

    drawdown_max = df['DRAWDOWN'].min()
    recovery = abs(df['CAPITAL_ACUM'].iloc[-1] / drawdown_max) if drawdown_max < 0 else 0

    return {
        'drawdown_max': drawdown_max,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'win_rate': win_rate,
        'expectativa': expectativa,
        'sharpe': sharpe,
        'recovery_factor': recovery,
        'capital_final': df['CAPITAL_ACUM'].iloc[-1],
        'capital_max': df['CAPITAL_ACUM'].max(),
        'total_trades': df['total_trades'].sum() if 'total_trades' in df.columns else 0,
        'total_gains': df['gains'].sum() if 'gains' in df.columns else 0,
        'total_losses': df['losses'].sum() if 'losses' in df.columns else 0,
        'df': df,
        'col_lucro': col_lucro,
        'col_periodo': col_periodo
    }

# ===============================
# HEADER
# ===============================
st.markdown("""
<div style='text-align:center; padding:2rem; background:linear-gradient(90deg,rgba(124,58,237,0.1),rgba(147,51,234,0.1)); border-radius:10px; margin-bottom:2rem;'>
    <h1 style='font-size:3rem; margin:0; background:linear-gradient(90deg,#7C3AED,#9333EA); -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
        📊 TRADING DASHBOARD PRO
    </h1>
    <p style='color:#C4B5FD; font-size:1.2rem; margin-top:0.5rem;'>☁️ Dados em Tempo Real</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# SIDEBAR
# ===============================
st.sidebar.markdown("### ⚙️ Configurações")

tipo_analise = st.sidebar.selectbox(
    "📊 Período de Análise",
    ["Diário", "Mensal", "Anual"],
    index=0
)

mapa_tabelas = {
    "Diário": "resumo_diario",
    "Mensal": "resumo_mensal",
    "Anual": "resumo_anual"
}

tabela = mapa_tabelas[tipo_analise]
df = carregar_dados(tabela)

if not df.empty:
    st.sidebar.success(f"✅ {len(df)} registros")
    st.sidebar.info("☁️ Supabase conectado")
else:
    st.sidebar.error("❌ Sem dados")

# Filtros
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtros")

df_filtrado = df.copy()

if tipo_analise == "Diário" and not df.empty and 'data' in df.columns:
    df['data'] = pd.to_datetime(df['data'])
    data_min = df['data'].min().date()
    data_max = df['data'].max().date()
    col1, col2 = st.sidebar.columns(2)
    data_ini = col1.date_input("De:", data_min, min_value=data_min, max_value=data_max)
    data_fim = col2.date_input("Até:", data_max, min_value=data_min, max_value=data_max)
    df_filtrado = df[(df['data'].dt.date >= data_ini) & (df['data'].dt.date <= data_fim)]

elif tipo_analise == "Mensal" and not df.empty and 'mes_ano' in df.columns:
    meses = sorted(df['mes_ano'].unique(), reverse=True)
    selecionados = st.sidebar.multiselect("Meses:", meses, default=meses)
    if selecionados:
        df_filtrado = df[df['mes_ano'].isin(selecionados)]

elif tipo_analise == "Anual" and not df.empty and 'ano' in df.columns:
    anos = sorted(df['ano'].unique(), reverse=True)
    selecionados = st.sidebar.multiselect("Anos:", anos, default=anos)
    if selecionados:
        df_filtrado = df[df['ano'].isin(selecionados)]

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"⏱️ Auto-atualiza a cada 30s")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ===============================
# DASHBOARD PRINCIPAL
# ===============================
if not df_filtrado.empty:
    metricas = calcular_metricas(df_filtrado, tipo_analise)

    if metricas:
        df_calc = metricas['df']

        # CARDS PRINCIPAIS
        st.markdown("### 💰 Performance Geral")
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.metric("Capital", f"R$ {metricas['capital_final']:,.2f}",
                delta=f"{metricas['capital_final']:+.2f}",
                delta_color="normal" if metricas['capital_final'] >= 0 else "inverse")
        with col2:
            st.metric("Profit Factor", f"{metricas['profit_factor']:.2f}",
                delta="Bom" if metricas['profit_factor'] > 1.5 else "Atenção",
                delta_color="normal" if metricas['profit_factor'] > 1.5 else "inverse")
        with col3:
            st.metric("Win Rate", f"{metricas['win_rate']:.1f}%", delta=f"{metricas['win_rate']:.1f}%")
        with col4:
            st.metric("Sharpe Ratio", f"{metricas['sharpe']:.2f}",
                delta="Ótimo" if metricas['sharpe'] > 1 else "Normal")
        with col5:
            st.metric("Drawdown Máx", f"R$ {metricas['drawdown_max']:.2f}",
                delta=f"{(metricas['drawdown_max']/metricas['capital_max']*100):.1f}%" if metricas['capital_max'] > 0 else "0%",
                delta_color="inverse")
        with col6:
            st.metric("Expectativa", f"R$ {metricas['expectativa']:.2f}",
                delta="Positiva" if metricas['expectativa'] > 0 else "Negativa",
                delta_color="normal" if metricas['expectativa'] > 0 else "inverse")

        st.markdown("---")

        # CARDS DETALHADOS
        st.markdown("### 📈 Análise Detalhada")
        ca, cb, cc, cd = st.columns(4)

        with ca:
            st.markdown(f"""<div style='background:rgba(124,58,237,0.2);padding:1rem;border-radius:10px;border-left:4px solid #7C3AED;'>
                <p style='color:#C4B5FD;margin:0;font-size:0.9rem;'>Média Positivos</p>
                <p style='color:#22C55E;margin:0;font-size:1.5rem;font-weight:700;'>R$ {metricas['avg_win']:.2f}</p>
            </div>""", unsafe_allow_html=True)
        with cb:
            st.markdown(f"""<div style='background:rgba(124,58,237,0.2);padding:1rem;border-radius:10px;border-left:4px solid #EF4444;'>
                <p style='color:#C4B5FD;margin:0;font-size:0.9rem;'>Média Negativos</p>
                <p style='color:#EF4444;margin:0;font-size:1.5rem;font-weight:700;'>R$ {metricas['avg_loss']:.2f}</p>
            </div>""", unsafe_allow_html=True)
        with cc:
            st.markdown(f"""<div style='background:rgba(124,58,237,0.2);padding:1rem;border-radius:10px;border-left:4px solid #10B981;'>
                <p style='color:#C4B5FD;margin:0;font-size:0.9rem;'>Total Trades</p>
                <p style='color:#10B981;margin:0;font-size:1.5rem;font-weight:700;'>{int(metricas['total_trades'])}</p>
            </div>""", unsafe_allow_html=True)
        with cd:
            rr = (metricas['avg_win']/metricas['avg_loss']) if metricas['avg_loss'] > 0 else 0
            st.markdown(f"""<div style='background:rgba(124,58,237,0.2);padding:1rem;border-radius:10px;border-left:4px solid #F59E0B;'>
                <p style='color:#C4B5FD;margin:0;font-size:0.9rem;'>Risk/Reward</p>
                <p style='color:#F59E0B;margin:0;font-size:1.5rem;font-weight:700;'>{rr:.2f}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # GRÁFICOS
        st.markdown("### 📊 Visualizações")
        tab1, tab2, tab3 = st.tabs(["📈 Equity Curve", "📊 Barras", "🎯 Distribuição"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_calc[metricas['col_periodo']], y=df_calc['CAPITAL_ACUM'],
                fill='tozeroy', name='Capital',
                line=dict(color='#7C3AED', width=3),
                fillcolor='rgba(124,58,237,0.1)'
            ))
            fig.add_trace(go.Scatter(
                x=df_calc[metricas['col_periodo']], y=df_calc['PEAK'],
                name='Peak', line=dict(color='#10B981', width=2, dash='dash'), opacity=0.7
            ))
            fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
            fig.update_layout(
                title="Evolução do Capital", height=500,
                plot_bgcolor='rgba(15,15,35,0.5)', paper_bgcolor='rgba(15,15,35,0.5)',
                font=dict(color='#C4B5FD'), hovermode='x unified',
                legend=dict(bgcolor='rgba(30,27,75,0.8)', bordercolor='#7C3AED', borderwidth=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = go.Figure(data=[go.Bar(
                x=df_calc[metricas['col_periodo']], y=df_calc[metricas['col_lucro']],
                marker=dict(
                    color=df_calc[metricas['col_lucro']],
                    colorscale=[[0,'#EF4444'],[0.5,'#7C3AED'],[1,'#10B981']]
                )
            )])
            fig2.update_layout(
                title="Resultado por Período", height=400,
                plot_bgcolor='rgba(15,15,35,0.5)', paper_bgcolor='rgba(15,15,35,0.5)',
                font=dict(color='#C4B5FD'), showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            fig3 = go.Figure(data=[go.Histogram(
                x=df_filtrado[metricas['col_lucro']], nbinsx=20,
                marker=dict(color='#7C3AED', line=dict(color='#9333EA', width=1))
            )])
            fig3.update_layout(
                title="Distribuição de Resultados", height=400,
                plot_bgcolor='rgba(15,15,35,0.5)', paper_bgcolor='rgba(15,15,35,0.5)',
                font=dict(color='#C4B5FD')
            )
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")

        # TABELA
        st.markdown("### 📋 Histórico Detalhado")
        col_t, col_f = st.columns([3, 1])
        with col_f:
            filtro = st.selectbox("Filtrar:", ["Todos", "Apenas Positivos", "Apenas Negativos"])

        df_tab = df_filtrado.copy()
        if filtro == "Apenas Positivos":
            df_tab = df_tab[df_tab[metricas['col_lucro']] > 0]
        elif filtro == "Apenas Negativos":
            df_tab = df_tab[df_tab[metricas['col_lucro']] < 0]

        st.dataframe(df_tab, use_container_width=True, hide_index=True, height=400)

        st.download_button(
            label="📥 Exportar CSV",
            data=df_tab.to_csv(index=False).encode('utf-8'),
            file_name=f"trading_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.warning("⚠️ Nenhum dado encontrado.")
    st.info("💡 Verifique se o sincronizador está rodando no seu PC.")

# RODAPÉ
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.caption(f"☁️ Fonte: Supabase")
c2.caption(f"📊 {len(df_filtrado) if not df_filtrado.empty else 0} registros")
c3.caption(f"💜 Dashboard Pro v3.0")
