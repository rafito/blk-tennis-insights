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
    
    def get_points_for_round(row, is_champion=False):
        if pd.isna(row['round']) or pd.isna(row['tournament_name']):
            return 0
            
        is_finals = 'FINALS' in str(row['tournament_name']).upper()
        
        # Nova estrutura de pontos baseada nos Grand Slams
        if is_finals:
            # Torneios FINALS - estrutura adaptada
            if row['round'] == 3:  # Final
                return 2000 if is_champion else 1200  # Campeão vs Vice-campeão
            elif row['round'] == 2:  # Semifinal
                return 720
            elif row['round'] == 1:  # Quartas
                return 360
        else:
            # Torneios regulares - estrutura adaptada
            if row['round'] == 4:  # Final
                return 2000 if is_champion else 1200  # Campeão vs Vice-campeão
            elif row['round'] == 3:  # Semifinal
                return 720
            elif row['round'] == 2:  # Quartas
                return 360
            elif row['round'] == 1:  # Oitavas/Primeira rodada
                return 180
        
        return 0
    
    # Calcular pontos dos vencedores considerando se são campeões
    points_list = []
    for _, row in filtered_matches.iterrows():
        # Verificar se é campeão do torneio
        tournament_matches = filtered_matches[filtered_matches['tournament_id'] == row['tournament_id']]
        max_round = tournament_matches['round'].max()
        is_champion = (row['round'] == max_round)
        
        points = get_points_for_round(row, is_champion)
        points_list.append(points)
    
    filtered_matches['points'] = points_list
    
    # Agrupa por jogador e torneio, pegando a última rodada (maior pontuação) de cada torneio
    tournament_points = filtered_matches.groupby(['winner_id', 'tournament_id'])['points'].max().reset_index()
    winners = tournament_points.groupby('winner_id')['points'].sum().reset_index()
    winners.columns = ['player_id', 'points']
    
    # Calcular pontos dos perdedores (vice-campeões nas finais e participação)
    losers_points_list = []
    
    for _, row in filtered_matches.iterrows():
        loser_id = row['loser_id']
        tournament_id = row['tournament_id']
        round_num = row['round']
        
        # Verificar se é vice-campeão (perdedor da rodada mais alta)
        tournament_matches = filtered_matches[filtered_matches['tournament_id'] == tournament_id]
        max_round = tournament_matches['round'].max()
        
        if round_num == max_round:
            # Vice-campeão (perdedor da final)
            is_finals = 'FINALS' in str(row['tournament_name']).upper()
            points = 1200  # Vice-campeão recebe 1200 pontos
        elif round_num == 1:
            # Perdedor na primeira rodada recebe pontos de participação
            points = 10
        else:
            # Outros perdedores não recebem pontos (já receberam ao chegar na rodada)
            points = 0
        
        if points > 0:
            losers_points_list.append({
                'player_id': loser_id,
                'tournament_id': tournament_id,
                'points': points
            })
    
    if losers_points_list:
        losers_df = pd.DataFrame(losers_points_list)
        losers_points = losers_df.groupby('player_id')['points'].sum().reset_index()
    else:
        losers_points = pd.DataFrame(columns=['player_id', 'points'])
    
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

@st.cache_data
def get_player_points_breakdown(player_id, matches, players, tournaments, category=None, time_period=None):
    """Retorna detalhamento dos pontos de um jogador específico"""
    # Filtrar partidas por categoria e período se especificado
    filtered_matches = matches.copy()
    
    if category is not None and category != "Todas":
        tournament_ids = tournaments[tournaments['category'] == category]['id'].tolist()
        filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
    
    if time_period:
        if isinstance(time_period, str):
            time_period = pd.to_datetime(time_period)
        filtered_matches = filtered_matches[
            pd.to_datetime(filtered_matches['started_month_year'], format='%m/%Y') >= time_period
        ]
    
    # Filtrar partidas onde o jogador participou
    player_matches = filtered_matches[
        (filtered_matches['winner_id'] == player_id) | 
        (filtered_matches['loser_id'] == player_id)
    ].copy()
    
    if player_matches.empty:
        return pd.DataFrame()
    
    def get_points_for_round(row, is_champion=False):
        if pd.isna(row['round']) or pd.isna(row['tournament_name']):
            return 0
            
        is_finals = 'FINALS' in str(row['tournament_name']).upper()
        
        if is_finals:
            if row['round'] == 3:  # Final
                return 2000 if is_champion else 1200
            elif row['round'] == 2:  # Semifinal
                return 720
            elif row['round'] == 1:  # Quartas
                return 360
        else:
            if row['round'] == 4:  # Final
                return 2000 if is_champion else 1200
            elif row['round'] == 3:  # Semifinal
                return 720
            elif row['round'] == 2:  # Quartas
                return 360
            elif row['round'] == 1:  # Oitavas/Primeira rodada
                return 180
        
        return 0
    
    # Calcular pontos por torneio
    breakdown = []
    
    for tournament_id in player_matches['tournament_id'].unique():
        tournament_matches = player_matches[player_matches['tournament_id'] == tournament_id]
        tournament_info = tournaments[tournaments['id'] == tournament_id].iloc[0]
        
        # Encontrar a melhor performance no torneio
        best_performance = None
        max_points = 0
        
        # Verificar vitórias (performance como vencedor)
        wins = tournament_matches[tournament_matches['winner_id'] == player_id]
        if not wins.empty:
            max_round_won = wins['round'].max()
            best_win = wins[wins['round'] == max_round_won].iloc[0]
            
            # Verificar se é campeão
            all_tournament_matches = filtered_matches[filtered_matches['tournament_id'] == tournament_id]
            tournament_max_round = all_tournament_matches['round'].max()
            is_champion = (max_round_won == tournament_max_round)
            
            points = get_points_for_round(best_win, is_champion)
            if points > max_points:
                max_points = points
                round_name = get_round_name(best_win['round'], tournament_info['name'])
                status = "Campeão" if is_champion else f"Venceu {round_name}"
                best_performance = {
                    'tournament': tournament_info['name'],
                    'date': tournament_info['started_month_year'],
                    'performance': status,
                    'points': points
                }
        
        # Verificar derrotas (performance como perdedor)
        losses = tournament_matches[tournament_matches['loser_id'] == player_id]
        if not losses.empty:
            max_round_lost = losses['round'].max()
            best_loss = losses[losses['round'] == max_round_lost].iloc[0]
            
            # Verificar se é vice-campeão
            all_tournament_matches = filtered_matches[filtered_matches['tournament_id'] == tournament_id]
            tournament_max_round = all_tournament_matches['round'].max()
            
            if max_round_lost == tournament_max_round:
                # Vice-campeão
                points = 1200
                if points > max_points:
                    max_points = points
                    best_performance = {
                        'tournament': tournament_info['name'],
                        'date': tournament_info['started_month_year'],
                        'performance': "Vice-campeão",
                        'points': points
                    }
            elif max_round_lost == 1:
                # Perdeu na primeira rodada - pontos de participação
                points = 10
                if max_points == 0:  # Só se não tiver outras performances
                    max_points = points
                    best_performance = {
                        'tournament': tournament_info['name'],
                        'date': tournament_info['started_month_year'],
                        'performance': "Participação (1ª rodada)",
                        'points': points
                    }
        
        if best_performance:
            breakdown.append(best_performance)
    
    # Converter para DataFrame e ordenar por pontos
    if breakdown:
        breakdown_df = pd.DataFrame(breakdown)
        breakdown_df = breakdown_df.sort_values('points', ascending=False)
        return breakdown_df
    else:
        return pd.DataFrame()

def get_round_name(round_num, tournament_name):
    """Converte número da rodada para nome legível"""
    is_finals = 'FINALS' in str(tournament_name).upper()
    
    if is_finals:
        if round_num == 3:
            return "Final"
        elif round_num == 2:
            return "Semifinal"
        elif round_num == 1:
            return "Quartas"
    else:
        if round_num == 4:
            return "Final"
        elif round_num == 3:
            return "Semifinal"
        elif round_num == 2:
            return "Quartas"
        elif round_num == 1:
            return "Oitavas/1ª rodada"
    
    return f"Rodada {round_num}"

def display_ranking_with_icons(ranking_df, ranking_type="Glicko", matches=None, players=None, tournaments=None, category=None, time_period=None):
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
            show_points_button = False
        else:  # Pontos
            points = int(row['points'])
            set_balance = int(row['set_balance'])
            extra_info = f"Pontos: {points:,} | Saldo: {set_balance:+d}"
            show_points_button = True
        
        # Linha com layout em colunas e ações à direita
        key_suffix = f"{ranking_type}_{player_id}"
        medal = ""
        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"

        col_pos, col_name, col_stats, col_actions = st.columns([1, 6, 3, 2])
        with col_pos:
            st.markdown(f"**{position}º** {medal}")
        with col_name:
            st.markdown(f"**{player_name}**")
        with col_stats:
            st.caption(extra_info)
        with col_actions:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👤", key=f"profile_{key_suffix}", help="Ver análise do jogador"):
                    st.query_params["page"] = "Análise de Jogadores"
                    st.query_params["player_id"] = str(player_id)
                    st.rerun()
            with c2:
                if show_points_button and matches is not None:
                    with st.popover("📊", use_container_width=False):
                        st.markdown(f"**{player_name}** — Detalhes dos pontos")
                        with st.spinner("Carregando..."):
                            breakdown_df = get_player_points_breakdown(
                                player_id, matches, players, tournaments, category, time_period
                            )
                        if breakdown_df is not None and not breakdown_df.empty:
                            st.metric("Total", f"{int(breakdown_df['points'].sum()):,} pts")
                            show_df = breakdown_df.rename(columns={
                                'tournament': 'Torneio',
                                'date': 'Data',
                                'performance': 'Resultado',
                                'points': 'Pontos'
                            })[["Torneio","Data","Resultado","Pontos"]]
                            st.dataframe(show_df, hide_index=True, use_container_width=True)
                        else:
                            st.info("Sem pontos no período.")
        st.divider()
        
        # Removido bloco expandido para evitar poluição visual; usando popover acima

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
                display_ranking_with_icons(
                    glicko_ratings, "Glicko", 
                    matches, players, tournaments, category, time_period
                )
        else:
            st.info("Não há dados suficientes para gerar o ranking Glicko-2 neste período.")
    
    with tab2:
        st.subheader("Ranking por Pontos")
        
        # Substituir card de info por expander
        with st.expander("ℹ️ Como funciona o Ranking por Pontos?"):
            st.write("""
            O ranking por pontos segue o sistema dos Grand Slams de tênis:
            
            **Sistema de Pontuação:**
            - **Campeão:** 2.000 pontos
            - **Vice-campeão:** 1.200 pontos
            - **Semifinalistas:** 720 pontos
            - **Quartas de final:** 360 pontos
            - **Oitavas/Primeira rodada:** 180 pontos
            
            **Torneios FINALS:**
            - Seguem a mesma estrutura, mas com menos rodadas
            - Final: Campeão (2.000) vs Vice-campeão (1.200)
            - Semifinal: 720 pontos
            - Quartas: 360 pontos
            
            **Pontos de Participação:**
            - Jogadores que perdem na primeira rodada recebem 10 pontos de participação
            
            **Critérios de desempate:** Saldo de Sets
            """)
        
        if not points_ranking.empty:
            with st.spinner('Preparando ranking por pontos...'):
                display_ranking_with_icons(
                    points_ranking, "Pontos", 
                    matches, players, tournaments, category, time_period
                )
        else:
            st.info("Não há dados suficientes para gerar o ranking por pontos neste período.") 