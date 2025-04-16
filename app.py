import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np
from player_analysis import display_player_page
from rankings import display_rankings_page
import tracemalloc
import warnings
import asyncio

# Inicializar tracemalloc
tracemalloc.start()

# Configurar para ignorar avisos específicos do asyncio
warnings.filterwarnings("ignore", category=RuntimeWarning, message="coroutine.*never awaited")

# Configuração da página
st.set_page_config(
    page_title="BLK Tennis Insights",
    page_icon="🎾",
    layout="wide"
)

# Conexão com o banco de dados
@st.cache_data
def load_data():
    with st.spinner('Carregando dados do banco...'):
        conn = sqlite3.connect('challonge-scraper/database/database.sqlite')
        matches = pd.read_sql_query("SELECT * FROM matches", conn)
        players = pd.read_sql_query("SELECT * FROM players", conn)
        tournaments = pd.read_sql_query("SELECT * FROM tournaments", conn)
        conn.close()
        
        # Debug: Imprimir colunas das tabelas
        print("\nColunas em matches:", matches.columns.tolist())
        print("\nColunas em tournaments:", tournaments.columns.tolist())
        print("\nColunas em players:", players.columns.tolist())
        
        # Adiciona a data do torneio às partidas
        if 'start_date' in tournaments.columns:
            matches = matches.merge(
                tournaments[['id', 'start_date']],
                left_on='tournament_id',
                right_on='id',
                suffixes=('', '_tournament')
            )
            matches = matches.rename(columns={'start_date': 'tournament_date'})
        elif 'created_at' in tournaments.columns:
            matches = matches.merge(
                tournaments[['id', 'created_at']],
                left_on='tournament_id',
                right_on='id',
                suffixes=('', '_tournament')
            )
            matches = matches.rename(columns={'created_at': 'tournament_date'})
        
        return matches, players, tournaments

# Carregar dados
matches, players, tournaments = load_data()

# Debug temporário
print("Colunas disponíveis em matches:", matches.columns.tolist())

# Título principal
st.title("🎾 BLK Tennis Insights")

# Sidebar para navegação
st.sidebar.title("Navegação")
page = st.sidebar.selectbox(
    "Selecione a página:",
    ["Análise de Jogadores", "Rankings"]
)

# Exibir página selecionada
if page == "Análise de Jogadores":
    display_player_page(matches, players)
elif page == "Rankings":
    display_rankings_page(matches, players, tournaments) 