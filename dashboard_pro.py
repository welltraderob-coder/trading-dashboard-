import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from supabase import create_client, Client

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
    
    h1 {
        color: #E9D5FF;
        font-weight: 800;
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #7C3AED 0%, #9333EA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    h2, h3 {
        color: #DDD6FE;
        font-weight: 600;
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
        padding: 0.5rem 2rem;
    }
    
    .stButton>button:hover {
        background: linear-gradient(90deg, #6D28D9 0%, #7C3AED 100%);
        box-shadow: 0 0 20px rgba(124, 58, 237, 0.5);
    }
    
    hr {
        border-color: #7C3AED;
        opacity: 0.3;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# CONEXÃO SUPABASE
# ===============================
@st.cache_resource
def conectar_supabase():
    """Cria conexão com o Supabase"""
    try:
        supabase: Client = create_client(
            st.secrets["supabase"]["url"],
            st.secrets["supabase"]["key"]
        )
        return supabase
    except Exception as e:
        st.error(f"❌ Erro ao conectar no Supabase: {e}")
        return None

@st.cache_data(ttl=30)  # Cache de 30 segundos para dados em tempo real!
def carregar_dados(tabela):
    """Carrega dados de uma tabela do Supabase"""
    supabase = conectar_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table(tabela).select("*").execute()
        df = pd.DataFrame(response.data)
        
        if 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data'])
            df = df.rename(columns={'data': 'DATA'})
        
        return df
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
        df = df.sort_values('DATA')
        col_periodo = 'DATA'
    elif tipo_analise == "Mensal":
        col_periodo = 'mes_ano'
    else:
        df = df.sort_values('ano')
        col_periodo = 'ano'
    
    df['CAPITAL_ACUM'] = df[col_lucro].cumsum()
    df['PEAK'] = df['CAPITAL_ACUM'].expanding().max()
    df['DRAWDOWN'] = df['CAPITAL_ACUM'] - df['PEAK']
    
    lucros = df[df[col_lucro] > 0][col_lucro].sum()
    perdas = abs(df[df[col_lucro] < 0][col_lucro].sum())
    profit_factor = lucros / perdas if perdas > 0 else 0
    
    total_periodos = len(df)
    periodos_positivos = len(df[df[col_lucro] > 0])
    win_rate = (periodos_positivos / total_periodos * 100) if total_periodos > 0 else 0
    
    avg_win = df[df[col_lucro] > 0][col_lucro].mean() if len(df[df[col_lucro] > 0]) > 0 else 0
    avg_loss = abs(df[df[col_lucro] < 0][col_lucro].mean()) if len(df[df[col_lucro] < 0]) > 0 else 0
    
    expectativa = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)
    
    retornos = df[col_lucro]
    periodos_por_ano = 252 if tipo_analise == "Diário" else (12 if tipo_analise == "Mensal" else 1)
    sharpe = (retornos.mean() / retornos.std()) * np.sqrt(periodos_por_ano) if retornos.std() > 0 else 0
    
    drawdown_max = df['DRAWDOWN'].min()
    recovery_factor = abs(df['CAPITAL_ACUM'].iloc[-1] / drawdown_max) if drawdown_max < 0 else 0
    
    return {
        'drawdown_max': drawdown_max,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'win_rate': win_rate,
        'expectativa': expectativa,
        'sharpe': sharpe,
        'recovery_factor': recovery_factor,
        'capital_final': df['CAPITAL_ACUM'].iloc[-1] if len(df) > 0 else 0,
        'capital_max': df['CAPITAL_ACUM'].max() if len(df) > 0 else 0,
        'total_trades': df['total_trades'].sum(),
        'total_gains': df['gains'].sum(),
        'total_losses': df['losses'].sum(),
        'df_com_metricas': df,
        'col_lucro': col_lucro,
        'col_periodo': col_periodo
    }

# ===============================
# HEADER
# ===============================
st.markdown("""
<div style='text-align: center; padding: 2rem 0; background: linear-gradient(90deg, rgba(124, 58, 237, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%); border-radius: 10px; margin-bottom: 2rem;'>
    <h1 style='font-size: 3rem; margin: 0;'>📊 TRADING DASHBOARD PRO</h1>
    <p style='color: #C4B5FD; font-size: 1.2rem; margin-top: 0.5rem;'>☁️ Dados em Tempo Real - Supabase</p>
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

tabela_selecionada = mapa_tabelas[tipo_analise]

# Carrega dados
df = carregar_dados(tabela_selecionada)

if not df.empty:
    st.sidebar.success(f"✅ {len(df)} registros")
    st.sidebar.info("☁️ Conectado ao Supabase")
else:
    st.sidebar.error("❌ Sem dados")

# Botão atualizar
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"⏱️ Atualização automática a cada 30s")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ===============================
# DASHBOARD PRINCIPAL
# ===============================

if not df.empty:
    metricas = calcular_metricas(df, tipo_analise)
    
    if metricas:
        df_calc = metricas['df_com_metricas']
        
        # CARDS PRINCIPAIS
        st.markdown("### 💰 Performance Geral")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric(
                "Capital",
                f"R$ {metricas['capital_final']:,.2f}",
                delta=f"{metricas['capital_final']:+.2f}",
                delta_color="normal" if metricas['capital_final'] >= 0 else "inverse"
            )
        
        with col2:
            st.metric(
                "Profit Factor",
                f"{metricas['profit_factor']:.2f}",
                delta="Bom" if metricas['profit_factor'] > 1.5 else "Atenção",
                delta_color="normal" if metricas['profit_factor'] > 1.5 else "inverse"
            )
        
        with col3:
            st.metric(
                "Win Rate",
                f"{metricas['win_rate']:.1f}%",
                delta=f"{metricas['win_rate']:.1f}%"
            )
        
        with col4:
            st.metric(
                "Sharpe Ratio",
                f"{metricas['sharpe']:.2f}",
                delta="Ótimo" if metricas['sharpe'] > 1 else "Normal"
            )
        
        with col5:
            st.metric(
                "Drawdown Máx",
                f"R$ {metricas['drawdown_max']:.2f}",
                delta=f"{(metricas['drawdown_max']/metricas['capital_max']*100):.1f}%" if metricas['capital_max'] > 0 else "0%",
                delta_color="inverse"
            )
        
        with col6:
            st.metric(
                "Expectativa",
                f"R$ {metricas['expectativa']:.2f}",
                delta="Positiva" if metricas['expectativa'] > 0 else "Negativa",
                delta_color="normal" if metricas['expectativa'] > 0 else "inverse"
            )
        
        st.markdown("---")
        
        # GRÁFICO EQUITY CURVE
        st.markdown("### 📈 Equity Curve")
        
        fig_equity = go.Figure()
        
        fig_equity.add_trace(go.Scatter(
            x=df_calc[metricas['col_periodo']],
            y=df_calc['CAPITAL_ACUM'],
            fill='tozeroy',
            name='Capital',
            line=dict(color='#7C3AED', width=3),
            fillcolor='rgba(124, 58, 237, 0.1)'
        ))
        
        fig_equity.add_trace(go.Scatter(
            x=df_calc[metricas['col_periodo']],
            y=df_calc['PEAK'],
            name='Peak',
            line=dict(color='#10B981', width=2, dash='dash'),
            opacity=0.7
        ))
        
        fig_equity.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
        
        fig_equity.update_layout(
            title="Evolução do Capital",
            xaxis_title="Período",
            yaxis_title="Capital (R$)",
            hovermode='x unified',
            height=500,
            plot_bgcolor='rgba(15, 15, 35, 0.5)',
            paper_bgcolor='rgba(15, 15, 35, 0.5)',
            font=dict(color='#C4B5FD'),
            legend=dict(
                bgcolor='rgba(30, 27, 75, 0.8)',
                bordercolor='#7C3AED',
                borderwidth=1
            )
        )
        
        st.plotly_chart(fig_equity, use_container_width=True)
        
        st.markdown("---")
        
        # TABELA DETALHADA
        st.markdown("### 📋 Histórico Detalhado")
        
        st.dataframe(
            df_calc,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Download
        st.download_button(
            label="📥 Exportar Dados (CSV)",
            data=df_calc.to_csv(index=False).encode('utf-8'),
            file_name=f"trading_{tipo_analise.lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.warning(f"⚠️ Nenhum dado encontrado para o período {tipo_analise}.")
    st.info("💡 Aguarde o sincronizador enviar os dados para o Supabase.")

# RODAPÉ
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption(f"☁️ Fonte: Supabase")
with col_footer2:
    st.caption(f"📊 {len(df) if not df.empty else 0} registros")
with col_footer3:
    st.caption(f"💜 Dashboard Pro v3.0 - Tempo Real")
