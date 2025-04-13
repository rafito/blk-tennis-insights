import pandas as pd
import plotly.express as px
import streamlit as st

def get_player_stats(matches, player_id):
    """Calcula estatísticas do jogador"""
    player_matches = matches[
        (matches['winner_id'] == player_id) | 
        (matches['loser_id'] == player_id)
    ]
    
    total_matches = len(player_matches)
    wins = len(player_matches[player_matches['winner_id'] == player_id])
    losses = total_matches - wins
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
    
    # Títulos (vitórias em Round 4)
    titles = len(player_matches[
        (player_matches['winner_id'] == player_id) & 
        (player_matches['round'] == 4)
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
    
    round_counts = player_matches['round'].value_counts().sort_index()
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

def display_player_page(matches, players):
    """Exibe a página de análise de jogadores"""
    st.header("Análise de Jogadores")
    
    # Seleção do jogador
    player_names = players['name'].tolist()
    selected_player = st.selectbox("Selecione um jogador:", player_names)
    
    # Obter ID do jogador selecionado
    player_id = players[players['name'] == selected_player]['id'].iloc[0]
    
    # Estatísticas do jogador
    stats = get_player_stats(matches, player_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Jogos", stats['total_matches'])
    with col2:
        st.metric("Vitórias", stats['wins'])
    with col3:
        st.metric("Derrotas", stats['losses'])
    with col4:
        st.metric("Títulos", stats['titles'])
    
    # Gráfico de distribuição de rodadas
    st.subheader("Distribuição de Rodadas Alcançadas")
    round_dist = get_round_distribution(matches, player_id)
    fig = px.bar(x=round_dist.index, y=round_dist.values, 
                 labels={'x': 'Rodada', 'y': 'Quantidade'},
                 title=f"Distribuição de Rodadas - {selected_player}")
    st.plotly_chart(fig)
    
    # Head-to-Head
    st.subheader("Head-to-Head")
    opponent = st.selectbox("Selecione um oponente:", 
                           [p for p in player_names if p != selected_player])
    opponent_id = players[players['name'] == opponent]['id'].iloc[0]
    
    h2h = get_head_to_head(matches, player_id, opponent_id)
    
    if h2h['total_matches'] > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"Vitórias de {selected_player}", h2h['player1_wins'])
        with col2:
            st.metric(f"Vitórias de {opponent}", h2h['player2_wins'])
        
        # Gráfico de pizza do head-to-head
        fig = px.pie(values=[h2h['player1_wins'], h2h['player2_wins']],
                     names=[selected_player, opponent],
                     title=f"Head-to-Head: {selected_player} vs {opponent}")
        st.plotly_chart(fig)
    else:
        st.info("Não há histórico de jogos entre estes jogadores.") 