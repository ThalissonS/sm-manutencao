import os
import io
from functools import wraps
from datetime import date, datetime, timedelta 
from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship, joinedload
from sqlalchemy import Integer, String, Text, Float, Date, or_, ForeignKey
import pandas as pd

# --- Configuração Inicial ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave-padrao-para-teste-local-insegura')
app.permanent_session_lifetime = timedelta(days=7)

# =======================================================================
# MUDANÇA PRINCIPAL: LÓGICA DE CONEXÃO COM O BANCO DE DADOS
# =======================================================================
# Procura pela variável de ambiente DATABASE_URL. Se não achar, usa um SQLite local.
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Pequeno ajuste para compatibilidade com o SQLAlchemy
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Se estivermos em produção (no Render), usará a URL do PostgreSQL.
# Se estivermos localmente sem a URL configurada, usará um arquivo SQLite.
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or f'sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance/local.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Estrutura do Banco de Dados ---
class Maquina(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    serie: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    manutencoes = relationship("Manutencao", back_populates="maquina", cascade="all, delete-orphan")
    def __init__(self, nome, serie): self.nome, self.serie = nome, serie

class Peca(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    def __init__(self, nome): self.nome = nome

class Solicitante(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    manutencoes = relationship("Manutencao", back_populates="solicitante")
    def __init__(self, nome): self.nome = nome

class Responsavel(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    manutencoes = relationship("Manutencao", back_populates="responsavel")
    def __init__(self, nome): self.nome = nome

class PecaUtilizada(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quantidade: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    manutencao_id: Mapped[int] = mapped_column(ForeignKey("manutencao.id"), nullable=False)
    peca_id: Mapped[int] = mapped_column(ForeignKey("peca.id"), nullable=False)
    manutencao = relationship("Manutencao", back_populates="pecas_utilizadas")
    peca = relationship("Peca")
    def __init__(self, quantidade, peca_id): self.quantidade, self.peca_id = quantidade, peca_id

class Manutencao(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquina.id"), nullable=False)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("solicitante.id"), nullable=False)
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsavel.id"), nullable=False)
    maquina = relationship("Maquina", back_populates="manutencoes")
    solicitante = relationship("Solicitante", back_populates="manutencoes")
    responsavel = relationship("Responsavel", back_populates="manutencoes")
    pecas_utilizadas = relationship("PecaUtilizada", back_populates="manutencao", cascade="all, delete-orphan")
    def __init__(self, data, descricao, valor, maquina_id, solicitante_id, responsavel_id):
        self.data, self.descricao, self.valor, self.maquina_id, self.solicitante_id, self.responsavel_id = data, descricao, valor, maquina_id, solicitante_id, responsavel_id

# --- Autenticação ---
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session: return redirect(url_for('index'))
    erro = None
    if request.method == 'POST':
        app_user, app_password = os.environ.get('APP_USER'), os.environ.get('APP_PASSWORD')
        if request.form['username'] == app_user and request.form['password'] == app_password:
            session['logged_in'], session.permanent = True, True
            return redirect(url_for('index'))
        else: erro = 'Usuário ou senha inválidos.'
    return render_template('login.html', erro=erro)
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- Rotas da Aplicação ---
@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

# --- ROTAS DE API ---
def create_crud_routes(model_class, route_name):
    plural_name = route_name
    singular_name = route_name[:-1]
    @app.route(f'/api/{plural_name}', methods=['GET', 'POST'], endpoint=f'handle_{plural_name}')
    @requires_auth
    def handle_list_and_create():
        if request.method == 'GET':
            items = db.session.execute(db.select(model_class).order_by(model_class.nome)).scalars().all()
            return jsonify([{'id': item.id, 'nome': item.nome} for item in items])
        elif request.method == 'POST':
            dados = request.get_json()
            if not dados or not dados.get('nome'): return jsonify({'erro': 'O nome é obrigatório'}), 400
            new_item = model_class(nome=dados['nome'])
            db.session.add(new_item)
            try:
                db.session.commit()
                return jsonify({'id': new_item.id, 'nome': new_item.nome}), 201
            except Exception:
                db.session.rollback(); return jsonify({'erro': f'Erro ao salvar. O valor já pode existir.'}), 500
        return jsonify({'erro': 'Método não permitido'}), 405
    @app.route(f'/api/{singular_name}/<int:id>', methods=['PUT', 'DELETE'], endpoint=f'handle_{singular_name}')
    @requires_auth
    def handle_item(id):
        item = db.session.get(model_class, id)
        if not item: return jsonify({'erro': 'Item não encontrado'}), 404
        if request.method == 'PUT':
            dados = request.get_json()
            if not dados or not dados.get('nome'): return jsonify({'erro': 'O nome é obrigatório'}), 400
            item.nome = dados['nome']
            try:
                db.session.commit()
                return jsonify({'id': item.id, 'nome': item.nome})
            except Exception:
                db.session.rollback(); return jsonify({'erro': 'Erro ao atualizar. O valor já pode existir.'}), 500
        elif request.method == 'DELETE':
            try:
                db.session.delete(item); db.session.commit()
                return jsonify({'mensagem': 'Item excluído com sucesso!'})
            except Exception:
                db.session.rollback(); return jsonify({'erro': 'Não foi possível excluir este item, pois ele está em uso em um ou mais registros de manutenção.'}), 409
        return jsonify({'erro': 'Método não permitido'}), 405

create_crud_routes(Solicitante, 'solicitantes')
create_crud_routes(Responsavel, 'responsaveis')
create_crud_routes(Peca, 'pecas')

@app.route('/api/maquinas', methods=['GET', 'POST'])
@requires_auth
def handle_maquinas():
    if request.method == 'GET':
        maquinas = db.session.execute(db.select(Maquina).order_by(Maquina.nome)).scalars().all()
        return jsonify([{'id': m.id, 'nome': m.nome, 'serie': m.serie} for m in maquinas])
    elif request.method == 'POST':
        dados = request.get_json()
        if not dados or not dados.get('serie') or not dados.get('nome'): return jsonify({'erro': 'Nome e Série da máquina são obrigatórios'}), 400
        nova_maquina = Maquina(nome=dados['nome'], serie=dados['serie'])
        db.session.add(nova_maquina)
        try:
            db.session.commit()
            return jsonify({'id': nova_maquina.id, 'nome': nova_maquina.nome, 'serie': nova_maquina.serie}), 201
        except Exception:
            db.session.rollback(); return jsonify({'erro': 'Erro ao salvar a máquina. A série já pode existir.'}), 500
    return jsonify({'erro': 'Método não permitido'}), 405

@app.route('/api/maquina/<int:id>', methods=['PUT', 'DELETE'])
@requires_auth
def handle_maquina(id):
    maquina = db.session.get(Maquina, id)
    if not maquina: return jsonify({'erro': 'Máquina não encontrada'}), 404
    if request.method == 'PUT':
        dados = request.get_json()
        if not dados or not dados.get('serie') or not dados.get('nome'): return jsonify({'erro': 'Nome e Série da máquina são obrigatórios'}), 400
        maquina.nome, maquina.serie = dados['nome'], dados['serie']
        try:
            db.session.commit()
            return jsonify({'id': maquina.id, 'nome': maquina.nome, 'serie': maquina.serie})
        except Exception:
            db.session.rollback(); return jsonify({'erro': 'Erro ao atualizar a máquina. A série já pode existir.'}), 500
    elif request.method == 'DELETE':
        db.session.delete(maquina); db.session.commit()
        return jsonify({'mensagem': 'Máquina excluída com sucesso!'})
    return jsonify({'erro': 'Método não permitido'}), 405

@app.route('/api/manutencoes', methods=['GET', 'POST'])
@requires_auth
def handle_manutencoes_api():
    if request.method == 'GET':
        query = db.select(Manutencao).options(joinedload(Manutencao.maquina), joinedload(Manutencao.solicitante), joinedload(Manutencao.responsavel), joinedload(Manutencao.pecas_utilizadas).joinedload(PecaUtilizada.peca))
        termo_busca, data_inicio, data_fim = request.args.get('termo'), request.args.get('data_inicio'), request.args.get('data_fim')
        if termo_busca:
            termo_like = f"%{termo_busca}%"
            query = query.join(Manutencao.maquina).outerjoin(Manutencao.pecas_utilizadas).outerjoin(PecaUtilizada.peca).join(Manutencao.solicitante).join(Manutencao.responsavel).where(
                or_(Maquina.nome.ilike(termo_like), Maquina.serie.ilike(termo_like), Manutencao.descricao.ilike(termo_like), Solicitante.nome.ilike(termo_like), Responsavel.nome.ilike(termo_like), Peca.nome.ilike(termo_like)))
        if data_inicio: query = query.where(Manutencao.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
        if data_fim: query = query.where(Manutencao.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
        manutencoes = db.session.execute(query.order_by(Manutencao.data.desc())).scalars().unique().all()
        resultado = [{'id': m.id, 'data': m.data.strftime('%d/%m/%Y'), 'descricao': m.descricao, 'valor': f"{m.valor:.2f}", 'maquina_nome': m.maquina.nome, 'maquina_serie': m.maquina.serie, 'solicitante_nome': m.solicitante.nome, 'responsavel_nome': m.responsavel.nome, 'pecas_utilizadas': [{'nome_peca': p.peca.nome, 'quantidade': p.quantidade} for p in m.pecas_utilizadas]} for m in manutencoes]
        return jsonify(resultado)
    elif request.method == 'POST':
        dados = request.get_json()
        campos = ['maquina_id', 'data', 'descricao', 'solicitante_id', 'responsavel_id', 'valor', 'pecas']
        if not dados or not all(k in dados for k in campos): return jsonify({'erro': 'Dados incompletos no envio.'}), 400
        try:
            nova_manutencao = Manutencao(maquina_id=int(dados['maquina_id']), data=datetime.strptime(dados['data'], '%Y-%m-%d').date(), descricao=dados['descricao'], solicitante_id=int(dados['solicitante_id']), responsavel_id=int(dados['responsavel_id']), valor=float(dados['valor']))
            for peca_data in dados['pecas']:
                if peca_data.get('peca_id') and peca_data.get('quantidade'):
                    nova_peca = PecaUtilizada(peca_id=int(peca_data['peca_id']), quantidade=int(peca_data['quantidade']))
                    nova_manutencao.pecas_utilizadas.append(nova_peca)
            db.session.add(nova_manutencao)
            db.session.commit()
            return jsonify({'mensagem': 'Manutenção registrada com sucesso!'}), 201
        except Exception as e:
            db.session.rollback(); print(f"Erro: {e}"); return jsonify({'erro': 'Erro interno ao salvar.'}), 500
    return jsonify({'erro': 'Método não permitido'}), 405

@app.route('/api/manutencao/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@requires_auth
def handle_manutencao_api(id):
    manutencao = db.session.get(Manutencao, id)
    if not manutencao: return jsonify({'erro': 'Registro não encontrado'}), 404
    if request.method == 'DELETE':
        db.session.delete(manutencao); db.session.commit()
        return jsonify({'mensagem': 'Registro excluído com sucesso!'})
    elif request.method == 'PUT':
        dados = request.get_json()
        if not dados: return jsonify({'erro': 'Dados inválidos'}), 400
        try:
            manutencao.maquina_id, manutencao.data, manutencao.descricao, manutencao.solicitante_id, manutencao.responsavel_id, manutencao.valor = int(dados.get('maquina_id')), datetime.strptime(dados.get('data'), '%Y-%m-%d').date(), dados.get('descricao'), int(dados.get('solicitante_id')), int(dados.get('responsavel_id')), float(dados.get('valor'))
            manutencao.pecas_utilizadas.clear()
            for peca_data in dados.get('pecas', []):
                if peca_data.get('peca_id') and peca_data.get('quantidade'):
                    nova_peca = PecaUtilizada(peca_id=int(peca_data['peca_id']), quantidade=int(peca_data['quantidade']))
                    manutencao.pecas_utilizadas.append(nova_peca)
            db.session.commit()
            return jsonify({'mensagem': 'Manutenção atualizada com sucesso!'})
        except Exception as e:
            db.session.rollback(); print(f"Erro: {e}"); return jsonify({'erro': 'Erro interno ao atualizar.'}), 500
    elif request.method == 'GET':
        dados_retorno = {'id': manutencao.id, 'data_iso': manutencao.data.isoformat(), 'descricao': manutencao.descricao, 'valor': manutencao.valor, 'maquina_id': manutencao.maquina_id, 'solicitante_id': manutencao.solicitante_id, 'responsavel_id': manutencao.responsavel_id, 'pecas_utilizadas': [{'peca_id': p.peca_id, 'quantidade': p.quantidade} for p in manutencao.pecas_utilizadas]}
        return jsonify(dados_retorno)
    return jsonify({'erro': 'Método não suportado'}), 405

@app.route('/api/exportar', methods=['GET'])
@requires_auth
def exportar_excel():
    query = db.select(Manutencao).options(joinedload(Manutencao.maquina), joinedload(Manutencao.solicitante), joinedload(Manutencao.responsavel), joinedload(Manutencao.pecas_utilizadas).joinedload(PecaUtilizada.peca))
    termo_busca, data_inicio, data_fim = request.args.get('termo'), request.args.get('data_inicio'), request.args.get('data_fim')
    if termo_busca:
        termo_like = f"%{termo_busca}%"
        query = query.join(Manutencao.maquina).outerjoin(Manutencao.pecas_utilizadas).outerjoin(PecaUtilizada.peca).join(Manutencao.solicitante).join(Manutencao.responsavel).where(or_(Maquina.nome.ilike(termo_like), Maquina.serie.ilike(termo_like), Manutencao.descricao.ilike(termo_like), Solicitante.nome.ilike(termo_like), Responsavel.nome.ilike(termo_like), Peca.nome.ilike(termo_like)))
    if data_inicio: query = query.where(Manutencao.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim: query = query.where(Manutencao.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
    manutencoes = db.session.execute(query.order_by(Manutencao.data.asc())).scalars().unique().all()
    if not manutencoes: return "Nenhum dado para exportar.", 404
    lista_para_excel = []
    for m in manutencoes:
        pecas_str = "; ".join([f"{p.quantidade}x {p.peca.nome}" for p in m.pecas_utilizadas])
        lista_para_excel.append({'Máquina': m.maquina.nome, 'Série': m.maquina.serie, 'Data': m.data.strftime('%d/%m/%Y'), 'Descrição do Serviço': m.descricao, 'Peças Utilizadas': pecas_str, 'Solicitante': m.solicitante.nome, 'Responsável': m.responsavel.nome, 'Valor (R$)': m.valor})
    df = pd.DataFrame(lista_para_excel)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Manutencoes')
    output.seek(0)
    nome_arquivo = f'relatorio_manutencoes_{datetime.now().strftime("%d-%m-%Y")}.xlsx'
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=nome_arquivo)

@app.route('/api/template/download')
@requires_auth
def download_template():
    return "Funcionalidade de importação desativada devido à complexidade do novo modelo.", 501

if __name__ == '__main__':
    if 'APP_USER' not in os.environ: os.environ['APP_USER'] = 'admin'
    if 'APP_PASSWORD' not in os.environ: os.environ['APP_PASSWORD'] = 'admin'
    if 'SECRET_KEY' not in os.environ: os.environ['SECRET_KEY'] = 'chave-super-secreta-para-ambiente-local'
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)