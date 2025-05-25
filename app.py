from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_use_uma_chave_real'
app.config['DATABASE'] = 'barbearia.db'

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telefone TEXT,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'barbeiro',
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            email TEXT,
            observacoes TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            duracao INTEGER NOT NULL,
            ativo INTEGER DEFAULT 1
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            barbeiro_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            status TEXT DEFAULT 'agendado',
            observacoes TEXT,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (barbeiro_id) REFERENCES usuarios(id)
        )''')
        
        try:
            senha_admin = generate_password_hash('admin123')
            cursor.execute("INSERT OR IGNORE INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                          ('Administrador', 'admin@barbearia.com', senha_admin, 'admin'))
            
            servicos_iniciais = [
                ('Corte de Cabelo', 'Corte básico', 25.00, 30),
                ('Barba', 'Aparar e modelar barba', 20.00, 25),
                ('Corte + Barba', 'Pacote completo', 40.00, 55),
                ('Pezinho', 'Aparar a barba no pescoço', 10.00, 15)
            ]
            cursor.executemany("INSERT OR IGNORE INTO servicos (nome, descricao, preco, duracao) VALUES (?, ?, ?, ?)",
                              servicos_iniciais)
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao inicializar banco de dados: {e}")
        finally:
            conn.close()

@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin'))
        return redirect(url_for('agenda'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        if not email or not senha:
            flash('Email e senha são obrigatórios', 'error')
            return render_template('login.html')
        
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if usuario and check_password_hash(usuario['senha'], senha):
            session['user_id'] = usuario['id']
            session['user_nome'] = usuario['nome']
            session['user_email'] = usuario['email']
            session['is_admin'] = usuario['tipo'] == 'admin'
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin' if usuario['tipo'] == 'admin' else 'agenda'))
        
        flash('Credenciais inválidas', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        telefone = request.form.get('telefone')
        
        if not all([nome, email, senha]):
            flash('Preencha todos os campos obrigatórios', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        try:
            senha_hash = generate_password_hash(senha)
            conn.execute('INSERT INTO usuarios (nome, email, senha, telefone) VALUES (?, ?, ?, ?)',
                         (nome, email, senha_hash, telefone))
            conn.commit()
            flash('Registro realizado com sucesso! Faça login', 'success')
            return redirect(url_for('login'))
            flash('Email já cadastrado', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/agenda')
def agenda():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    agendamentos = conn.execute('''
        SELECT a.data, a.hora, s.nome as servico, c.nome as cliente 
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        JOIN clientes c ON a.cliente_id = c.id
        WHERE a.barbeiro_id = ?
        ORDER BY a.data, a.hora
    ''', (session['user_id'],)).fetchall()
    servicos = conn.execute('SELECT id, nome FROM servicos WHERE ativo = 1').fetchall()
    clientes = conn.execute('SELECT id, nome FROM clientes').fetchall()
    conn.close()
    
    return render_template('agenda.html', 
                         agendamentos=agendamentos,
                         servicos=servicos,
                         clientes=clientes)

@app.route('/agendar', methods=['POST'])
def agendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        data = request.form['data']
        hora = request.form['hora']
        cliente_id = request.form['cliente']
        servico_id = request.form['servico']
        
        # Validar data/hora
        datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO agendamentos 
            (cliente_id, servico_id, barbeiro_id, data, hora)
            VALUES (?, ?, ?, ?, ?)
        ''', (cliente_id, servico_id, session['user_id'], data, hora))
        conn.commit()
        conn.close()
        
        flash('Agendamento realizado com sucesso!', 'success')
    except ValueError:
        flash('Data/hora inválida', 'error')
    except Exception as e:
        print(f"Erro ao agendar: {e}")
        flash('Erro ao realizar agendamento', 'error')
    
    return redirect(url_for('agenda'))

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    total_clientes = conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    total_agendamentos = conn.execute('SELECT COUNT(*) FROM agendamentos').fetchone()[0]
    proximos_agendamentos = conn.execute('''
        SELECT a.data, a.hora, u.nome as barbeiro, c.nome as cliente, s.nome as servico
        FROM agendamentos a
        JOIN usuarios u ON a.barbeiro_id = u.id
        JOIN clientes c ON a.cliente_id = c.id
        JOIN servicos s ON a.servico_id = s.id
        WHERE a.data >= date('now')
        ORDER BY a.data, a.hora
        LIMIT 5
    ''').fetchall()
    conn.close()
    
    return render_template('admin.html', 
                         total_clientes=total_clientes,
                         total_agendamentos=total_agendamentos,
                         agendamentos=proximos_agendamentos)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)