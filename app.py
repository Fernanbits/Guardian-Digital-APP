from flask import Flask, render_template, request, redirect, url_for
import os
from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Personal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_responsable = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Personal {self.nombre_responsable}>"

class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_equipo = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<Equipo {self.nombre_equipo}>"

class Registro(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    fecha_hora_salida = db.Column(db.DateTime, nullable=False, default=datetime.now)
    nombre_usuario = db.Column(db.String(100), nullable=False)
    nombre_equipo = db.Column(db.String(100), nullable=False)
    id_personal_salida = db.Column(db.String(100), nullable=False)
    fecha_hora_devolucion = db.Column(db.DateTime, nullable=True)
    id_personal_devolucion = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(50), nullable=False, default='Pendiente')

    def __repr__(self):
        return f"<Registro {self.id} - {self.nombre_equipo}>"

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    registros_db = Registro.query.all()
    personal_db = Personal.query.all()
    equipos_db = Equipo.query.all()

    registros_para_html = []
    for reg in registros_db:
        registros_para_html.append({
            'ID Registro': reg.id,
            'Fecha y Hora Salida': reg.fecha_hora_salida.strftime('%d/%m/%Y %H:%M') if reg.fecha_hora_salida else '',
            'Nombre Usuario': reg.nombre_usuario,
            'Nombre Equipo': reg.nombre_equipo,
            'ID Personal Salida': reg.id_personal_salida,
            'Fecha y Hora Devolucion': reg.fecha_hora_devolucion.strftime('%d/%m/%Y %H:%M') if reg.fecha_hora_devolucion else '',
            'ID Personal Devolucion': reg.id_personal_devolucion,
            'Estado': reg.estado
        })

    personal_para_html = [{'Nombre Responsable': p.nombre_responsable} for p in personal_db]
    equipos_para_html = [{'Nombre Equipo': e.nombre_equipo} for e in equipos_db]

    # --- INICIO: LÍNEAS TEMPORALES PARA DEPURACIÓN ---
    print(f"DEBUG: Número de personal encontrado: {len(personal_db)}")
    print(f"DEBUG: Número de equipos encontrado: {len(equipos_db)}")
    # --- FIN: LÍNEAS TEMPORALES PARA DEPURACIÓN ---

    return render_template('index.html',
                        personal=personal_para_html,
                        equipos=equipos_para_html,
                        registros=registros_para_html)


@app.route('/registrar_salida', methods=['POST'])
def registrar_salida():
    equipo_nombre = request.form['equipo_id']
    personal_nombre_salida = request.form['personal_id_salida']
    nombre_usuario_actual = request.form['nombre_usuario']

    nuevo_registro = Registro(
        nombre_usuario=nombre_usuario_actual,
        nombre_equipo=equipo_nombre,
        id_personal_salida=personal_nombre_salida,
        estado='Pendiente'
    )
    db.session.add(nuevo_registro)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/registrar_devolucion', methods=['POST'])
def registrar_devolucion():
    registro_id = request.form['registro_id']
    personal_nombre_devolucion = request.form['personal_id_devolucion']
    fecha_hora_devolucion = datetime.now()

    registro = Registro.query.get(registro_id)
    if registro:
        registro.id_personal_devolucion = personal_nombre_devolucion
        registro.fecha_hora_devolucion = fecha_hora_devolucion
        registro.estado = 'Completo'
        db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)