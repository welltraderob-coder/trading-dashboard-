import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import numpy as np
from datetime import datetime, timedelta

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
# CSS CUSTOMIZADO - TEMA ROXO PROFISSIONAL
# ===============================
st.markdown("""
<style>
    /* Tema roxo escuro profissional */
    .stApp {
        background: linear-gradient(135deg, #0F0F23 0%, #1E1B4B 100%);
    }
    
    /* Cards de métricas */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #A78BFA;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        color: #C4B5FD;
        font-weight: 500;
    }
    
    /* Títulos */
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
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E1B4B 0%, #0F0F23 100%);
    }
    
    /* Botões */
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
    
    /* Dividers */
    hr {
        border-color: #7C3AED;
        opacity: 0.3;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #C4B5FD;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        color: #A78BFA;
        border-bottom-color: #7C3AED;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# FUNÇÕES DE CONEXÃO E LEITURA
# ===============================
@st.cache_resource
def conectar_banco():
    """Cria conexão com o banco de dados"""
    return sqlite3.connect('trading.db', check_same_thread=False)

@st.cache_data(ttl=60)
def carregar_dados(tabela):
    """Carrega dados de uma tabela específica"""
    conn = conectar_banco()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    
    if 'DATA' in df.columns:
        df['DATA'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y')
    
    return df

# ===============================
# FUNÇÕES DE CÁLCULO DE MÉTRICAS
# ===============================
def calcular_metricas_adaptadas(df, tipo_analise):
    """Calcula métricas adaptadas para cada tipo de período"""
    
    # Define coluna de lucro baseado no tipo
    col_lucro = 'LUCRO LIQUIDO' if 'LUCRO LIQUIDO' in df.columns else 'LUCRO LÍQUIDO'
    
    # Ordena dados
    if tipo_analise == "Diário" and 'DATA' in df.columns:
        df = df.sort_values('DATA')
        col_periodo = 'DATA'
    elif tipo_analise == "Mensal":
        col_periodo = 'MÊS/ANO'
    else:  # Anual
        df = df.sort_values('ANO')
        col_periodo = 'ANO'
    
    # Capital acumulado
    df['CAPITAL_ACUM'] = df[col_lucro].cumsum()
    
    # Drawdown
    df['PEAK'] = df['CAPITAL_ACUM'].expanding().max()
    df['DRAWDOWN'] = df['CAPITAL_ACUM'] - df['PEAK']
    drawdown_max = df['DRAWDOWN'].min()
    drawdown_atual = df['DRAWDOWN'].iloc[-1] if len(df) > 0 else 0
    
    # Profit Factor
    lucros = df[df[col_lucro] > 0][col_lucro].sum()
    perdas = abs(df[df[col_lucro] < 0][col_lucro].sum())
    profit_factor = lucros / perdas if perdas > 0 else 0
    
    # Win Rate
    total_periodos = len(df)
    periodos_positivos = len(df[df[col_lucro] > 0])
    win_rate = (periodos_positivos / total_periodos * 100) if total_periodos > 0 else 0
    
    # Médias
    avg_win = df[df[col_lucro] > 0][col_lucro].mean() if len(df[df[col_lucro] > 0]) > 0 else 0
    avg_loss = abs(df[df[col_lucro] < 0][col_lucro].mean()) if len(df[df[col_lucro] < 0]) > 0 else 0
    
    # Expectativa
    expectativa = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)
    
    # Sharpe Ratio
    retornos = df[col_lucro]
    periodos_por_ano = 252 if tipo_analise == "Diário" else (12 if tipo_analise == "Mensal" else 1)
    sharpe = (retornos.mean() / retornos.std()) * np.sqrt(periodos_por_ano) if retornos.std() > 0 else 0
    
    # Recovery Factor
    recovery_factor = abs(df['CAPITAL_ACUM'].iloc[-1] / drawdown_max) if drawdown_max < 0 else 0
    
    # Total de trades
    total_trades = df['TOTAL TRADES'].sum()
    total_gains = df['GAINS'].sum()
    total_losses = df['LOSSES'].sum()
    
    return {
        'drawdown_max': drawdown_max,
        'drawdown_atual': drawdown_atual,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'win_rate': win_rate,
        'expectativa': expectativa,
        'sharpe': sharpe,
        'recovery_factor': recovery_factor,
        'capital_final': df['CAPITAL_ACUM'].iloc[-1] if len(df) > 0 else 0,
        'capital_max': df['CAPITAL_ACUM'].max() if len(df) > 0 else 0,
        'total_trades': total_trades,
        'total_gains': total_gains,
        'total_losses': total_losses,
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
    <p style='color: #C4B5FD; font-size: 1.2rem; margin-top: 0.5rem;'>Análise Profissional de Performance</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# SIDEBAR
# ===============================
st.sidebar.markdown("### ⚙️ Configurações")

# Seleção do tipo de análise
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

st.sidebar.success(f"✅ {len(df)} registros")

# Filtros
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtros")

df_filtrado = df.copy()

if tipo_analise == "Diário" and 'DATA' in df.columns:
    data_min = df['DATA'].min().date()
    data_max = df['DATA'].max().date()
    
    col1, col2 = st.sidebar.columns(2)
    data_inicio = col1.date_input("De:", data_min, min_value=data_min, max_value=data_max)
    data_fim = col2.date_input("Até:", data_max, min_value=data_min, max_value=data_max)
    
    df_filtrado = df_filtrado[
        (df_filtrado['DATA'].dt.date >= data_inicio) & 
        (df_filtrado['DATA'].dt.date <= data_fim)
    ]

elif tipo_analise == "Mensal" and 'MÊS/ANO' in df.columns:
    meses_disponiveis = sorted(df['MÊS/ANO'].unique(), reverse=True)
    meses_selecionados = st.sidebar.multiselect(
        "Selecione os Meses:",
        options=meses_disponiveis,
        default=meses_disponiveis
    )
    if meses_selecionados:
        df_filtrado = df_filtrado[df_filtrado['MÊS/ANO'].isin(meses_selecionados)]

elif tipo_analise == "Anual" and 'ANO' in df.columns:
    anos_disponiveis = sorted(df['ANO'].unique(), reverse=True)
    anos_selecionados = st.sidebar.multiselect(
        "Selecione os Anos:",
        options=anos_disponiveis,
        default=anos_disponiveis
    )
    if anos_selecionados:
        df_filtrado = df_filtrado[df_filtrado['ANO'].isin(anos_selecionados)]

# Botão atualizar
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Info
st.sidebar.markdown("---")
st.sidebar.caption(f"⏱️ Última atualização")
st.sidebar.caption(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ===============================
# DASHBOARD PRINCIPAL
# ===============================

if not df_filtrado.empty:
    
    # Calcula métricas
    metricas = calcular_metricas_adaptadas(df_filtrado, tipo_analise)
    df_calc = metricas['df_com_metricas']
    
    # ===============================
    # SEÇÃO 1: CARDS PRINCIPAIS
    # ===============================
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
    
    # ===============================
    # SEÇÃO 2: MÉTRICAS DETALHADAS
    # ===============================
    st.markdown("### 📈 Análise Detalhada")
    
    col_a, col_b, col_c, col_d = st.columns(4)
    
    with col_a:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #7C3AED;'>
            <p style='color: #C4B5FD; margin: 0; font-size: 0.9rem;'>Média Períodos Positivos</p>
            <p style='color: #22C55E; margin: 0; font-size: 1.5rem; font-weight: 700;'>R$ {metricas['avg_win']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_b:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #EF4444;'>
            <p style='color: #C4B5FD; margin: 0; font-size: 0.9rem;'>Média Períodos Negativos</p>
            <p style='color: #EF4444; margin: 0; font-size: 1.5rem; font-weight: 700;'>R$ {metricas['avg_loss']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_c:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #10B981;'>
            <p style='color: #C4B5FD; margin: 0; font-size: 0.9rem;'>Total Trades</p>
            <p style='color: #10B981; margin: 0; font-size: 1.5rem; font-weight: 700;'>{int(metricas['total_trades'])}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_d:
        risk_reward = (metricas['avg_win'] / metricas['avg_loss']) if metricas['avg_loss'] > 0 else 0
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #F59E0B;'>
            <p style='color: #C4B5FD; margin: 0; font-size: 0.9rem;'>Risk/Reward Ratio</p>
            <p style='color: #F59E0B; margin: 0; font-size: 1.5rem; font-weight: 700;'>{risk_reward:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===============================
    # SEÇÃO 3: GRÁFICOS
    # ===============================
    st.markdown("### 📊 Visualizações")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Equity Curve", "📊 Distribuição", "🎯 Performance", "📋 Indicadores"])
    
    with tab1:
        # Equity Curve profissional
        fig_equity = go.Figure()
        
        # Área de lucro
        fig_equity.add_trace(go.Scatter(
            x=df_calc[metricas['col_periodo']],
            y=df_calc['CAPITAL_ACUM'],
            fill='tozeroy',
            name='Capital',
            line=dict(color='#7C3AED', width=3),
            fillcolor='rgba(124, 58, 237, 0.1)'
        ))
        
        # Linha de Peak
        fig_equity.add_trace(go.Scatter(
            x=df_calc[metricas['col_periodo']],
            y=df_calc['PEAK'],
            name='Peak',
            line=dict(color='#10B981', width=2, dash='dash'),
            opacity=0.7
        ))
        
        # Linha zero
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
    
    with tab2:
        # Distribuição de resultados
        fig_dist = go.Figure()
        
        # Histogram
        fig_dist.add_trace(go.Histogram(
            x=df_filtrado[metricas['col_lucro']],
            nbinsx=20,
            marker=dict(
                color='#7C3AED',
                line=dict(color='#9333EA', width=1)
            ),
            name='Distribuição'
        ))
        
        fig_dist.update_layout(
            title="Distribuição de Resultados",
            xaxis_title="Lucro/Prejuízo (R$)",
            yaxis_title="Frequência",
            height=400,
            plot_bgcolor='rgba(15, 15, 35, 0.5)',
            paper_bgcolor='rgba(15, 15, 35, 0.5)',
            font=dict(color='#C4B5FD')
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with tab3:
        # Gráfico de performance
        col_perf1, col_perf2 = st.columns(2)
        
        with col_perf1:
            # Pizza: Gains vs Losses
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Gains', 'Losses'],
                values=[metricas['total_gains'], metricas['total_losses']],
                marker=dict(colors=['#10B981', '#EF4444']),
                hole=0.5,
                textfont=dict(size=16, color='white')
            )])
            
            fig_pie.update_layout(
                title="Gains vs Losses",
                height=350,
                paper_bgcolor='rgba(15, 15, 35, 0.5)',
                font=dict(color='#C4B5FD'),
                showlegend=True
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_perf2:
            # Gráfico de barras por período
            fig_bar = go.Figure(data=[go.Bar(
                x=df_calc[metricas['col_periodo']],
                y=df_calc[metricas['col_lucro']],
                marker=dict(
                    color=df_calc[metricas['col_lucro']],
                    colorscale=[[0, '#EF4444'], [0.5, '#7C3AED'], [1, '#10B981']],
                ),
            )])
            
            fig_bar.update_layout(
                title=f"Resultado por {tipo_analise[:-1] if tipo_analise != 'Mensal' else 'Mês'}",
                xaxis_title="Período",
                yaxis_title="Resultado (R$)",
                height=350,
                plot_bgcolor='rgba(15, 15, 35, 0.5)',
                paper_bgcolor='rgba(15, 15, 35, 0.5)',
                font=dict(color='#C4B5FD'),
                showlegend=False
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab4:
        # Indicadores de qualidade
        col_ind1, col_ind2 = st.columns(2)
        
        with col_ind1:
            st.markdown(f"""
            <div style='background: rgba(124, 58, 237, 0.1); padding: 2rem; border-radius: 10px;'>
                <h4 style='color: #DDD6FE; margin-top: 0;'>🎯 Indicadores de Qualidade</h4>
                
                <div style='margin: 1rem 0;'>
                    <p style='color: #C4B5FD; margin: 0.5rem 0;'>Recovery Factor</p>
                    <div style='background: rgba(30, 27, 75, 0.5); border-radius: 5px; height: 30px; position: relative;'>
                        <div style='background: linear-gradient(90deg, #7C3AED, #10B981); height: 100%; 
                                    width: {min(metricas['recovery_factor'] * 20, 100)}%; border-radius: 5px;'></div>
                        <p style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                                  margin: 0; color: white; font-weight: 700;'>{metricas['recovery_factor']:.2f}</p>
                    </div>
                </div>
                
                <div style='margin: 1rem 0;'>
                    <p style='color: #C4B5FD; margin: 0.5rem 0;'>Win Rate</p>
                    <div style='background: rgba(30, 27, 75, 0.5); border-radius: 5px; height: 30px; position: relative;'>
                        <div style='background: linear-gradient(90deg, #7C3AED, #10B981); height: 100%; 
                                    width: {metricas['win_rate']}%; border-radius: 5px;'></div>
                        <p style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                                  margin: 0; color: white; font-weight: 700;'>{metricas['win_rate']:.1f}%</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_ind2:
            # Resumo numérico
            st.markdown(f"""
            <div style='background: rgba(124, 58, 237, 0.1); padding: 2rem; border-radius: 10px;'>
                <h4 style='color: #DDD6FE; margin-top: 0;'>📊 Resumo Estatístico</h4>
                
                <div style='margin: 1rem 0; display: flex; justify-content: space-between;'>
                    <span style='color: #C4B5FD;'>Total Períodos:</span>
                    <span style='color: #A78BFA; font-weight: 700;'>{len(df_filtrado)}</span>
                </div>
                
                <div style='margin: 1rem 0; display: flex; justify-content: space-between;'>
                    <span style='color: #C4B5FD;'>Períodos Positivos:</span>
                    <span style='color: #10B981; font-weight: 700;'>{len(df_filtrado[df_filtrado[metricas['col_lucro']] > 0])}</span>
                </div>
                
                <div style='margin: 1rem 0; display: flex; justify-content: space-between;'>
                    <span style='color: #C4B5FD;'>Períodos Negativos:</span>
                    <span style='color: #EF4444; font-weight: 700;'>{len(df_filtrado[df_filtrado[metricas['col_lucro']] < 0])}</span>
                </div>
                
                <div style='margin: 1rem 0; display: flex; justify-content: space-between;'>
                    <span style='color: #C4B5FD;'>Melhor Período:</span>
                    <span style='color: #10B981; font-weight: 700;'>R$ {df_filtrado[metricas['col_lucro']].max():.2f}</span>
                </div>
                
                <div style='margin: 1rem 0; display: flex; justify-content: space-between;'>
                    <span style='color: #C4B5FD;'>Pior Período:</span>
                    <span style='color: #EF4444; font-weight: 700;'>R$ {df_filtrado[metricas['col_lucro']].min():.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===============================
    # SEÇÃO 4: TABELA DETALHADA
    # ===============================
    st.markdown("### 📋 Histórico Detalhado")
    
    col_tab1, col_tab2 = st.columns([3, 1])
    with col_tab2:
        filtro_tipo = st.selectbox(
            "Filtrar por:",
            ["Todos", "Apenas Positivos", "Apenas Negativos"]
        )
    
    df_tabela = df_filtrado.copy()
    
    if filtro_tipo == "Apenas Positivos":
        df_tabela = df_tabela[df_tabela[metricas['col_lucro']] > 0]
    elif filtro_tipo == "Apenas Negativos":
        df_tabela = df_tabela[df_tabela[metricas['col_lucro']] < 0]
    
    # Ordena pela coluna de período
    if tipo_analise == "Diário":
        df_tabela = df_tabela.sort_values('DATA', ascending=False)
    elif tipo_analise == "Anual":
        df_tabela = df_tabela.sort_values('ANO', ascending=False)
    
    st.dataframe(
        df_tabela,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Download
    st.download_button(
        label="📥 Exportar Dados (CSV)",
        data=df_tabela.to_csv(index=False).encode('utf-8'),
        file_name=f"trading_{tipo_analise.lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

else:
    st.warning(f"⚠️ Nenhum dado encontrado para o período {tipo_analise} selecionado.")

# ===============================
# RODAPÉ
# ===============================
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption(f"📂 Fonte: {tabela_selecionada}")
with col_footer2:
    st.caption(f"📊 {len(df_filtrado)} registros analisados")
with col_footer3:
    st.caption(f"💜 Dashboard Pro v2.1")
