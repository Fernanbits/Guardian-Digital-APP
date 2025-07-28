import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

BUENOS_AIRES_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

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

    # --- INICIO: CÓDIGO TEMPORAL PARA FORZAR CARGA DE DATOS ORIGINALES DESDE CSVs ---
    # !!! ATENCIÓN: ESTO BORRA Y VUELVE A INSERTAR PERSONAL Y EQUIPOS EN CADA INICIO !!!
    # Lo eliminaremos al final.

    print("DEBUG: Borrando datos existentes de Personal para recargar desde CSV...")
    db.session.query(Personal).delete()
    db.session.commit()
    print("DEBUG: Datos de Personal borrados.")

    print("DEBUG: Intentando cargar datos de Personal desde Personal.csv...")
    try:
        df_personal_original = pd.read_csv(os.path.join(BASE_DIR, 'Personal.csv'), delimiter=';')
        personas_a_añadir = []
        for index, row in df_personal_original.iterrows():
            new_personal = Personal(nombre_responsable=row['Nombre Responsable'], email=row['Email'])
            personas_a_añadir.append(new_personal)
        if personas_a_añadir:
            db.session.add_all(personas_a_añadir)
            db.session.commit()
            print(f"DEBUG: {len(personas_a_añadir)} personas originales insertadas desde Personal.csv.")
        else:
            print("DEBUG: Personal.csv no contenía personas para insertar.")
    except FileNotFoundError:
        print("ERROR: Personal.csv no encontrado en el servidor de Render. No se pudieron cargar personas originales.")
        db.session.rollback()
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Fallo al cargar personal desde CSV: {e}")

    print("DEBUG: Borrando datos existentes de Equipos para recargar desde CSV...")
    db.session.query(Equipo).delete()
    db.session.commit()
    print("DEBUG: Datos de Equipos borrados.")

    print("DEBUG: Intentando cargar datos de Equipos desde Equipos.csv...")
    try:
        df_equipos_original = pd.read_csv(os.path.join(BASE_DIR, 'Equipos.csv'), delimiter=';')
        equipos_a_añadir = []
        for index, row in df_equipos_original.iterrows():
            new_equipo = Equipo(nombre_equipo=row['Nombre Equipo'], descripcion=row['Descripcion'])
            equipos_a_añadir.append(new_equipo)
        if equipos_a_añadir:
            db.session.add_all(equipos_a_añadir)
            db.session.commit()
            print(f"DEBUG: {len(equipos_a_añadir)} equipos originales insertados desde Equipos.csv.")
        else:
            print("DEBUG: Equipos.csv no contenía equipos para insertar.")
    except FileNotFoundError:
        print("ERROR: Equipos.csv no encontrado en el servidor de Render. No se pudieron cargar equipos originales.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Fallo al cargar equipos desde CSV: {e}")
    # --- FIN: CÓDIGO TEMPORAL PARA FORZAR CARGA DE DATOS ORIGINALES DESDE CSVs ---

    print(f"DEBUG: La tabla 'personal' tiene {Personal.query.count()} registros al final del startup.")
    print(f"DEBUG: La tabla 'equipo' tiene {Equipo.query.count()} registros al final del startup.")

@app.route('/')
def index():
    responsable_filter = request.args.get('responsable_filter')
    pc_filter = request.args.get('pc_filter')

    query = Registro.query

    if responsable_filter:
        query = query.filter(db.or_(
            Registro.id_personal_salida.ilike(f'%{responsable_filter}%'),
            Registro.id_personal_devolucion.ilike(f'%{responsable_filter}%')
        ))
    
    if pc_filter:
        query = query.filter(Registro.nombre_equipo.ilike(f'%{pc_filter}%'))

    registros_db = query.all()
    personal_db = Personal.query.all()
    equipos_db = Equipo.query.all()

    registros_para_html = []
    for reg in registros_db:
        fecha_salida_local = reg.fecha_hora_salida.astimezone(BUENOS_AIRES_TZ) if reg.fecha_hora_salida else None
        fecha_devolucion_local = reg.fecha_hora_devolucion.astimezone(BUENOS_AIRES_TZ) if reg.fecha_hora_devolucion else None

        registros_para_html.append({
            'ID Registro': reg.id,
            'Fecha y Hora Salida': fecha_salida_local.strftime('%d/%m/%Y %H:%M') if fecha_salida_local else '',
            'Nombre Usuario': reg.nombre_usuario,
            'Nombre Equipo': reg.nombre_equipo,
            'ID Personal Salida': reg.id_personal_salida,
            'Fecha y Hora Devolucion': fecha_devolucion_local.strftime('%d/%m/%Y %H:%M') if fecha_devolucion_local else '',
            'ID Personal Devolucion': reg.id_personal_devolucion,
            'Estado': reg.estado
        })

    personal_para_html = [{'Nombre Responsable': p.nombre_responsable} for p in personal_db]
    equipos_para_html = [{'Nombre Equipo': e.nombre_equipo} for e in equipos_db]

    print(f"DEBUG: Número de personal enviado al HTML: {len(personal_db)}")
    print(f"DEBUG: Número de equipos enviado al HTML: {len(equipos_db)}")

    return render_template('index.html',
                           personal=personal_para_html,
                           equipos=equipos_para_html,
                           registros=registros_para_html,
                           responsable_filter=responsable_filter,
                           pc_filter=pc_filter)

@app.route('/registrar_salida', methods=['POST'])
def registrar_salida():
    equipo_nombre = request.form['equipo_id']
    personal_nombre_salida = request.form['personal_id_salida']
    
    fecha_hora_salida_utc = datetime.now(timezone.utc)

    nuevo_registro = Registro(
        nombre_usuario=request.form['nombre_usuario'],
        nombre_equipo=equipo_nombre,
        id_personal_salida=personal_nombre_salida,
        fecha_hora_salida=fecha_hora_salida_utc,
        estado='Pendiente'
    )
    db.session.add(nuevo_registro)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/registrar_devolucion', methods=['POST'])
def registrar_devolucion():
    registro_id = request.form['registro_id']
    personal_nombre_devolucion = request.form['personal_id_devolucion']
    
    fecha_hora_devolucion_utc = datetime.now(timezone.utc)

    registro = Registro.query.get(registro_id)
    if registro:
        registro.id_personal_devolucion = personal_nombre_devolucion
        registro.fecha_hora_devolucion = fecha_hora_devolucion_utc,
        registro.estado = 'Completo'
        db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)