import streamlit as st
import sqlite3
import hashlib
import os
from PIL import Image
import io
import base64

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    return stored_password == hash_password(provided_password)

def init_db():
    """Inicializa o banco de dados se necessário"""
    conn = sqlite3.connect('challonge-scraper/database/database.sqlite')
    cursor = conn.cursor()
    
    # Criar tabela de administradores se não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Criar tabela de perfis de jogadores se não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_profiles (
        player_id INTEGER PRIMARY KEY,
        display_name TEXT,
        profile_image TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id)
    )
    ''')
    
    conn.commit()
    conn.close()

def login_page():
    """Página de login"""
    st.title("🔐 Área Administrativa")
    
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        conn = sqlite3.connect('challonge-scraper/database/database.sqlite')
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result and verify_password(result[0], password):
            st.session_state['admin_logged_in'] = True
            st.session_state['admin_username'] = username
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")
        
        conn.close()

def admin_page(matches, players, tournaments):
    """Página principal da área administrativa"""
    st.title("👨‍💼 Painel Administrativo")
    
    # Menu lateral
    menu = st.sidebar.selectbox(
        "Menu",
        ["Gerenciar Jogadores", "Configurações"]
    )
    
    if menu == "Gerenciar Jogadores":
        manage_players(players)
    elif menu == "Configurações":
        settings_page()

def manage_players(players):
    """Gerenciamento de jogadores"""
    st.header("👤 Gerenciar Jogadores")
    
    # Selecionar jogador
    player_id = st.selectbox(
        "Selecione um jogador",
        options=players['id'].tolist(),
        format_func=lambda x: players[players['id'] == x]['name'].iloc[0]
    )
    
    # Carregar informações atuais do jogador
    conn = sqlite3.connect('challonge-scraper/database/database.sqlite')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT display_name, profile_image 
    FROM player_profiles 
    WHERE player_id = ?
    ''', (player_id,))
    
    result = cursor.fetchone()
    current_display_name = result[0] if result else None
    current_image = result[1] if result else None
    
    # Formulário de edição
    new_display_name = st.text_input(
        "Nome de Exibição",
        value=current_display_name if current_display_name else players[players['id'] == player_id]['name'].iloc[0]
    )
    
    uploaded_file = st.file_uploader("Foto do Jogador", type=["jpg", "jpeg", "png"])
    
    if st.button("Salvar Alterações"):
        # Processar imagem
        image_data = None
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            # Redimensionar imagem para thumbnail
            image.thumbnail((200, 200))
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_data = base64.b64encode(buffered.getvalue()).decode()
        
        # Atualizar ou inserir dados
        cursor.execute('''
        INSERT OR REPLACE INTO player_profiles 
        (player_id, display_name, profile_image, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (player_id, new_display_name, image_data))
        
        conn.commit()
        st.success("Alterações salvas com sucesso!")
    
    # Exibir preview da imagem atual
    if current_image:
        st.image(base64.b64decode(current_image), caption="Foto atual", width=200)
    
    conn.close()

def settings_page():
    """Página de configurações"""
    st.header("⚙️ Configurações")
    
    # Criar novo administrador
    st.subheader("Criar Novo Administrador")
    new_username = st.text_input("Novo Usuário")
    new_password = st.text_input("Nova Senha", type="password")
    
    if st.button("Criar Administrador"):
        if new_username and new_password:
            conn = sqlite3.connect('challonge-scraper/database/database.sqlite')
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                INSERT INTO admins (username, password_hash)
                VALUES (?, ?)
                ''', (new_username, hash_password(new_password)))
                
                conn.commit()
                st.success("Administrador criado com sucesso!")
            except sqlite3.IntegrityError:
                st.error("Nome de usuário já existe")
            
            conn.close()
        else:
            st.error("Preencha todos os campos")

def display_admin_page(matches, players, tournaments):
    """Função principal para exibir a área administrativa"""
    # Inicializar banco de dados
    init_db()
    
    # Verificar se está logado
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False
    
    if st.session_state['admin_logged_in']:
        admin_page(matches, players, tournaments)
    else:
        login_page() 