import os
import io
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Float, Date, or_
from datetime import date, datetime
import pandas as pd

# --- Configuração Inicial ---
app = Flask(__name__)

instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "manutencoes.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Modelo do Banco de Dados ---
class Manutencao(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_empacotadeira: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    num_equipamento: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    solicitante: Mapped[str] = mapped_column(String(100), nullable=False)
    responsavel: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False)

    def __init__(self, serie_empacotadeira, data, descricao, solicitante, responsavel, valor, num_equipamento=None):
        self.serie_empacotadeira = serie_empacotadeira
        self.data = data
        self.num_equipamento = num_equipamento
        self.descricao = descricao
        self.solicitante = solicitante
        self.responsavel = responsavel
        self.valor = valor

    def to_dict(self):
        return {
            'id': self.id,
            'serie_empacotadeira': self.serie_empacotadeira,
            'data': self.data.strftime('%d/%m/%Y'),
            'num_equipamento': self.num_equipamento,
            'descricao': self.descricao,
            'solicitante': self.solicitante,
            'responsavel': self.responsavel,
            'valor': f"{self.valor:.2f}"
        }

# --- Lógica de Autenticação ---
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        app_user = os.environ.get('APP_USER')
        app_password = os.environ.get('APP_PASSWORD')

        if not auth or not (auth.username == app_user and auth.password == app_password):
            return Response(
                'Acesso negado. É necessário fornecer credenciais válidas.', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        
        return f(*args, **kwargs)
    return decorated

# --- Rotas da Aplicação ---
@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/api/manutencoes', methods=['GET', 'POST'])
@requires_auth
def handle_manutencoes():
    if request.method == 'GET':
        query = db.select(Manutencao)
        
        termo_busca = request.args.get('termo')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        if termo_busca:
            termo_like = f"%{termo_busca}%"
            query = query.where(
                or_(
                    Manutencao.serie_empacotadeira.ilike(termo_like),
                    Manutencao.num_equipamento.ilike(termo_like),
                    Manutencao.descricao.ilike(termo_like),
                    Manutencao.solicitante.ilike(termo_like),
                    Manutencao.responsavel.ilike(termo_like)
                )
            )

        if data_inicio:
            query = query.where(Manutencao.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
        
        if data_fim:
            query = query.where(Manutencao.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

        query = query.order_by(Manutencao.data.desc())
        
        manutencoes = db.session.execute(query).scalars().all()
        return jsonify([m.to_dict() for m in manutencoes])
    
    elif request.method == 'POST':
        dados = request.get_json()
        if not dados or not all(k in dados for k in ['serie_empacotadeira', 'data', 'descricao', 'solicitante', 'responsavel', 'valor']):
            return jsonify({'erro': 'Dados incompletos ou formato inválido'}), 400

        nova_manutencao = Manutencao(
            serie_empacotadeira=dados['serie_empacotadeira'],
            data=datetime.strptime(dados['data'], '%Y-%m-%d').date(),
            num_equipamento=dados.get('num_equipamento'),
            descricao=dados['descricao'],
            solicitante=dados['solicitante'],
            responsavel=dados['responsavel'],
            valor=float(dados['valor'])
        )
        
        db.session.add(nova_manutencao)
        db.session.commit()
        return jsonify(nova_manutencao.to_dict()), 201
    
    return jsonify({'erro': 'Método não permitido'}), 405


@app.route('/api/exportar', methods=['GET'])
@requires_auth
def exportar_excel():
    query = db.select(Manutencao)
    
    termo_busca = request.args.get('termo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    if termo_busca:
        termo_like = f"%{termo_busca}%"
        query = query.where(
            or_(
                Manutencao.serie_empacotadeira.ilike(termo_like),
                Manutencao.num_equipamento.ilike(termo_like),
                Manutencao.descricao.ilike(termo_like),
                Manutencao.solicitante.ilike(termo_like),
                Manutencao.responsavel.ilike(termo_like)
            )
        )

    if data_inicio:
        query = query.where(Manutencao.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    
    if data_fim:
        query = query.where(Manutencao.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

    query = query.order_by(Manutencao.data.asc())
    
    manutencoes = db.session.execute(query).scalars().all()
    
    if not manutencoes:
        return "Nenhum dado encontrado para exportar com os filtros aplicados.", 404
        
    dados_para_df = [m.to_dict() for m in manutencoes]
    df = pd.DataFrame(dados_para_df)

    df.rename(columns={
        'id': 'ID',
        'serie_empacotadeira': 'Série da Empacotadeira',
        'data': 'Data',
        'num_equipamento': 'N° do Equipamento',
        'descricao': 'Descrição do Serviço',
        'solicitante': 'Solicitante',
        'responsavel': 'Responsável',
        'valor': 'Valor (R$)'
    }, inplace=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Manutencoes')
    output.seek(0)
    
    nome_arquivo = f'relatorio_manutencoes_{datetime.now().strftime("%d-%m-%Y")}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nome_arquivo
    )

@app.route('/api/importar', methods=['POST'])
@requires_auth
def importar_excel():
    if 'arquivo' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado.'}), 400
    
    arquivo = request.files['arquivo']
    
    if not arquivo or arquivo.filename == '':
        return jsonify({'erro': 'Nenhum arquivo selecionado.'}), 400

    filename = arquivo.filename
    if not (filename.endswith('.xlsx') or filename.endswith('.xls')): # type: ignore
        return jsonify({'erro': 'Formato de arquivo inválido. Use .xlsx ou .xls'}), 400
    
    try:
        df = pd.read_excel(arquivo)
        
        colunas_necessarias = ['serie_empacotadeira', 'data', 'descricao', 'solicitante', 'responsavel', 'valor']
        if not all(col in df.columns for col in colunas_necessarias):
            return jsonify({'erro': 'O arquivo não contém todas as colunas necessárias. Baixe o modelo.'}), 400

        registros_adicionados = 0
        for _, row in df.iterrows():
            try:
                data_obj = pd.to_datetime(row['data']).date()

                nova_manutencao = Manutencao(
                    serie_empacotadeira=str(row['serie_empacotadeira']),
                    data=data_obj,
                    num_equipamento=str(row['num_equipamento']) if pd.notna(row.get('num_equipamento')) else None,
                    descricao=str(row['descricao']),
                    solicitante=str(row['solicitante']),
                    responsavel=str(row['responsavel']),
                    valor=float(row['valor'])
                )
                db.session.add(nova_manutencao)
                registros_adicionados += 1
            except Exception as e:
                print(f"Erro ao processar linha: {row}. Erro: {e}")
                continue

        db.session.commit()
        return jsonify({'mensagem': f'{registros_adicionados} registros importados com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Ocorreu um erro ao processar o arquivo: {e}'}), 500

@app.route('/api/template/download')
@requires_auth
def download_template():
    colunas = [
        'serie_empacotadeira', 'data', 'num_equipamento', 
        'descricao', 'solicitante', 'responsavel', 'valor'
    ]
    df_template = pd.DataFrame(columns=colunas)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False, sheet_name='ModeloImportacao')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='modelo_importacao_manutencoes.xlsx'
    )

# --- Inicialização ---
if __name__ == '__main__':
    if 'APP_USER' not in os.environ:
        print("AVISO: Variáveis de ambiente não definidas. Usando credenciais padrão para teste local.")
        os.environ['APP_USER'] = 'admin'
        os.environ['APP_PASSWORD'] = 'admin'

    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)