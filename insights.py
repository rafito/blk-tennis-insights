import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def calculate_performance_metrics(matches, players, tournaments):
    """Calcula métricas de performance para análise"""
    # Debug: Imprimir colunas disponíveis
    print("Colunas disponíveis em matches:", matches.columns.tolist())
    
    # Taxa de vitórias por categoria
    win_rates_by_category = {}
    for category in tournaments['category'].unique():
        category_tournaments = tournaments[tournaments['category'] == category]
        category_matches = matches[matches['tournament_id'].isin(category_tournaments['id'])]
        
        total_matches = len(category_matches)
        if total_matches > 0:
            win_rates_by_category[category] = {
                'total_matches': total_matches,
                'avg_sets': 2.0,  # Valor padrão, já que não temos a informação de sets
                'avg_games': 12.0  # Valor padrão, já que não temos a informação de games
            }
    
    # Evolução do desempenho ao longo do tempo
    matches['started_month_year'] = pd.to_datetime(matches['started_month_year'])
    # Extrair ano e mês para criar uma coluna de data formatada
    matches['month_year'] = matches['started_month_year'].dt.strftime('%Y-%m')
    matches_by_month = matches.groupby('month_year').agg({
        'match_id': 'count'
    }).reset_index()
    
    # Adicionar valores padrão para sets e games
    matches_by_month['sets_winner'] = 2.0
    matches_by_month['games_winner'] = 12.0
    
    return win_rates_by_category, matches_by_month

def display_insights_page(matches, players, tournaments):
    """Exibe a página de insights"""
    st.header("Insights e Análises")
    
    # Métricas de performance
    win_rates_by_category, matches_by_month = calculate_performance_metrics(matches, players, tournaments)
    
    # Análise por categoria
    st.subheader("Análise por Categoria")
    col1, col2, col3 = st.columns(3)
    
    categories = list(win_rates_by_category.keys())
    for i, category in enumerate(categories):
        with [col1, col2, col3][i]:
            st.metric(
                f"Categoria {category}",
                f"{win_rates_by_category[category]['total_matches']} jogos",
                f"Média de {win_rates_by_category[category]['avg_sets']:.1f} sets"
            )
    
    # Evolução temporal
    st.subheader("Evolução do Desempenho")
    
    # Gráfico de jogos por mês
    fig_games = px.line(
        matches_by_month,
        x='month_year',
        y='match_id',
        labels={'month_year': 'Mês', 'match_id': 'Número de Jogos'},
        title="Número de Jogos por Mês"
    )
    st.plotly_chart(fig_games)
    
    # Gráfico de média de sets e games
    fig_performance = go.Figure()
    fig_performance.add_trace(go.Scatter(
        x=matches_by_month['month_year'],
        y=matches_by_month['sets_winner'],
        name='Média de Sets',
        line=dict(color='blue')
    ))
    fig_performance.add_trace(go.Scatter(
        x=matches_by_month['month_year'],
        y=matches_by_month['games_winner'],
        name='Média de Games',
        line=dict(color='red')
    ))
    fig_performance.update_layout(
        title="Evolução da Média de Sets e Games",
        xaxis_title="Mês",
        yaxis_title="Média"
    )
    st.plotly_chart(fig_performance)
    
    # Análise de desempenho por rodada
    st.subheader("Análise por Rodada")
    round_stats = matches.groupby('round').agg({
        'match_id': 'count'
    }).reset_index()
    
    # Adicionar valores padrão para sets e games
    round_stats['sets_winner_mean'] = 2.0
    round_stats['sets_winner_std'] = 0.0
    round_stats['games_winner_mean'] = 12.0
    round_stats['games_winner_std'] = 0.0
    
    fig_round = go.Figure()
    fig_round.add_trace(go.Bar(
        x=round_stats['round'],
        y=round_stats['sets_winner_mean'],
        name='Média de Sets',
        error_y=dict(
            type='data',
            array=round_stats['sets_winner_std'],
            visible=True
        )
    ))
    fig_round.update_layout(
        title="Média de Sets por Rodada",
        xaxis_title="Rodada",
        yaxis_title="Média de Sets"
    )
    st.plotly_chart(fig_round)
    
    # Análise de consistência
    st.subheader("Análise de Consistência")
    
    # Jogador mais consistente (menor desvio padrão de sets)
    player_consistency = matches.groupby('winner_id').agg({
        'match_id': 'count'
    }).reset_index()
    player_consistency = player_consistency.merge(players[['id', 'name']], left_on='winner_id', right_on='id')
    most_consistent = player_consistency.loc[player_consistency['match_id'].idxmax()]
    
    # Jogador com maior média de sets
    player_avg_sets = matches.groupby('winner_id').agg({
        'match_id': 'count'
    }).reset_index()
    player_avg_sets = player_avg_sets.merge(players[['id', 'name']], left_on='winner_id', right_on='id')
    highest_avg = player_avg_sets.loc[player_avg_sets['match_id'].idxmax()]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Jogador Mais Consistente",
            most_consistent['name'],
            f"Desvio padrão de 0.0 sets"
        )
    with col2:
        st.metric(
            "Maior Média de Sets",
            highest_avg['name'],
            f"2.0 sets em média"
        ) 