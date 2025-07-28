import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
from datetime import datetime, timezone # Importar timezone de datetime
from zoneinfo import ZoneInfo # Importar ZoneInfo

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Definir el huso horario de Buenos Aires (ART)
# Puedes encontrar los nombres de huso horario en la base de datos IANA (ej. 'America/Argentina/Buenos_Aires')
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

    # CÓDIGO TEMPORAL PARA CARGAR DATOS ORIGINALES (NO BORRADO AÚN)
    print("DEBUG: Intentando cargar datos de Personal desde Personal.csv...")
    try:
        df_personal_original = pd.read_csv(os.path.join(BASE_DIR, 'Personal.csv'), delimiter=';')
        personas_añadidas = 0
        for index, row in df_personal_original.iterrows():
            existing_personal = Personal.query.filter_by(nombre_responsable=row['Nombre Responsable']).first()
            if not existing_personal:
                new_personal = Personal(nombre_responsable=row['Nombre Responsable'], email=row['Email'])
                db.session.add(new_personal)
                personas_añadidas += 1
        if personas_añadidas > 0:
            db.session.commit()
            print(f"DEBUG: {personas_añadidas} personas originales insertadas desde Personal.csv.")
        else:
            print("DEBUG: No se encontraron nuevas personas en Personal.csv para insertar o ya existían en la DB.")
    except FileNotFoundError:
        print("ERROR: Personal.csv no encontrado en el servidor de Render. No se pudieron cargar personas originales.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Fallo al cargar personal desde CSV: {e}")

    print("DEBUG: Intentando cargar datos de Equipos desde Equipos.csv...")
    try:
        df_equipos_original = pd.read_csv(os.path.join(BASE_DIR, 'Equipos.csv'), delimiter=';')
        equipos_a_añadir = []
        for index, row in df_equipos_original.iterrows():
            existing_equipo = Equipo.query.filter_by(nombre_equipo=row['Nombre Equipo']).first()
            if not existing_equipo:
                new_equipo = Equipo(nombre_equipo=row['Nombre Equipo'], descripcion=row['Descripcion'])
                equipos_a_añadir.append(new_equipo)
            if equipos_a_añadir:
                db.session.add_all(equipos_a_añadir)
                db.session.commit()
                print(f"DEBUG: {len(equipos_a_añadir)} equipos originales insertados desde Equipos.csv.")
            else:
                print("DEBUG: No se encontraron nuevos equipos en Equipos.csv para insertar o ya existían en la DB.")
    except FileNotFoundError:
        print("ERROR: Equipos.csv no encontrado en el servidor de Render. No se pudieron cargar equipos originales.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Fallo al cargar equipos desde CSV: {e}")

    print(f"DEBUG: La tabla 'personal' tiene {Personal.query.count()} registros al final del startup.")
    print(f"DEBUG: La tabla 'equipo' tiene {Equipo.query.count()} registros al final del startup.")

@app.route('/')
def index():
    registros_db = Registro.query.all()
    personal_db = Personal.query.all()
    equipos_db = Equipo.query.all()

    registros_para_html = []
    for reg in registros_db:
        # Convertir a la hora de Buenos Aires antes de formatear para HTML
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
                           registros=registros_para_html)

@app.route('/registrar_salida', methods=['POST'])
def registrar_salida():
    equipo_nombre = request.form['equipo_id']
    personal_nombre_salida = request.form['personal_id_salida']
    
    # Obtener la hora actual en UTC y luego convertirla a la zona horaria deseada para guardar o mostrar
    fecha_hora_salida_utc = datetime.now(timezone.utc) # Guardar en UTC en la DB (recomendado)

    nuevo_registro = Registro(
        nombre_usuario=request.form['nombre_usuario'], # Directamente desde el form
        nombre_equipo=equipo_nombre,
        id_personal_salida=personal_nombre_salida,
        fecha_hora_salida=fecha_hora_salida_utc, # Usar la hora UTC
        estado='Pendiente'
    )
    db.session.add(nuevo_registro)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/registrar_devolucion', methods=['POST'])
def registrar_devolucion():
    registro_id = request.form['registro_id']
    personal_nombre_devolucion = request.form['personal_id_devolucion']
    
    # Obtener la hora actual en UTC para la devolución
    fecha_hora_devolucion_utc = datetime.now(timezone.utc) # Guardar en UTC

    registro = Registro.query.get(registro_id)
    if registro:
        registro.id_personal_devolucion = personal_nombre_devolucion
        registro.fecha_hora_devolucion = fecha_hora_devolucion_utc # Usar la hora UTC
        registro.estado = 'Completo'
        db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)