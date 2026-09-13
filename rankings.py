import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from glicko import GlickoSystem


def filter_dataframe_by_period(df, column_name, time_period):
    """Filtra um DataFrame pelo período selecionado."""
    if not time_period:
        return df

    if isinstance(time_period, tuple):
        start_date, end_date = time_period
        if start_date is None and end_date is None:
            return df
    else:
        start_date, end_date = time_period, None

    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)

    dates = pd.to_datetime(df[column_name], format='%m/%Y')
    mask = pd.Series(True, index=df.index)

    if start_date is not None:
        mask &= dates >= start_date
    if end_date is not None:
        mask &= dates <= end_date

    return df.loc[mask]


@st.cache_data
def calculate_glicko_ratings(matches, players, tournaments, category=None, time_period=None):
    """Calcula ratings Glicko-2 para os jogadores"""
    # Filtrar partidas por categoria e período se especificado
    filtered_matches = matches.copy()
    
    if category != "Todas":
        tournament_ids = tournaments[tournaments['category'] == category]['id'].tolist()
        filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
    
    filtered_matches = filter_dataframe_by_period(
        filtered_matches, 'started_month_year', time_period
    )
    
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
    ratings_df = ratings_df.merge(players[['id', 'name', 'disqualified']], left_on='player_id', right_on='id')
    ratings_df['name'] = ratings_df['name'].str.upper()
    # Remover jogadores desclassificados do ranking exibido (o cálculo do Glicko em si já os considerou como adversários)
    ratings_df = ratings_df[ratings_df['disqualified'] == 0]
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
    
    filtered_matches = filter_dataframe_by_period(
        filtered_matches, 'started_month_year', time_period
    )
    
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
    
    # Pontos dos vencedores por torneio (pegar a maior rodada vencida no torneio)
    winners_tournament_points = filtered_matches.groupby(['winner_id', 'tournament_id'])['points'].max().reset_index()
    winners_tournament_points = winners_tournament_points.rename(columns={'winner_id': 'player_id'})
    
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
            points = 180
        else:
            # Outros perdedores recebem pontos baseados na rodada que perderam
            if round_num == max_round - 1:  # Perdedor na semifinal
                points = 720
            elif round_num == max_round - 2:  # Perdedor nas quartas
                points = 360
            else:
                points = 0
        
        if points > 0:
            losers_points_list.append({
                'player_id': loser_id,
                'tournament_id': tournament_id,
                'points': points
            })
    
    if losers_points_list:
        losers_df = pd.DataFrame(losers_points_list)
        # Pontos dos perdedores por torneio (ex.: vice-campeão, participação)
        losers_tournament_points = losers_df.groupby(['player_id', 'tournament_id'])['points'].max().reset_index()
    else:
        losers_tournament_points = pd.DataFrame(columns=['player_id', 'tournament_id', 'points'])

    # Combinar por torneio e pegar o melhor resultado do jogador em cada torneio (evita somar 720 + 1200)
    combined_tournament_points = pd.concat([winners_tournament_points, losers_tournament_points], ignore_index=True)
    if not combined_tournament_points.empty:
        best_tournament_points = combined_tournament_points.groupby(['player_id', 'tournament_id'])['points'].max().reset_index()
        all_points = best_tournament_points.groupby('player_id')['points'].sum().reset_index()
    else:
        all_points = pd.DataFrame(columns=['player_id', 'points'])
    
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
    ranking_df = ranking_df.merge(players[['id', 'name', 'disqualified']], left_on='player_id', right_on='id')
    ranking_df['name'] = ranking_df['name'].str.upper()
    # Remover jogadores desclassificados do ranking exibido
    ranking_df = ranking_df[ranking_df['disqualified'] == 0]
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
    
    filtered_matches = filter_dataframe_by_period(
        filtered_matches, 'started_month_year', time_period
    )
    
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
    
    def get_stage_label(round_num, tournament_name):
        """Retorna o nome da etapa (sem preposição) para compor frases de derrota."""
        is_finals = 'FINALS' in str(tournament_name).upper()
        if is_finals:
            mapping = {1: 'Quartas', 2: 'Semifinal', 3: 'Final'}
        else:
            mapping = {1: 'Oitavas', 2: 'Quartas', 3: 'Semifinal', 4: 'Final'}
        return mapping.get(int(round_num), f"Rodada {int(round_num)}")
    
    def loss_phrase(round_num, tournament_name):
        """Monta a frase 'Perdeu na(s) X' com a preposição correta."""
        if int(round_num) == 1 and 'FINALS' not in str(tournament_name).upper():
            # Caso especial para torneios regulares onde 1 é 'Oitavas' (plural)
            label = get_stage_label(round_num, tournament_name)
            prep = 'nas' if label in ('Quartas', 'Oitavas') else 'na'
            return f"Perdeu {prep} {label}"
        label = get_stage_label(round_num, tournament_name)
        prep = 'nas' if label in ('Quartas', 'Oitavas') else 'na'
        return f"Perdeu {prep} {label}"
    
    # Calcular pontos por torneio
    breakdown = []
    
    for tournament_id in player_matches['tournament_id'].unique():
        tournament_matches = player_matches[player_matches['tournament_id'] == tournament_id]
        tournament_info = tournaments[tournaments['id'] == tournament_id].iloc[0]
        
        # Encontrar a melhor performance no torneio com rótulo de etapa alcançada
        best_performance = None
        max_points = 0

        wins = tournament_matches[tournament_matches['winner_id'] == player_id]
        losses = tournament_matches[tournament_matches['loser_id'] == player_id]

        all_tournament_matches = filtered_matches[filtered_matches['tournament_id'] == tournament_id]
        tournament_max_round = all_tournament_matches['round'].max()

        # Caso 1: Campeão
        if not wins.empty and wins['round'].max() == tournament_max_round:
            best_win = wins[wins['round'] == wins['round'].max()].iloc[0]
            points = get_points_for_round(best_win, is_champion=True)
            max_points = points
            best_performance = {
                'tournament': tournament_info['name'],
                'date': tournament_info['started_month_year'],
                'performance': "Campeão",
                'points': points
            }
        else:
            # Derrota existente define a etapa alcançada
            if not losses.empty:
                max_round_lost = int(losses['round'].max())
                # Caso 2: Perdeu na Final (vice)
                if max_round_lost == int(tournament_max_round):
                    points = 1200
                    max_points = points
                    best_performance = {
                        'tournament': tournament_info['name'],
                        'date': tournament_info['started_month_year'],
                        'performance': loss_phrase(max_round_lost, tournament_info['name']),
                        'points': points
                    }
                else:
                    # Determinar pontos baseados na rodada em que perdeu
                    if max_round_lost == tournament_max_round - 1:  # Perdeu na semifinal
                        points = 720
                    elif max_round_lost == tournament_max_round - 2:  # Perdeu nas quartas
                        points = 360
                    elif max_round_lost == 1:  # Perdeu na primeira rodada
                        points = 180
                    else:
                        points = 0
                    
                    if points > 0:
                        max_points = points
                        best_performance = {
                            'tournament': tournament_info['name'],
                            'date': tournament_info['started_month_year'],
                            'performance': loss_phrase(max_round_lost, tournament_info['name']),
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
    """Exibe ranking com linhas compactas, nome clicável e tooltip on-hover."""
    if ranking_df.empty:
        return

    host = st.session_state.get('host', 'http://localhost:8502')

    # CSS para linhas mais compactas e tooltip por hover
    st.markdown(
        """
        <style>
        .ranking-row { display:flex; align-items:center; gap:8px; padding:6px 10px; border:1px solid var(--row-border); border-radius:8px; margin:6px 0; position:relative; min-height:32px; }
        .ranking-pos { width:40px; font-weight:700; text-align:right; }
        .ranking-name { flex:1; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .ranking-name a { color:inherit; text-decoration:none; }
        .ranking-name a:hover { text-decoration:underline; }
        .ranking-stats { font-size:12px; color:#6c757d; min-width:220px; text-align:right; }
        .ranking-hover { display:none; position:absolute; right:10px; top:36px; background:#ffffff; color:#111; border:1px solid #dee2e6; border-radius:8px; box-shadow:0 6px 24px rgba(0,0,0,0.12); padding:10px; z-index:10; min-width:260px; max-width:420px; }
        .ranking-row:hover .ranking-hover { display:block; }
        .ranking-hover h4 { margin:0 0 6px 0; font-size:13px; }
        .ranking-hover table { width:100%; border-collapse:collapse; font-size:12px; }
        .ranking-hover td, .ranking-hover th { padding:4px 6px; border-bottom:1px solid #f1f3f5; text-align:left; }
        .ranking-medal { margin-left:6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Renderização de cada linha
    for i, (_, row) in enumerate(ranking_df.iterrows()):
        player_id = row['player_id']
        player_name = row['name']
        position = i + 1

        player_link = f"{host}?page=Análise de Jogadores&player_id={player_id}"

        # Destaques por posição
        if position <= 3:
            bg_color = "#fff3cd"  # top 3
            border_color = "#ffc107"
        elif position <= 10:
            bg_color = "#e6f3ff"  # top 10
            border_color = "#007bff"
        else:
            bg_color = "#f8f9fa"
            border_color = "#dee2e6"

        medal = ""
        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"

        # Info compacta por tipo
        if ranking_type == "Glicko":
            rating = int(row['rating'])
            rd = int(row['rd'])
            extra_info = f"Rating: {rating} | RD: {rd}"
            hover_title = f"{player_name} — Glicko-2"
            hover_body = f"<div>Rating: <b>{rating}</b><br/>Desvio (RD): <b>{rd}</b></div>"
        else:
            points = int(row['points'])
            set_balance = int(row['set_balance'])
            extra_info = f"Pontos: {points:,} | Saldo: {set_balance:+d}"
            hover_title = f"{player_name} — Detalhes dos pontos"
            # Calcular breakdown para tooltip
            breakdown_html = "<div>Sem pontos no período.</div>"
            if matches is not None and players is not None and tournaments is not None:
                breakdown_df = get_player_points_breakdown(
                    player_id, matches, players, tournaments, category, time_period
                )
                if breakdown_df is not None and not breakdown_df.empty:
                    total_pts = int(breakdown_df['points'].sum())
                    top_rows = breakdown_df.head(5).copy()
                    rows_html = "".join(
                        f"<tr><td>{r['tournament']}</td><td>{r['date']}</td><td>{r['performance']}</td><td style='text-align:right;'>{int(r['points'])}</td></tr>"
                        for _, r in top_rows.iterrows()
                    )
                    breakdown_html = (
                        f"<div style='margin-bottom:6px;'>Total: <b>{total_pts:,} pts</b></div>"
                        f"<table><thead><tr><th>Torneio</th><th>Data</th><th>Resultado</th><th style='text-align:right;'>Pts</th></tr></thead><tbody>{rows_html}</tbody></table>"
                    )
            hover_body = breakdown_html

        row_html = f"""
        <div class='ranking-row' style='--row-border:{border_color}; background:{bg_color};'>
            <div class='ranking-pos'>{position}º <span class='ranking-medal'>{medal}</span></div>
            <div class='ranking-name'><a href='{player_link}' target='_self'>{player_name}</a></div>
            <div class='ranking-stats'>{extra_info}</div>
            <div class='ranking-hover'>
                <h4>{hover_title}</h4>
                {hover_body}
            </div>
        </div>
        """

        st.markdown(row_html, unsafe_allow_html=True)

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
        base_period_options = [
            "Todo o histórico",
            "Somente este ano",
            "Últimos 12 meses",
            "Últimos 24 meses",
        ]
        unique_years = (
            tournaments['started_month_year']
            .dropna()
            .astype(str)
            .str[-4:]
        )
        year_options = sorted(
            {int(year) for year in unique_years if year.isdigit()},
            reverse=True
        )
        period_options = base_period_options + [f"Ranking {year}" for year in year_options]
        default_period_index = (
            period_options.index("Somente este ano")
            if "Somente este ano" in period_options
            else 0
        )
        selected_period = st.selectbox(
            "Período:",
            period_options,
            index=default_period_index
        )
    
    # Só mostra os rankings se uma categoria for selecionada
    if category == "Selecione...":
        st.warning("⚠️ Por favor, selecione uma categoria para visualizar os rankings")
        return
    
    now = pd.Timestamp.now().normalize()
    filter_start = None
    filter_end = None

    if selected_period == "Últimos 12 meses":
        filter_start = now - pd.DateOffset(months=12)
        filter_end = now
    elif selected_period == "Últimos 24 meses":
        filter_start = now - pd.DateOffset(months=24)
        filter_end = now
    elif selected_period == "Somente este ano":
        filter_start = pd.Timestamp(f"{now.year}-01-01")
        filter_end = pd.Timestamp(f"{now.year}-12-31")
    elif selected_period.startswith("Ranking "):
        try:
            year = int(selected_period.split(" ")[1])
            filter_start = pd.Timestamp(f"{year}-01-01")
            filter_end = pd.Timestamp(f"{year}-12-31")
        except (ValueError, IndexError):
            filter_start = None
            filter_end = None

    if filter_start is not None or filter_end is not None:
        time_period = (filter_start, filter_end)
    else:
        time_period = None
    
    # Mostrar informações sobre os torneios sendo computados
    with st.expander("📊 Torneios Computados neste Ranking", expanded=False):
        # Filtrar torneios pela categoria e período selecionados
        filtered_tournaments = tournaments.copy()
        
        if category != "Todas":
            filtered_tournaments = filtered_tournaments[filtered_tournaments['category'] == category]
        
        filtered_tournaments = filter_dataframe_by_period(
            filtered_tournaments, 'started_month_year', time_period
        )
        
        # Filtrar partidas para mostrar estatísticas
        filtered_matches = matches.copy()
        if category != "Todas":
            tournament_ids = filtered_tournaments['id'].tolist()
            filtered_matches = filtered_matches[filtered_matches['tournament_id'].isin(tournament_ids)]
        
        filtered_matches = filter_dataframe_by_period(
            filtered_matches, 'started_month_year', time_period
        )
        
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
    
    # Botão de cache removido daqui; refresh global no app
    
    # Debug: Mostrar informações sobre o filtro de período
    if time_period:
        start_date, end_date = time_period
        if start_date is not None and end_date is not None:
            st.info(
                f"📅 Filtrando dados entre: {start_date.strftime('%d/%m/%Y')} "
                f"e {end_date.strftime('%d/%m/%Y')}"
            )
        elif start_date is not None:
            st.info(f"📅 Filtrando dados a partir de: {start_date.strftime('%d/%m/%Y')}")
        elif end_date is not None:
            st.info(f"📅 Filtrando dados até: {end_date.strftime('%d/%m/%Y')}")
    
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
    tab_pontos, tab_glicko = st.tabs(["Ranking por Pontos", "Ranking Glicko-2"])
    
    with tab_pontos:
        st.subheader("Ranking por Pontos")
        
        # Substituir card de info por expander
        with st.expander("ℹ️ Como funciona o Ranking por Pontos?"):
            st.write("""
            O ranking por pontos segue o sistema dos Grand Slams de tênis:
            
            **Sistema de Pontuação:**
            - **Campeão:** 2.000 pontos
            - **Vice-campeão (perdedor da final):** 1.200 pontos
            - **Perdedor na semifinal:** 720 pontos
            - **Perdedor nas quartas de final:** 360 pontos
            - **Perdedor na primeira rodada:** 180 pontos
            
            **Torneios FINALS:**
            - Seguem a mesma estrutura, mas com menos rodadas
            - Final: Campeão (2.000) vs Vice-campeão (1.200)
            - Semifinal: 720 pontos (perdedor)
            - Quartas: 360 pontos (perdedor)
            
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

    with tab_glicko:
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