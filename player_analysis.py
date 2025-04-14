import pandas as pd
import plotly.express as px
import streamlit as st

def is_finals_tournament(tournament_name):
    """Verifica se é um torneio FINALS"""
    return 'FINALS' in str(tournament_name).upper()

def get_round_name(round_number, tournament_name):
    """Retorna o nome da rodada baseado no número e tipo do torneio"""
    if is_finals_tournament(tournament_name):
        round_names = {
            1: 'Quartas de Final',
            2: 'Semifinal',
            3: 'Final'
        }
    else:
        round_names = {
            1: 'Primeira Rodada',
            2: 'Quartas de Final',
            3: 'Semifinal',
            4: 'Final'
        }
    return round_names.get(round_number, f'Rodada {round_number}')

def is_final_round(round_number, tournament_name):
    """Verifica se é a rodada final do torneio"""
    return (is_finals_tournament(tournament_name) and round_number == 3) or \
           (not is_finals_tournament(tournament_name) and round_number == 4)

def get_player_stats(matches, player_id):
    """Calcula estatísticas do jogador"""
    # Garantir que matches é um DataFrame válido
    if matches is None or matches.empty:
        return {
            'total_matches': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'titles': 0
        }

    # Filtrar partidas do jogador com verificação de valores nulos
    player_matches = matches[
        (matches['winner_id'].notna() & matches['loser_id'].notna()) &
        ((matches['winner_id'] == player_id) | (matches['loser_id'] == player_id))
    ]
    
    if player_matches.empty:
        return {
            'total_matches': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'titles': 0
        }
    
    total_matches = len(player_matches)
    wins = len(player_matches[player_matches['winner_id'] == player_id])
    losses = total_matches - wins
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
    
    # Títulos (vitórias na rodada final)
    titles = len(player_matches[
        (player_matches['winner_id'] == player_id) & 
        player_matches.apply(lambda x: is_final_round(x['round'], x['tournament_name']), axis=1)
    ])
    
    return {
        'total_matches': total_matches,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'titles': titles
    }

def get_round_distribution(matches, player_id):
    """Calcula distribuição de rodadas alcançadas"""
    player_matches = matches[
        (matches['winner_id'] == player_id) | 
        (matches['loser_id'] == player_id)
    ]
    
    # Agrupa por torneio e rodada para evitar duplicatas
    tournament_rounds = player_matches.groupby(['tournament_name', 'round']).first().reset_index()
    
    # Mapeia as rodadas para nomes descritivos considerando o tipo de torneio
    round_counts = {}
    for _, row in tournament_rounds.iterrows():
        round_name = get_round_name(row['round'], row['tournament_name'])
        round_counts[round_name] = round_counts.get(round_name, 0) + 1
    
    # Converte para Series e ordena pela ordem natural das rodadas
    round_order = ['Primeira Rodada', 'Quartas de Final', 'Semifinal', 'Final']
    round_counts = pd.Series(round_counts)
    round_counts = round_counts.reindex(round_order).fillna(0)
    
    return round_counts

def get_head_to_head(matches, player1_id, player2_id):
    """Calcula estatísticas head-to-head entre dois jogadores"""
    h2h_matches = matches[
        ((matches['winner_id'] == player1_id) & (matches['loser_id'] == player2_id)) |
        ((matches['winner_id'] == player2_id) & (matches['loser_id'] == player1_id))
    ]
    
    player1_wins = len(h2h_matches[h2h_matches['winner_id'] == player1_id])
    player2_wins = len(h2h_matches[h2h_matches['winner_id'] == player2_id])
    
    return {
        'total_matches': len(h2h_matches),
        'player1_wins': player1_wins,
        'player2_wins': player2_wins
    }

def get_match_history(matches, players, player_id):
    """Obtém o histórico de jogos de um jogador com informações detalhadas"""
    # Verificar se temos dados válidos
    if matches is None or matches.empty or players is None or players.empty:
        return pd.DataFrame()

    # Filtra partidas do jogador com verificação de valores nulos
    player_matches = matches[
        (matches['match_id'].notna()) &
        (matches['winner_id'].notna() & matches['loser_id'].notna()) &
        ((matches['winner_id'] == player_id) | (matches['loser_id'] == player_id))
    ].copy()
    
    if player_matches.empty:
        return pd.DataFrame()
    
    # Adiciona nome do oponente com verificação de valores nulos
    player_matches['opponent_id'] = player_matches.apply(
        lambda x: x['loser_id'] if x['winner_id'] == player_id else x['winner_id'],
        axis=1
    )
    
    # Criar um dicionário de nomes de jogadores para evitar problemas de índice
    player_names = players.set_index('id')['name'].to_dict()
    player_matches['opponent_name'] = player_matches['opponent_id'].map(player_names)
    
    # Adiciona resultado e placar formatado
    player_matches['result'] = player_matches.apply(
        lambda x: 'Vitória' if x['winner_id'] == player_id else 'Derrota',
        axis=1
    )
    
    # Formata o placar sempre com o número maior primeiro
    def format_score(row):
        try:
            if pd.isna(row['score']):
                return "N/A"
            score_str = str(row['score']).strip('"')
            if not score_str or score_str == 'nan':
                return "N/A"
            sets = [int(s) for s in score_str.split('-')]
            return f"{max(sets)}x{min(sets)}"
        except (ValueError, AttributeError):
            return "N/A"
    
    # Aplica a formatação do placar
    player_matches['score_formatted'] = player_matches.apply(format_score, axis=1)
    
    # Calcula o número real de sets jogados baseado no placar
    def calculate_sets_played(score):
        try:
            if pd.isna(score):
                return 0
            score_str = str(score).strip('"')
            if not score_str or score_str == 'nan':
                return 0
            sets = [int(s) for s in score_str.split('-')]
            return sum(sets)
        except (ValueError, AttributeError):
            return 0
    
    player_matches['sets_played'] = player_matches['score'].apply(calculate_sets_played)
    
    # Mapeia as rodadas para nomes mais descritivos com verificação de valores nulos
    player_matches['round_name'] = player_matches.apply(
        lambda x: get_round_name(x['round'], x['tournament_name']) if pd.notna(x['round']) else 'N/A',
        axis=1
    )
    
    # Adiciona informações do torneio
    player_matches['tournament_info'] = player_matches.apply(
        lambda x: f"{x['tournament_name'] or 'N/A'} ({x['tournament_category'] or 'N/A'})",
        axis=1
    )
    
    # Ordena por data do torneio se disponível
    if 'started_month_year' in player_matches.columns:
        player_matches['tournament_date'] = pd.to_datetime(
            player_matches['started_month_year'],
            format='%m/%Y',
            errors='coerce'
        )
        player_matches = player_matches.sort_values('tournament_date', ascending=False)
        player_matches['tournament_date'] = player_matches['tournament_date'].dt.strftime('%d/%m/%Y')
    
    # Seleciona e renomeia as colunas para exibição
    display_columns = {
        'tournament_date': 'Data',
        'tournament_info': 'Torneio',
        'round_name': 'Fase',
        'opponent_name': 'Adversário',
        'result': 'Resultado',
        'score_formatted': 'Placar',
        'sets_played': 'Sets Jogados'
    }
    
    # Retorna apenas as colunas que existem no DataFrame
    available_columns = [col for col in display_columns.keys() if col in player_matches.columns]
    result_df = player_matches[available_columns].rename(columns=display_columns)
    
    # Preenche valores nulos
    result_df = result_df.fillna('N/A')
    
    return result_df

def get_player_insights(matches, player_id, stats):
    """Gera insights sobre o desempenho do jogador"""
    insights = []
    
    # Filtrar partidas do jogador
    player_matches = matches[
        (matches['winner_id'] == player_id) | 
        (matches['loser_id'] == player_id)
    ].copy()  # Adicionado .copy() para evitar SettingWithCopyWarning
    
    if player_matches.empty:
        return insights
    
    # Adiciona nome da rodada
    player_matches['round_name'] = player_matches.apply(
        lambda x: get_round_name(x['round'], x['tournament_name']),
        axis=1
    )
    
    # Insight sobre títulos e finais
    finals_played = len(player_matches[
        player_matches.apply(lambda x: is_final_round(x['round'], x['tournament_name']), axis=1)
    ])
    if finals_played > 0:
        win_rate_finals = (stats['titles'] / finals_played) * 100
        insights.append({
            'icon': '🏆',
            'title': 'Desempenho em Finais',
            'text': f"Disputou {finals_played} final{'is' if finals_played > 1 else ''}, " +
                   f"vencendo {stats['titles']} ({win_rate_finals:.1f}% de aproveitamento em finais)"
        })
    
    # Insight sobre sequência atual
    current_streak = 0
    max_streak = 0
    current_type = None
    
    for _, match in player_matches.sort_values('started_month_year', ascending=True).iterrows():
        is_victory = match['winner_id'] == player_id
        
        if current_type is None:
            current_type = 'vitórias' if is_victory else 'derrotas'
            current_streak = 1
        elif (is_victory and current_type == 'vitórias') or (not is_victory and current_type == 'derrotas'):
            current_streak += 1
        else:
            if current_type == 'vitórias' and current_streak > max_streak:
                max_streak = current_streak
            current_type = 'vitórias' if is_victory else 'derrotas'
            current_streak = 1
    
    if current_streak > 2:
        insights.append({
            'icon': '🔥' if current_type == 'vitórias' else '📉',
            'title': 'Sequência Atual',
            'text': f"Está em sequência de {current_streak} {current_type} consecutivas"
        })
    
    # Insight sobre aproveitamento por categoria
    category_stats = {}
    for category in player_matches['tournament_category'].unique():
        category_matches = player_matches[player_matches['tournament_category'] == category]
        wins = len(category_matches[category_matches['winner_id'] == player_id])
        total = len(category_matches)
        win_rate = (wins / total * 100) if total > 0 else 0
        category_stats[category] = {'wins': wins, 'total': total, 'win_rate': win_rate}
    
    best_category = max(category_stats.items(), key=lambda x: x[1]['win_rate'])
    if best_category[1]['total'] >= 3:  # Só mostra se tiver pelo menos 3 jogos
        insights.append({
            'icon': '📈',
            'title': 'Melhor Categoria',
            'text': f"Maior aproveitamento na categoria {best_category[0]}: " +
                   f"{best_category[1]['win_rate']:.1f}% ({best_category[1]['wins']}/{best_category[1]['total']})"
        })
    
    # Insight sobre fases mais alcançadas
    if not player_matches['round_name'].empty:
        most_reached_round = player_matches['round_name'].mode().iloc[0]
        round_count = len(player_matches[player_matches['round_name'] == most_reached_round])
        if round_count > 2:
            insights.append({
                'icon': '🎯',
                'title': 'Fase mais Frequente',
                'text': f"Alcançou a fase de {most_reached_round} em {round_count} torneios"
            })
    
    return insights

def display_player_page(matches, players, shared_player_id=None):
    """Exibe a página de análise de jogadores"""
    st.header("Análise de Jogadores")
    
    # Seleção do jogador com opção vazia inicial
    player_names = [""] + sorted(players['name'].tolist())
    
    # Se tiver um jogador compartilhado, seleciona ele pelo ID
    default_index = 0
    if shared_player_id and shared_player_id.isdigit():
        player_id = int(shared_player_id)
        player_df = players[players['id'] == player_id]
        if not player_df.empty:
            player_name = player_df['name'].iloc[0]
            if player_name in player_names:
                default_index = player_names.index(player_name)
    
    selected_player = st.selectbox(
        "Selecione um jogador:", 
        player_names,
        index=default_index
    )
    
    # Só mostra as análises se um jogador for selecionado
    if not selected_player:
        st.info("👆 Selecione um jogador acima para ver suas estatísticas")
        return
        
    # Obter ID do jogador selecionado
    player_df = players[players['name'] == selected_player]
    if player_df.empty:
        st.error("Jogador não encontrado no banco de dados.")
        return
    
    player_id = player_df['id'].iloc[0]
    
    with st.spinner('Carregando estatísticas do jogador...'):
        # Estatísticas do jogador
        stats = get_player_stats(matches, player_id)
        
        # Métricas principais
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total de Jogos", stats['total_matches'])
        with col2:
            st.metric("Vitórias", stats['wins'])
        with col3:
            st.metric("Derrotas", stats['losses'])
        with col4:
            st.metric("Taxa de Vitórias", f"{stats['win_rate']:.1f}%")
        with col5:
            st.metric("Títulos", stats['titles'])
        
        # Seção de Insights
        st.subheader("📊 Insights")
        insights = get_player_insights(matches, player_id, stats)
        
        if insights:
            cols = st.columns(2)  # Organiza os insights em duas colunas
            for i, insight in enumerate(insights):
                with cols[i % 2]:
                    st.markdown(
                        f"""
                        <div style='
                            background-color: #f0f2f6;
                            padding: 15px;
                            border-radius: 5px;
                            margin-bottom: 10px;
                        '>
                            <div style='font-size: 1.1em; margin-bottom: 5px;'>
                                {insight['icon']} <strong>{insight['title']}</strong>
                            </div>
                            <div style='color: #666;'>
                                {insight['text']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("Ainda não há dados suficientes para gerar insights.")
    
    with st.spinner('Carregando distribuição de rodadas...'):
        # Gráfico de distribuição de rodadas
        st.subheader("Distribuição de Rodadas Alcançadas")
        round_dist = get_round_distribution(matches, player_id)
        
        # Converte os números das rodadas para nomes descritivos no gráfico
        round_dist.index = [get_round_name(r, None) for r in round_dist.index]
        
        fig = px.bar(x=round_dist.index, y=round_dist.values, 
                     labels={'x': 'Fase', 'y': 'Quantidade'},
                     title=f"Distribuição de Fases - {selected_player}")
        st.plotly_chart(fig)
    
    # Adiciona botão de compartilhar
    share_url = f"{st.session_state.get('host', 'https://blk-tennis-insights.streamlit.app')}?player_id={player_id}&page=Análise de Jogadores"
    
    st.markdown("##### 📤 Link para compartilhar:")
    st.code(share_url, language=None)
    
    # Histórico de Jogos
    st.subheader("Histórico de Jogos")
    
    # Filtros para o histórico
    col1, col2, col3 = st.columns(3)
    
    with col1:
        result_filter = st.multiselect(
            "Filtrar por resultado:",
            options=['Vitória', 'Derrota'],
            default=['Vitória', 'Derrota']
        )
    
    with col2:
        tournament_categories = matches['tournament_category'].unique()
        category_filter = st.multiselect(
            "Filtrar por categoria:",
            options=tournament_categories,
            default=tournament_categories
        )
    
    with col3:
        # Lista todas as fases possíveis
        all_rounds = []
        for tournament_name in matches['tournament_name'].unique():
            if is_finals_tournament(tournament_name):
                all_rounds.extend(['Quartas de Final', 'Semifinal', 'Final'])
            else:
                all_rounds.extend(['Primeira Rodada', 'Quartas de Final', 'Semifinal', 'Final'])
        round_filter = st.multiselect(
            "Filtrar por fase:",
            options=sorted(list(set(all_rounds))),
            default=sorted(list(set(all_rounds)))
        )
    
    with st.spinner('Carregando histórico de jogos...'):
        # Filtra as partidas antes de passar para get_match_history
        filtered_matches = matches[
            matches['tournament_category'].isin(category_filter)
        ].copy()
        
        # Obtém o histórico de jogos com os dados filtrados
        match_history = get_match_history(filtered_matches, players, player_id)
        
        if not match_history.empty:
            # Aplica os filtros no DataFrame antes de estilizar
            filtered_df = match_history[
                (match_history['Resultado'].isin(result_filter)) &
                (match_history['Fase'].isin(round_filter))
            ]
            
            if not filtered_df.empty:
                # Aplica a estilização no DataFrame filtrado
                def style_match_history(df):
                    def row_style(row):
                        color = 'background-color: #FFB6C1' if row['Resultado'] == 'Derrota' else ''
                        return [color] * len(row)
                    
                    return df.style.apply(row_style, axis=1)
                
                styled_df = style_match_history(filtered_df)
                
                # Exibe o histórico em uma tabela com estilo
                st.dataframe(
                    styled_df,
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Nenhum jogo encontrado com os filtros selecionados.")
        else:
            st.info("Nenhum histórico de jogos encontrado para este jogador.")
    
    # Head-to-Head
    st.subheader("Head-to-Head")
    
    # Encontrar todos os oponentes que já jogaram contra o jogador selecionado
    opponents_ids = pd.concat([
        matches[matches['winner_id'] == player_id]['loser_id'],
        matches[matches['loser_id'] == player_id]['winner_id']
    ]).unique()
    
    # Converter IDs para nomes e ordenar
    opponents_names = [""] + sorted(players[players['id'].isin(opponents_ids)]['name'].tolist())
    
    opponent = st.selectbox("Selecione um oponente:", opponents_names)
    
    if opponent:
        opponent_df = players[players['name'] == opponent]
        if opponent_df.empty:
            st.error("Oponente não encontrado no banco de dados.")
            return
            
        opponent_id = opponent_df['id'].iloc[0]
        
        with st.spinner('Carregando head-to-head...'):
            h2h = get_head_to_head(matches, player_id, opponent_id)
            
            if h2h['total_matches'] > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(f"Total de Jogos", h2h['total_matches'])
                with col2:
                    st.metric(f"Vitórias de {selected_player}", h2h['player1_wins'])
                with col3:
                    st.metric(f"Vitórias de {opponent}", h2h['player2_wins'])
                
                # Gráfico de pizza do head-to-head
                fig = px.pie(values=[h2h['player1_wins'], h2h['player2_wins']],
                             names=[selected_player, opponent],
                             title=f"Head-to-Head: {selected_player} vs {opponent}")
                st.plotly_chart(fig)
                
                # Histórico de confrontos diretos
                st.subheader(f"Histórico de Jogos: {selected_player} vs {opponent}")
                h2h_matches = matches[
                    ((matches['winner_id'] == player_id) & (matches['loser_id'] == opponent_id)) |
                    ((matches['winner_id'] == opponent_id) & (matches['loser_id'] == player_id))
                ]
                h2h_history = get_match_history(h2h_matches, players, player_id)
                st.dataframe(h2h_history, hide_index=True, use_container_width=True)
            else:
                st.info("Não há histórico de jogos entre estes jogadores.") 