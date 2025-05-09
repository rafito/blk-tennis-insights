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
    
    # Obter lista de jogadores ativos no período
    active_players = pd.concat([
        filtered_matches['winner_id'],
        filtered_matches['loser_id']
    ]).unique()
    
    # Inicializar sistema Glicko-2
    glicko_system = GlickoSystem()
    
    # Processar partidas em ordem cronológica
    filtered_matches = filtered_matches.sort_values('started_month_year')
    
    for _, match in filtered_matches.iterrows():
        if pd.notna(match['winner_id']) and pd.notna(match['loser_id']):
            glicko_system.update_match(match['winner_id'], match['loser_id'])
    
    # Converter ratings para DataFrame apenas para jogadores ativos
    ratings_df = pd.DataFrame([
        {
            'player_id': player_id,
            'rating': rating,
            'rd': rd,
            'vol': vol
        }
        for player_id in active_players
        for rating, rd, vol in [glicko_system.get_rating(player_id)]
    ])
    
    # Adicionar nomes dos jogadores
    ratings_df = ratings_df.merge(players[['id', 'name']], left_on='player_id', right_on='id')
    ratings_df['name'] = ratings_df['name'].str.upper()
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
    ranking_df['name'] = ranking_df['name'].str.upper()
    ranking_df = ranking_df[ranking_df['points'] > 0].sort_values(['points', 'set_balance'], ascending=[False, False])
    
    return ranking_df

def display_rankings_page(matches, players, tournaments):
    """Exibe a página de rankings"""
    st.header("Rankings")
    
    # Seleção de categoria e período
    col1, col2 = st.columns(2)
    with col1:
        categories = ["Selecione..."] + sorted(tournaments['category'].unique().tolist())
        try:
            default_index = categories.index("3a Classe")
        except ValueError:
            default_index = 1 if len(categories) > 1 else 0
        
        category = st.selectbox(
            "Selecione a categoria:",
            categories,
            index=default_index
        )
    with col2:
        time_period = st.selectbox(
            "Período:",
            ["Todo o histórico", "Somente este ano", "Últimos 12 meses", "Últimos 24 meses"],
            index=2  # Define "Últimos 12 meses" como padrão (índice 2 na lista)
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
        
        # Substituir card de info por expander
        with st.expander("ℹ️ Como funciona o Ranking Glicko-2?"):
            st.write("""
            O ranking Glicko-2 é um sistema sofisticado que considera:
            - Resultado das partidas (vitória/derrota)
            - Força dos adversários enfrentados
            - Frequência de jogos (quanto mais jogos, mais preciso o rating)
            - Desvio padrão (quanto menor, mais confiável é o rating)
            
            O rating base é 1500, com desvio padrão inicial de 350.
            Quanto maior o rating, melhor a performance do jogador.
            """)
        
        if not glicko_ratings.empty:
            with st.spinner('Preparando ranking Glicko-2...'):
                # Preparar DataFrame do Glicko
                glicko_df = glicko_ratings[['name', 'rating', 'rd']].rename(columns={
                    'name': 'Jogador',
                    'rating': 'Rating',
                    'rd': 'Desvio Padrão'
                })
                
                # Adicionar coluna de posição
                glicko_df.insert(0, 'Pos.', range(1, len(glicko_df) + 1))
                
                # Estilizar tabela Glicko
                def style_glicko_table(df):
                    def color_rows(x):
                        df_len = len(df)
                        colors = []
                        for i in range(df_len):
                            if i < 10:  # Top 10
                                colors.append('background-color: #e6f3ff')
                            elif i % 2 == 0:
                                colors.append('background-color: #f8f9fa')
                            else:
                                colors.append('')
                        return colors
                    
                    def bold_top3(x):
                        df_len = len(df)
                        return ['font-weight: bold' if i < 3 else '' for i in range(len(df.columns))]
                    
                    return df.style.format({
                        'Pos.': '{:.0f}',
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
        else:
            st.info("Não há dados suficientes para gerar o ranking Glicko-2 neste período.")
    
    with tab2:
        st.subheader("Ranking por Pontos")
        
        # Substituir card de info por expander
        with st.expander("ℹ️ Como funciona o Ranking por Pontos?"):
            st.write("""
            O ranking por pontos é baseado na performance em torneios:
            
            Torneios Regulares:
            - Campeão: 1000 pontos
            - Vice-campeão: 650 pontos
            - Semifinal: 400 pontos
            - Primeira rodada: 200 pontos
            
            Torneios Finals:
            - Campeão: 1000 pontos
            - Vice-campeão: 650 pontos
            - Semifinal: 400 pontos
            
            Pontos de Participação:
            - Todo jogador que participa de um torneio recebe 10 pontos se perder na primeira rodada.
            
            Critérios de desempate: Saldo de Sets
            """)
        
        if not points_ranking.empty:
            with st.spinner('Preparando ranking por pontos...'):
                # Preparar DataFrame de pontos
                points_df = points_ranking[['name', 'points', 'set_balance']].rename(columns={
                    'name': 'Jogador',
                    'points': 'Pontos',
                    'set_balance': 'Saldo de Sets'
                })
                
                # Adicionar coluna de posição
                points_df.insert(0, 'Pos.', range(1, len(points_df) + 1))
                
                # Estilizar tabela de pontos
                def style_points_table(df):
                    def color_rows(x):
                        df_len = len(df)
                        colors = []
                        for i in range(df_len):
                            if i < 10:  # Top 10
                                colors.append('background-color: #e6f3ff')
                            elif i % 2 == 0:
                                colors.append('background-color: #f8f9fa')
                            else:
                                colors.append('')
                        return colors
                    
                    def bold_top3(x):
                        df_len = len(df)
                        return ['font-weight: bold' if i < 3 else '' for i in range(len(df.columns))]
                    
                    return df.style.format({
                        'Pos.': '{:.0f}',
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
        else:
            st.info("Não há dados suficientes para gerar o ranking por pontos neste período.") 