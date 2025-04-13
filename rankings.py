import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from glicko import GlickoSystem

@st.cache_data
def calculate_glicko_ratings(matches, players, tournaments, category=None, time_period=None):
    """Calcula ratings Glicko-2 para os jogadores"""
    # Filtrar partidas por categoria e período se especificado
    filtered_matches = matches.copy()
    
    if category != "Todas":
        tournament_ids = tournaments[tournaments['category'] == category]['id'].tolist()
        filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
    
    if time_period:
        # Converter o período para datetime se for string
        if isinstance(time_period, str):
            time_period = pd.to_datetime(time_period)
        filtered_matches = filtered_matches[
            pd.to_datetime(filtered_matches['started_month_year'], format='%m/%Y') >= time_period
        ]
    
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

@st.cache_data
def calculate_points_ranking(matches, players, tournaments, category=None, time_period=None):
    """Calcula ranking baseado em pontos por vitória"""
    # Filtrar partidas por categoria e período se especificado
    filtered_matches = matches.copy()
    
    if category is not None and category != "Todas":
        filtered_matches = filtered_matches[filtered_matches['tournament_category'] == category]
    
    if time_period:
        if isinstance(time_period, str):
            time_period = pd.to_datetime(time_period)
        filtered_matches = filtered_matches[
            pd.to_datetime(filtered_matches['started_month_year'], format='%m/%Y') >= time_period
        ]
    
    # Pontos por rodada
    points_map = {
        4: 1000,  # Final
        3: 650,   # Semifinal
        2: 400,   # Quartas
        1: 200    # Primeira rodada
    }
    
    # Agrupar por jogador e somar pontos
    winners = filtered_matches.groupby('winner_id').agg({
        'round': lambda x: sum(points_map.get(r, 0) for r in x)
    }).reset_index()
    
    winners.columns = ['player_id', 'points']
    
    # Adicionar nomes dos jogadores e filtrar pontos > 0
    points_df = winners.merge(players[['id', 'name']], left_on='player_id', right_on='id')
    points_df = points_df[points_df['points'] > 0].sort_values('points', ascending=False)
    
    return points_df

def display_rankings_page(matches, players, tournaments):
    """Exibe a página de rankings"""
    st.header("Rankings")
    
    # Seleção de categoria e período
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox(
            "Selecione a categoria:",
            ["Selecione..."] + sorted(tournaments['category'].unique().tolist())
        )
    with col2:
        time_period = st.selectbox(
            "Período:",
            ["Todo o histórico", "Somente este ano", "Últimos 12 meses", "Últimos 24 meses"]
        )
    
    # Só mostra os rankings se uma categoria for selecionada
    if category == "Selecione...":
        st.warning("⚠️ Por favor, selecione uma categoria para visualizar os rankings")
        return
    
    # Converter período para data se necessário
    if time_period == "Últimos 12 meses":
        time_period = pd.Timestamp.now() - pd.DateOffset(months=12)
    elif time_period == "Últimos 24 meses":
        time_period = pd.Timestamp.now() - pd.DateOffset(months=24)
    elif time_period == "Somente este ano":
        time_period = pd.Timestamp(f"{pd.Timestamp.now().year}-01-01")
    else:
        time_period = None
    
    # Calcular rankings
    glicko_ratings = calculate_glicko_ratings(
        matches, players, tournaments,
        category=category,
        time_period=time_period
    )
    
    points_ranking = calculate_points_ranking(
        matches, players, tournaments,
        category=category,
        time_period=time_period
    )
    
    # Exibir rankings
    tab1, tab2 = st.tabs(["Ranking Glicko-2", "Ranking por Pontos"])
    
    with tab1:
        st.subheader("Ranking Glicko-2")
        
        # Preparar DataFrame do Glicko
        glicko_df = glicko_ratings[['name', 'rating', 'rd']].rename(columns={
            'name': 'Jogador',
            'rating': 'Rating',
            'rd': 'Desvio Padrão'
        })
        
        # Estilizar tabela Glicko
        def style_glicko_table(df):
            def color_rows(x):
                df_len = len(df)
                colors = ['background-color: #f0f8ff' if i % 2 == 0 else '' for i in range(df_len)]
                return colors
            
            def bold_top3(x):
                df_len = len(df)
                return ['font-weight: bold' if x.name < 3 else '' for _ in range(len(df.columns))]
            
            return df.style.format({
                'Rating': '{:.0f}',
                'Desvio Padrão': '{:.0f}'
            }).apply(color_rows, axis=0).apply(bold_top3, axis=1).set_properties(**{
                'text-align': 'center',
                'font-size': '14px',
                'padding': '5px 15px'
            }).set_properties(subset=['Jogador'], **{
                'text-align': 'left'
            }).hide(axis="index")
        
        st.dataframe(
            style_glicko_table(glicko_df),
            use_container_width=True,
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
        
        # Preparar DataFrame de pontos
        points_df = points_ranking[['name', 'points']].rename(columns={
            'name': 'Jogador',
            'points': 'Pontos'
        })
        
        # Estilizar tabela de pontos
        def style_points_table(df):
            def color_rows(x):
                df_len = len(df)
                colors = ['background-color: #f0f8ff' if i % 2 == 0 else '' for i in range(df_len)]
                return colors
            
            def bold_top3(x):
                df_len = len(df)
                return ['font-weight: bold' if x.name < 3 else '' for _ in range(len(df.columns))]
            
            return df.style.format({
                'Pontos': '{:,.0f}'
            }).apply(color_rows, axis=0).apply(bold_top3, axis=1).set_properties(**{
                'text-align': 'center',
                'font-size': '14px',
                'padding': '5px 15px'
            }).set_properties(subset=['Jogador'], **{
                'text-align': 'left'
            }).hide(axis="index")
        
        st.dataframe(
            style_points_table(points_df),
            use_container_width=True,
            hide_index=True
        ) 