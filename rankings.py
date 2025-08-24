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
        # Usar o mesmo método que o Glicko: filtrar por tournament_id baseado na categoria
        tournament_ids = tournaments[tournaments['category'] == category]['id'].tolist()
        filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
    
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

def display_ranking_with_icons(ranking_df, ranking_type="Glicko"):
    """Exibe ranking com ícones clicáveis para análise de jogadores"""
    if ranking_df.empty:
        return
    
    host = st.session_state.get('host', 'http://localhost:8502')
    
    # Criar HTML personalizado para cada linha do ranking
    for i, (_, row) in enumerate(ranking_df.iterrows()):
        player_id = row['player_id']
        player_name = row['name']
        position = i + 1
        
        # Link para análise do jogador
        player_link = f"{host}?page=Análise de Jogadores&player_id={player_id}"
        
        # Definir cor de fundo baseada na posição
        if position <= 3:
            bg_color = "#fff3cd"  # Dourado para top 3
            border_color = "#ffc107"
        elif position <= 10:
            bg_color = "#e6f3ff"  # Azul claro para top 10
            border_color = "#007bff"
        else:
            bg_color = "#f8f9fa"  # Cinza claro para o resto
            border_color = "#dee2e6"
        
        # Preparar dados específicos por tipo de ranking
        if ranking_type == "Glicko":
            rating = int(row['rating'])
            rd = int(row['rd'])
            extra_info = f"Rating: {rating} | RD: {rd}"
        else:  # Pontos
            points = int(row['points'])
            set_balance = int(row['set_balance'])
            extra_info = f"Pontos: {points:,} | Saldo: {set_balance:+d}"
        
        # Criar linha compacta do ranking
        st.markdown(f"""
        <div style="
            border-left: 4px solid {border_color};
            background-color: {bg_color};
            padding: 8px 12px;
            margin: 2px 0;
            border-radius: 0 6px 6px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: 50px;
        ">
            <div style="display: flex; align-items: center; flex-grow: 1;">
                <div style="
                    font-weight: bold;
                    font-size: 16px;
                    color: #495057;
                    margin-right: 12px;
                    min-width: 35px;
                    text-align: center;
                ">
                    {position}º
                </div>
                <div style="flex-grow: 1;">
                    <span style="
                        font-weight: bold;
                        font-size: 16px;
                        color: #212529;
                        margin-right: 10px;
                    ">{player_name}</span>
                    <span style="
                        font-size: 13px;
                        color: #6c757d;
                    ">({extra_info})</span>
                </div>
            </div>
            <a href="{player_link}" target="_self" style="
                text-decoration: none;
                background-color: #007bff;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                border: none;
                cursor: pointer;
                transition: background-color 0.3s;
                white-space: nowrap;
            " title="Ver análise do jogador">
                👤
            </a>
        </div>
        """, unsafe_allow_html=True)

def display_rankings_page(matches, players, tournaments):
    """Exibe a página de rankings"""
    st.header("Rankings")
    
    # Garantir que o host esteja disponível na session_state
    if 'host' not in st.session_state:
        st.session_state['host'] = 'http://localhost:8502'
    
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
    
    # Mostrar informações sobre os torneios sendo computados
    with st.expander("📊 Torneios Computados neste Ranking", expanded=False):
        # Filtrar torneios pela categoria e período selecionados
        filtered_tournaments = tournaments.copy()
        
        if category != "Todas":
            filtered_tournaments = filtered_tournaments[filtered_tournaments['category'] == category]
        
        if time_period:
            # Converter started_month_year para datetime para comparação
            filtered_tournaments['started_date'] = pd.to_datetime(
                filtered_tournaments['started_month_year'], 
                format='%m/%Y'
            )
            filtered_tournaments = filtered_tournaments[
                filtered_tournaments['started_date'] >= time_period
            ]
        
        # Filtrar partidas para mostrar estatísticas
        filtered_matches = matches.copy()
        if category != "Todas":
            tournament_ids = filtered_tournaments['id'].tolist()
            filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
        
        if time_period:
            filtered_matches = filtered_matches[
                pd.to_datetime(filtered_matches['started_month_year'], format='%m/%Y') >= time_period
            ]
        
        # Mostrar estatísticas
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("Torneios", len(filtered_tournaments))
        with col_stats2:
            st.metric("Partidas", len(filtered_matches))
        with col_stats3:
            unique_players = pd.concat([
                filtered_matches['winner_id'], 
                filtered_matches['loser_id']
            ]).nunique()
            st.metric("Jogadores Ativos", unique_players)
        
        # Lista dos torneios
        if not filtered_tournaments.empty:
            st.subheader("Lista de Torneios:")
            tournaments_display = filtered_tournaments[['name', 'started_month_year']].copy()
            tournaments_display = tournaments_display.sort_values('started_month_year', ascending=False)
            tournaments_display.columns = ['Nome do Torneio', 'Data (Mês/Ano)']
            
            st.dataframe(
                tournaments_display,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum torneio encontrado para os filtros selecionados.")
    
    # Botão para limpar cache (útil para debug)
    if st.button("🔄 Limpar Cache e Recalcular", help="Use se os dados não estiverem atualizados"):
        st.cache_data.clear()
        st.rerun()
    
    # Debug: Mostrar informações sobre o filtro de período
    if time_period:
        st.info(f"📅 Filtrando dados a partir de: {time_period.strftime('%d/%m/%Y')}")
    
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
                display_ranking_with_icons(glicko_ratings, "Glicko")
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
                display_ranking_with_icons(points_ranking, "Pontos")
        else:
            st.info("Não há dados suficientes para gerar o ranking por pontos neste período.") 