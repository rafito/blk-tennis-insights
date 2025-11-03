# BLK Tennis Insights

Dashboard interativo para análise de dados de tênis da academia BLK Tennis.

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone este repositório:
```bash
git clone [URL_DO_REPOSITÓRIO]
cd blk-tennis-insights
```
python3 -m venv venv
source venv/bin/activate

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Execução

Para iniciar o dashboard, execute:
```bash
streamlit run app.py
```

O dashboard estará disponível em `http://localhost:8501`

## Estrutura do Projeto

- `app.py`: Aplicação principal do Streamlit
- `database.sqlite`: Banco de dados SQLite com os dados dos jogos, jogadores e torneios
- `requirements.txt`: Lista de dependências do projeto

## Funcionalidades

- Visão geral do sistema
- Análise detalhada de jogadores
- Rankings por categoria
- Insights e análises estatísticas 

## O que fazer quando tiver torneio novo?

```bash
cd challonge-scraper

php artisan challonge:sync-all
ou
php artisan challonge:sync-all --reset-db

php artisan challonge:merge-participants --max-group-size=2

cd ..
cp challonge-scraper/database/database.sqlite .
```