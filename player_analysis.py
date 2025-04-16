import pandas as pd
import plotly.express as px
import streamlit as st

def is_finals_tournament(tournament_name):
    """Verifica se é um torneio FINALS"""
    return 'FINALS' in str(tournament_name).upper()

def get_round_name(round_number, tournament_name):
    """Retorna o nome da fase baseado no número e tipo do torneio"""
    if is_finals_tournament(tournament_name):
        round_names = {
            1: 'Quartas de Final',
            2: 'Semifinal',
            3: 'Final'
        }
    else:
        round_names = {
            1: 'Primeira',
            2: 'Quartas de Final',
            3: 'Semifinal',
            4: 'Final'
        }
    return round_names.get(round_number, f'Fase {round_number}')

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
    round_order = ['Primeira', 'Quartas de Final', 'Semifinal', 'Final']
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
    
    # Calcula o número de sets jogados para cada partida
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
    
    # Insight sobre maior rivalidade
    # Encontra o adversário contra quem mais jogou
    rivals = pd.concat([
        player_matches[player_matches['winner_id'] == player_id]['loser_id'],
        player_matches[player_matches['loser_id'] == player_id]['winner_id']
    ]).value_counts()
    
    if not rivals.empty and rivals.iloc[0] >= 2:  # Só mostra se tiver pelo menos 2 jogos
        rival_id = rivals.index[0]
        rival_matches = player_matches[
            ((player_matches['winner_id'] == player_id) & (player_matches['loser_id'] == rival_id)) |
            ((player_matches['winner_id'] == rival_id) & (player_matches['loser_id'] == player_id))
        ]
        wins = len(rival_matches[rival_matches['winner_id'] == player_id])
        total = len(rival_matches)
        rival_name = matches[matches['winner_id'] == rival_id]['winner_name'].iloc[0]
        
        insights.append({
            'icon': '⚔️',
            'title': 'Maior Rivalidade',
            'text': f"{rival_name}: {total} jogos, {wins} vitória{'s' if wins != 1 else ''} ({(wins/total*100):.1f}% de aproveitamento)"
        })
    
    # Insight sobre títulos e finais
    finals_played = len(player_matches[
        player_matches.apply(lambda x: is_final_round(x['round'], x['tournament_name']), axis=1)
    ])
    if finals_played > 0:
        win_rate_finals = (stats['titles'] / finals_played) * 100
        insights.append({
            'icon': '🏆',
            'title': 'Desempenho em Finais',
            'text': f"Disputou {finals_played} {'finais' if finals_played > 1 else 'final'}, " +
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
        # Ordem das fases do melhor para o pior resultado
        round_order = ['Final', 'Semifinal', 'Quartas de Final', 'Primeira']
        
        # Conta quantas vezes alcançou cada fase
        round_counts = player_matches['round_name'].value_counts()
        
        # Encontra a melhor fase alcançada que tenha pelo menos uma ocorrência
        best_rounds = []
        for round_name in round_order:
            if round_name in round_counts.index and round_counts[round_name] > 0:
                count = round_counts[round_name]
                best_rounds.append(f"{count}x {round_name}")
                if len(best_rounds) >= 2:  # Pega no máximo as 2 melhores fases
                    break
        
        if best_rounds:
            insights.append({
                'icon': '🎯',
                'title': 'Melhores Resultados',
                'text': f"Alcançou {' e '.join(best_rounds)}"
            })

    # Insight sobre jogos duros (terceiro set)
    third_set_matches = player_matches[player_matches['sets_played'] == 3]
    if not third_set_matches.empty:
        total_third_sets = len(third_set_matches)
        wins_third_sets = len(third_set_matches[third_set_matches['winner_id'] == player_id])
        win_rate_third_sets = (wins_third_sets / total_third_sets) * 100
        
        insights.append({
            'icon': '💪',
            'title': 'Jogos Duros',
            'text': f"Disputou {total_third_sets} {'jogos' if total_third_sets > 1 else 'jogo'} no terceiro set, " +
                   f"vencendo {wins_third_sets} ({win_rate_third_sets:.1f}% de aproveitamento)"
        })
    
    return insights

def get_player_opponents(matches, player_id):
    """Retorna lista de IDs dos jogadores que já enfrentaram o jogador selecionado"""
    # Encontra todos os oponentes nas partidas onde o jogador foi vencedor ou perdedor
    opponents = pd.concat([
        matches[matches['winner_id'] == player_id]['loser_id'],
        matches[matches['loser_id'] == player_id]['winner_id']
    ]).unique()
    
    return opponents

def display_player_page(matches, players, shared_player_id=None):
    """Exibe a página de análise de jogadores"""
    st.header("👤 Análise de Jogadores")
    
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
        "🔍 Selecione um jogador:", 
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
        st.error("❌ Jogador não encontrado no banco de dados.")
        return
    
    player_id = player_df['id'].iloc[0]
    
    with st.spinner('Carregando estatísticas do jogador...'):
        # Estatísticas do jogador
        stats = get_player_stats(matches, player_id)
        
        # Métricas principais
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("🎾 Total de Jogos", stats['total_matches'])
        with col2:
            st.metric("✅ Vitórias", stats['wins'])
        with col3:
            st.metric("❌ Derrotas", stats['losses'])
        with col4:
            st.metric("📈 Taxa de Vitórias", f"{stats['win_rate']:.1f}%")
        with col5:
            st.metric("🏆 Títulos", stats['titles'])
        
        # Seção de Insights
        st.subheader("💡 Insights")
        insights = get_player_insights(matches, player_id, stats)
        
        if insights:
            cols = st.columns(2)  # Organiza os insights em duas colunas
            for i, insight in enumerate(insights):
                with cols[i % 2]:
                    st.markdown(
                        f"""
                        {insight['icon']} **{insight['title']}**  
                        {insight['text']}
                        """
                    )
        else:
            st.info("📝 Ainda não há dados suficientes para gerar insights.")
    
    with st.spinner('Carregando distribuição de rodadas...'):
        # Gráfico de distribuição de rodadas
        st.subheader("Distribuição de Rodadas Alcançadas")
        round_dist = get_round_distribution(matches, player_id)
        
        # Converte os números das rodadas para nomes descritivos no gráfico
        round_dist.index = [get_round_name(r, None) for r in round_dist.index]
        
        # Cria o gráfico com mais customizações
        fig = px.bar(
            y=round_dist.index, 
            x=round_dist.values,
            orientation='h',
            labels={'y': 'Fase', 'x': 'Quantidade'},
            title=None
        )
        
        # Customiza o layout do gráfico
        fig.update_layout(
            plot_bgcolor='white',
            showlegend=False,
            yaxis=dict(
                title_font=dict(size=14),
                tickfont=dict(size=12),
                showgrid=False,
                autorange='reversed'  # Inverte a ordem para manter a sequência lógica
            ),
            xaxis=dict(
                title_font=dict(size=14),
                tickfont=dict(size=12),
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                zeroline=True,
                zerolinewidth=1,
                zerolinecolor='rgba(128, 128, 128, 0.2)'
            ),
            bargap=0.3
        )
        
        # Adiciona os valores nas barras
        fig.update_traces(
            text=round_dist.values,
            textposition='outside',
            textfont=dict(size=14),
            marker_color='#1f77b4',  # Cor azul mais profissional
            hovertemplate="<b>%{y}</b><br>" +
                         "Quantidade: %{x}<br>" +
                         "<extra></extra>"  # Remove texto adicional no hover
        )
        
        # Ajusta os limites do eixo X para acomodar os números
        max_value = round_dist.max()
        fig.update_layout(xaxis_range=[0, max_value * 1.2])
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Adiciona botão de compartilhar
    share_url = f"{st.session_state.get('host', 'https://blk-tennis-insights.streamlit.app')}?player_id={player_id}&page=Análise de Jogadores"
    
    st.markdown("##### 📤 Link para compartilhar:")
    st.code(share_url, language=None)
    
    # Histórico de Jogos
    st.subheader("📅 Histórico de Jogos")
    
    # Filtros para o histórico
    col1, col2, col3 = st.columns(3)
    
    with col1:
        result_filter = st.multiselect(
            "🎯 Filtrar por resultado:",
            options=['Vitória', 'Derrota'],
            default=['Vitória', 'Derrota']
        )
    
    with col2:
        tournament_categories = matches['tournament_category'].unique()
        category_filter = st.multiselect(
            "🏆 Filtrar por categoria:",
            options=tournament_categories,
            default=tournament_categories
        )
    
    with col3:
        all_rounds = []
        for tournament_name in matches['tournament_name'].unique():
            if is_finals_tournament(tournament_name):
                all_rounds.extend(['Quartas de Final', 'Semifinal', 'Final'])
            else:
                all_rounds.extend(['Primeira', 'Quartas de Final', 'Semifinal', 'Final'])
        round_filter = st.multiselect(
            "🔄 Filtrar por fase:",
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
                # Função para estilizar as linhas baseado no resultado
                def highlight_results(row):
                    if row['Resultado'] == 'Vitória':
                        return ['background-color: #e6ffe6' for _ in row]
                    else:  # Derrota
                        return ['background-color: #ffe6e6' for _ in row]
                
                # Aplica a estilização e mostra o DataFrame
                st.dataframe(
                    filtered_df.style.apply(highlight_results, axis=1),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Nenhum jogo encontrado com os filtros selecionados.")
        else:
            st.info("Nenhum histórico de jogos encontrado para este jogador.")
    
    # Head-to-Head
    st.subheader("🤼 Head-to-Head")
    
    # Obtém lista de oponentes que já jogaram contra o jogador selecionado
    opponent_ids = get_player_opponents(matches, player_id)
    opponent_names = players[players['id'].isin(opponent_ids)]['name'].tolist()
    
    if not opponent_names:
        st.info("Este jogador ainda não tem confrontos registrados.")
    else:
        # Seleção do oponente apenas entre aqueles que já jogaram contra o jogador selecionado
        opponent = st.selectbox(
            "🔄 Selecione um jogador para comparar:",
            [""] + sorted(opponent_names)
        )
    
    if opponent:
        opponent_df = players[players['name'] == opponent]
        if not opponent_df.empty:
            opponent_id = opponent_df['id'].iloc[0]
            
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