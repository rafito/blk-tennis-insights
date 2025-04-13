# Instruções para Desenvolvimento da Aplicação Web - Dashboard BLK Tennis

## Visão Geral
Crie uma aplicação web em Python utilizando o banco de dados SQLite (`database.sqlite`) localizado na raiz do projeto. O objetivo é desenvolver um dashboard com informações detalhadas sobre jogadores, jogos e torneios da academia de tênis BLK Tennis.

## Estrutura do Banco de Dados

- **matches (view)**: informações dos jogos incluindo vencedor, perdedor, placar, rodada, torneio e saldo de sets.
- **players (view)**: informações dos jogadores.
- **tournaments (view)**: informações sobre os torneios, incluindo categorias (3ª classe, 4ª classe, 5ª classe).

## Funcionalidades

### 1. Página do Jogador

#### Informações do Jogador
- Histórico completo dos jogos, com opção de filtro por torneio.
- Número total de vitórias.
- Número total de derrotas.
- Número total de títulos (definido como vitórias em Round 4).
- Performance geral (percentual de vitórias).
- Estatísticas detalhadas de performance em torneios (frequência de rodada alcançada).
- Head-to-Head: possibilidade de selecionar outro jogador para comparação detalhada de resultados.

### 2. Rankings

Crie rankings baseados no método Glicko-2:

- Rankings separados por categoria (3ª classe, 4ª classe, 5ª classe).
- Rankings históricos completos e específicos para os últimos 12 e 24 meses.
- Utilize ajustes apropriados no algoritmo Glicko-2 considerando o baixo volume de dados disponíveis.
- Crie ranking por pontuação em vitórias dependendo da rodada seguindo o seguinte critério:
-- Vitória em round 4: 1000
-- Vitória em round 3: 650
-- Vitória em round 2: 400
-- Vitória em round 1: 200

### 3. Insights e Gráficos

- Desenvolva gráficos intuitivos para visualização rápida de insights (ex.: desempenho médio por rodada, evolução do ranking dos principais jogadores, taxa de vitórias por categoria).
- Sugira insights adicionais que ajudem a compreender melhor os dados e apoiar decisões estratégicas.

## Requisitos Técnicos

- **Tecnologia**: Python (Flask ou Streamlit recomendado pela simplicidade)
- **Banco de Dados**: SQLite (`database.sqlite`)
- **Hospedagem**: AWS (sugestão: EC2 simples ou serviço equivalente com publicação facilitada)
- **IDE sugerida**: Cursor IDE para automação e facilitação do desenvolvimento.

## Critérios de Aceitação

- Aplicação deve ser simples, funcional e intuitiva.
- Acesso fácil aos filtros por categoria e torneio.
- Visualização clara e objetiva das informações, rankings e gráficos.
- Aplicação deve estar pronta para ser facilmente publicada em ambiente AWS sem necessidade de grandes ajustes adicionais.

