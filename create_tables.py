# create_tables.py
from app import app, db

with app.app_context():
    print("Criando todas as tabelas do banco de dados...")
    db.create_all()
    print("Tabelas criadas com sucesso!")