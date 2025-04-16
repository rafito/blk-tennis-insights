import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np
from player_analysis import display_player_page
from rankings import display_rankings_page
from admin import display_admin_page
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

# Função para obter query parameters e host
def get_query_params():
    """Obtém os query parameters da URL e o host"""
    query_params = st.query_params
    
    # Em produção, usa o domínio correto
    host = 'https://blk-tennis-insights.streamlit.app'
    
    return {
        'player_id': query_params.get('player_id', None),
        'page': query_params.get('page', 'Análise de Jogadores'),
        'host': host
    }

@st.cache_data
def load_data():
    with st.spinner('Carregando dados do banco...'):
        # Tenta diferentes caminhos possíveis para o banco de dados
        db_paths = [
            'database.sqlite',
            'challonge-scraper/database/database.sqlite',
            '/app/database.sqlite'  # Caminho no Streamlit Cloud
        ]
        
        conn = None
        for path in db_paths:
            try:
                conn = sqlite3.connect(path)
                break
            except sqlite3.OperationalError:
                continue
        
        if conn is None:
            st.error("Não foi possível conectar ao banco de dados. Verifique se o arquivo database.sqlite está no local correto.")
            return None, None, None
            
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

# Obter query parameters
params = get_query_params()

# Navegação no topo com ícones
page = st.selectbox(
    "📍 Navegação:",
    ["👤 Análise de Jogadores", "🏆 Rankings", "🔐 Administração"],
    index=0 if params['page'] == 'Análise de Jogadores' else 1 if params['page'] == 'Rankings' else 2,
    format_func=lambda x: x.split(" ", 1)[1]  # Remove o emoji do display
)

# Atualizar query parameters quando a página mudar
st.query_params['page'] = page.split(" ", 1)[1]  # Remove o emoji
if params['player_id']:
    st.query_params['player_id'] = params['player_id']

# Exibir página selecionada
if "Análise de Jogadores" in page:
    # Armazenar o host na session_state
    st.session_state['host'] = params['host']
    display_player_page(matches, players, shared_player_id=params['player_id'])
elif "Rankings" in page:
    display_rankings_page(matches, players, tournaments)
elif "Administração" in page:
    display_admin_page(matches, players, tournaments) 