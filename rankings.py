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
        if pd.notna(match['winner_id']) and pd.notna(match['loser_id']):
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
    """Calcula ranking baseado em pontos por vitória e saldo de sets"""
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
    
    def get_points_for_round(row):
        if pd.isna(row['round']) or pd.isna(row['tournament_name']):
            return 0
            
        is_finals = 'FINALS' in str(row['tournament_name']).upper()
        
        # Pontos para torneios FINALS
        points_finals = {
            3: 1000,  # Final
            2: 650,   # Semifinal
            1: 400    # Quartas
        }
        
        # Pontos para torneios regulares
        points_regular = {
            4: 1000,  # Final
            3: 650,   # Semifinal
            2: 400,   # Quartas
            1: 200    # Primeira rodada
        }
        
        points_map = points_finals if is_finals else points_regular
        return points_map.get(row['round'], 0)
    
    # Calcular pontos dos vencedores
    filtered_matches['points'] = filtered_matches.apply(get_points_for_round, axis=1)
    
    # Agrupa por jogador e torneio, pegando a última rodada (maior pontuação) de cada torneio
    tournament_points = filtered_matches.groupby(['winner_id', 'tournament_id'])['points'].max().reset_index()
    winners = tournament_points.groupby('winner_id')['points'].sum().reset_index()
    winners.columns = ['player_id', 'points']
    
    # Calcular pontos dos perdedores na primeira rodada (10 pontos)
    first_round_losers = filtered_matches[
        ((filtered_matches['round'] == 1) & ~filtered_matches['tournament_name'].str.contains('FINALS', case=False, na=False)) |
        ((filtered_matches['round'] == 1) & filtered_matches['tournament_name'].str.contains('FINALS', case=False, na=False))
    ][['loser_id', 'tournament_id']].drop_duplicates()
    
    first_round_losers['points'] = 10
    losers_points = first_round_losers.groupby('loser_id')['points'].sum().reset_index()
    losers_points.columns = ['player_id', 'points']
    
    # Combinar pontos de vencedores e perdedores
    all_points = pd.concat([winners, losers_points])
    all_points = all_points.groupby('player_id')['points'].sum().reset_index()
    
    # Calcular saldo de sets para cada jogador
    set_balance = filtered_matches.groupby('winner_id')['set_balance'].sum().reset_index()
    set_balance.columns = ['player_id', 'set_balance']
    
    # Adicionar saldo de sets negativo para os perdedores
    loser_set_balance = filtered_matches.groupby('loser_id')['set_balance'].sum().reset_index()
    loser_set_balance.columns = ['player_id', 'set_balance']
    loser_set_balance['set_balance'] = -loser_set_balance['set_balance']
    
    # Combinar saldo de sets
    all_set_balance = pd.concat([set_balance, loser_set_balance])
    all_set_balance = all_set_balance.groupby('player_id')['set_balance'].sum().reset_index()
    
    # Juntar pontos com saldo de sets
    ranking_df = all_points.merge(all_set_balance, on='player_id', how='left')
    ranking_df['set_balance'] = ranking_df['set_balance'].fillna(0)
    
    # Adicionar nomes dos jogadores e ordenar por pontos (primeiro critério) e saldo de sets (segundo critério)
    ranking_df = ranking_df.merge(players[['id', 'name']], left_on='player_id', right_on='id')
    ranking_df = ranking_df[ranking_df['points'] > 0].sort_values(['points', 'set_balance'], ascending=[False, False])
    
    return ranking_df

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
    with st.spinner('Calculando rankings...'):
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
        
        if glicko_ratings.empty:
            st.info("Não há dados suficientes para gerar o ranking Glicko-2 neste período.")
            return
            
        with st.spinner('Preparando ranking Glicko-2...'):
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
                    return ['font-weight: bold' if i < 3 else '' for i in range(len(df.columns))]
                
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
            top_5 = glicko_ratings.head(min(5, len(glicko_ratings)))
            if not top_5.empty:
                fig = px.bar(top_5, x='name', y='rating',
                            labels={'name': 'Jogador', 'rating': 'Rating'},
                            title="Top 5 Jogadores por Rating Glicko-2")
                st.plotly_chart(fig)
    
    with tab2:
        st.subheader("Ranking por Pontos")
        
        if points_ranking.empty:
            st.info("Não há dados suficientes para gerar o ranking por pontos neste período.")
            return
            
        with st.spinner('Preparando ranking por pontos...'):
            # Preparar DataFrame de pontos
            points_df = points_ranking[['name', 'points', 'set_balance']].rename(columns={
                'name': 'Jogador',
                'points': 'Pontos',
                'set_balance': 'Saldo de Sets'
            })
            
            # Estilizar tabela de pontos
            def style_points_table(df):
                def color_rows(x):
                    df_len = len(df)
                    colors = ['background-color: #f0f8ff' if i % 2 == 0 else '' for i in range(df_len)]
                    return colors
                
                def bold_top3(x):
                    df_len = len(df)
                    return ['font-weight: bold' if i < 3 else '' for i in range(len(df.columns))]
                
                return df.style.format({
                    'Pontos': '{:,.0f}',
                    'Saldo de Sets': '{:+.0f}'
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