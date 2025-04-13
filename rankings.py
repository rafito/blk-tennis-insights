import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from glicko import GlickoSystem

def calculate_glicko_ratings(matches, players, tournaments, category=None, time_period=None):
    """Calcula ratings Glicko-2 para os jogadores"""
    # Filtrar partidas por categoria e período se especificado
    filtered_matches = matches.copy()
    
    # Converter a coluna started_month_year para datetime
    filtered_matches['started_month_year'] = pd.to_datetime(filtered_matches['started_month_year'])
    
    if category != "Todas":
        tournament_ids = tournaments[tournaments['category'] == category]['id'].tolist()
        filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
    
    if time_period:
        # Converter o período para datetime se for string
        if isinstance(time_period, str):
            time_period = pd.to_datetime(time_period)
        filtered_matches = filtered_matches[filtered_matches['started_month_year'] >= time_period]
    
    # Inicializar sistema Glicko-2
    glicko_system = GlickoSystem()
    
    # Processar partidas em ordem cronológica
    filtered_matches = filtered_matches.sort_values('started_month_year')
    
    for _, match in filtered_matches.iterrows():
        glicko_system.update_match(match['winner_id'], match['loser_id'])
    
    # Converter ratings para DataFrame
    ratings_df = pd.DataFrame([
        {
            'player_id': player_id,
            'rating': rating,
            'rd': rd,
            'vol': vol
        }
        for player_id in players['id']
        for rating, rd, vol in [glicko_system.get_rating(player_id)]
    ])
    
    # Adicionar nomes dos jogadores
    ratings_df = ratings_df.merge(players[['id', 'name']], left_on='player_id', right_on='id')
    ratings_df = ratings_df.sort_values('rating', ascending=False)
    
    return ratings_df

def calculate_points_ranking(matches, players, tournaments, category=None, time_period=None):
    """Calcula ranking baseado em pontos por vitória"""
    # Filtrar partidas por categoria e período se especificado
    filtered_matches = matches.copy()
    
    # Converter a coluna started_month_year para datetime
    filtered_matches['started_month_year'] = pd.to_datetime(filtered_matches['started_month_year'])
    
    if category != "Todas":
        tournament_ids = tournaments[tournaments['category'] == category]['id'].tolist()
        filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
    
    if time_period:
        # Converter o período para datetime se for string
        if isinstance(time_period, str):
            time_period = pd.to_datetime(time_period)
        filtered_matches = filtered_matches[filtered_matches['started_month_year'] >= time_period]
    
    # Pontos por rodada
    points_map = {
        4: 1000,  # Final
        3: 650,   # Semifinal
        2: 400,   # Quartas
        1: 200    # Primeira rodada
    }
    
    # Calcular pontos para cada jogador
    player_points = {}
    for player_id in players['id']:
        player_matches = filtered_matches[filtered_matches['winner_id'] == player_id]
        total_points = sum(points_map.get(round, 0) for round in player_matches['round'])
        player_points[player_id] = total_points
    
    # Converter para DataFrame
    points_df = pd.DataFrame([
        {'player_id': player_id, 'points': points}
        for player_id, points in player_points.items()
    ])
    
    # Adicionar nomes dos jogadores
    points_df = points_df.merge(players[['id', 'name']], left_on='player_id', right_on='id')
    points_df = points_df.sort_values('points', ascending=False)
    
    return points_df

def display_rankings_page(matches, players, tournaments):
    """Exibe a página de rankings"""
    st.header("Rankings")
    
    # Seleção de categoria e período
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox(
            "Selecione a categoria:",
            ["Todas"] + sorted(tournaments['category'].unique().tolist())
        )
    with col2:
        time_period = st.selectbox(
            "Período:",
            ["Todo o histórico", "Últimos 12 meses", "Últimos 24 meses"]
        )
    
    # Converter período para data se necessário
    if time_period == "Últimos 12 meses":
        time_period = pd.Timestamp.now() - pd.DateOffset(months=12)
    elif time_period == "Últimos 24 meses":
        time_period = pd.Timestamp.now() - pd.DateOffset(months=24)
    else:
        time_period = None
    
    # Calcular rankings
    glicko_ratings = calculate_glicko_ratings(
        matches, players, tournaments,
        category=None if category == "Todas" else category,
        time_period=time_period
    )
    
    points_ranking = calculate_points_ranking(
        matches, players, tournaments,
        category=None if category == "Todas" else category,
        time_period=time_period
    )
    
    # Exibir rankings
    tab1, tab2 = st.tabs(["Ranking Glicko-2", "Ranking por Pontos"])
    
    with tab1:
        st.subheader("Ranking Glicko-2")
        st.dataframe(
            glicko_ratings[['name', 'rating', 'rd']].rename(columns={
                'name': 'Jogador',
                'rating': 'Rating',
                'rd': 'Desvio Padrão'
            }).round(2),
            hide_index=True
        )
        
        # Gráfico de evolução do rating
        st.subheader("Top 5 Jogadores - Rating Glicko-2")
        top_5 = glicko_ratings.head(5)
        fig = px.bar(top_5, x='name', y='rating',
                     labels={'name': 'Jogador', 'rating': 'Rating'},
                     title="Top 5 Jogadores por Rating Glicko-2")
        st.plotly_chart(fig)
    
    with tab2:
        st.subheader("Ranking por Pontos")
        st.dataframe(
            points_ranking[['name', 'points']].rename(columns={
                'name': 'Jogador',
                'points': 'Pontos'
            }),
            hide_index=True
        )
        
        # Gráfico de pontos
        st.subheader("Top 5 Jogadores - Pontos")
        top_5_points = points_ranking.head(5)
        fig = px.bar(top_5_points, x='name', y='points',
                     labels={'name': 'Jogador', 'points': 'Pontos'},
                     title="Top 5 Jogadores por Pontos")
        st.plotly_chart(fig) 