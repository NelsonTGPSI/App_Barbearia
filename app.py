from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'segredo'

def get_db():
    conn = sqlite3.connect('barbearia.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists('barbearia.db'):
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                data TEXT NOT NULL,
                hora TEXT NOT NULL,
                servico TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL
            )
        ''')
        # Cria admin padrão
        c.execute('INSERT INTO admin (usuario, senha) VALUES (?, ?)', ('admin', 'admin123'))
        conn.commit()
        conn.close()

@app.route('/', methods=['GET', 'POST'])
def agenda():
    conn = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        data = request.form['data']
        hora = request.form['hora']
        servico = request.form['servico']

        # Validação: data/hora não pode ser no passado
        try:
            agendamento_dt = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
            agora = datetime.now()
            if agendamento_dt < agora:
                flash('Não é possível agendar para datas/horários passados.', 'danger')
                conn.close()
                return render_template('agenda.html')
        except Exception:
            flash('Data ou hora inválida.', 'danger')
            conn.close()
            return render_template('agenda.html')

        # Impede agendamento durante o almoço
        if hora == "12:00":
            flash('Não é possível agendar das 12:00 às 13:00 (horário de almoço).', 'danger')
            conn.close()
            return render_template('agenda.html')

        # Só permite horários das 09:00 às 12:00 e das 13:00 às 18:00 (último horário 18:00)
        dt = datetime.strptime(data, "%Y-%m-%d")
        weekday = dt.weekday()  # 0=segunda, 6=domingo
        hora_int = int(hora.split(':')[0])
        if weekday >= 5 or hora_int < 9 or hora_int > 18 or hora == "12:00":
            flash('Só é possível agendar de segunda a sexta, das 09:00 às 12:00 e das 13:00 às 19:00 (exceto 12:00).', 'danger')
            conn.close()
            return render_template('agenda.html')

        # Verifica se já existe agendamento que conflita com o horário escolhido (1h de duração)
        hora_inicio = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
        hora_fim = hora_inicio + timedelta(hours=1)
        agendamentos_conflito = conn.execute(
            '''
            SELECT 1 FROM agendamentos
            WHERE data=? AND (
                (time(hora) <= ? AND time(hora, '+1 hour') > ?) OR
                (time(hora) < ? AND time(hora, '+1 hour') > ?)
            )
            ''',
            (data, hora, hora, hora_fim.strftime("%H:%M"), hora_fim.strftime("%H:%M"))
        ).fetchone()
        if agendamentos_conflito:
            flash('Horário já ocupado! Escolha outro horário.', 'danger')
            conn.close()
            return render_template('agenda.html')

        # Se passou por todas as validações, salva o agendamento
        conn.execute(
            'INSERT INTO agendamentos (nome, telefone, data, hora, servico) VALUES (?, ?, ?, ?, ?)',
            (nome, telefone, data, hora, servico)
        )
        conn.commit()
        flash('Agendamento criado!', 'success')
    conn.close()
    return render_template('agenda.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'admin' in session:
        return redirect(url_for('admin_agendamentos'))
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        conn = get_db()
        admin = conn.execute('SELECT * FROM admin WHERE usuario=? AND senha=?', (usuario, senha)).fetchone()
        conn.close()
        if admin:
            session['admin'] = usuario
            return redirect(url_for('admin_agendamentos'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/agendamentos')
def admin_agendamentos():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    agendamentos = conn.execute(
        'SELECT * FROM agendamentos ORDER BY data DESC, hora DESC'
    ).fetchall()
    conn.close()
    return render_template('admin_agendamentos.html', agendamentos=agendamentos)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)