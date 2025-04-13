import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np
from player_analysis import display_player_page
from rankings import display_rankings_page
from insights import display_insights_page

# Configuração da página
st.set_page_config(
    page_title="BLK Tennis Insights",
    page_icon="🎾",
    layout="wide"
)

# Conexão com o banco de dados
@st.cache_data
def load_data():
    conn = sqlite3.connect('database.sqlite')
    matches = pd.read_sql_query("SELECT * FROM matches", conn)
    players = pd.read_sql_query("SELECT * FROM players", conn)
    tournaments = pd.read_sql_query("SELECT * FROM tournaments", conn)
    conn.close()
    return matches, players, tournaments

# Carregar dados
matches, players, tournaments = load_data()

# Debug: Imprimir colunas disponíveis
print("Colunas disponíveis em matches:", matches.columns.tolist())
print("Colunas disponíveis em tournaments:", tournaments.columns.tolist())

# Título principal
st.title("🎾 BLK Tennis Insights")

# Sidebar para navegação
st.sidebar.title("Navegação")
page = st.sidebar.radio(
    "Selecione uma página:",
    ["Visão Geral", "Jogadores", "Rankings", "Insights"]
)

if page == "Visão Geral":
    st.header("Visão Geral do Sistema")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Estatísticas Gerais")
        total_jogadores = len(players)
        total_torneios = len(tournaments)
        total_jogos = len(matches)
        
        st.metric("Total de Jogadores", total_jogadores)
        st.metric("Total de Torneios", total_torneios)
        st.metric("Total de Jogos", total_jogos)
    
    with col2:
        st.subheader("Distribuição por Categoria")
        categoria_counts = tournaments['category'].value_counts()
        fig = px.pie(values=categoria_counts.values, names=categoria_counts.index, title="Distribuição de Torneios por Categoria")
        st.plotly_chart(fig)

elif page == "Jogadores":
    display_player_page(matches, players)

elif page == "Rankings":
    display_rankings_page(matches, players, tournaments)

elif page == "Insights":
    display_insights_page(matches, players, tournaments) 