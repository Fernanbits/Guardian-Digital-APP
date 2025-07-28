import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
import os
from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy # ### CAMBIO IMPORTANTE ### Importar SQLAlchemy

# --- Configuración de la aplicación Flask ---
app = Flask(__name__)

# --- Configuración de la Base de Datos ---
# La variable de entorno DATABASE_URL será proporcionada por Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Definición de Modelos de la Base de Datos ### CAMBIO IMPORTANTE ### ---
# Estos modelos representan tus tablas en la base de datos
class Personal(db.Model):
    id = db.Column(db.Integer, primary_key=True) # ID auto-incremental
    nombre_responsable = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Personal {self.nombre_responsable}>"

class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True) # ID auto-incremental
    nombre_equipo = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<Equipo {self.nombre_equipo}>"

class Registro(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4())) # UUID como ID
    fecha_hora_salida = db.Column(db.DateTime, nullable=False, default=datetime.now)
    nombre_usuario = db.Column(db.String(100), nullable=False)
    nombre_equipo = db.Column(db.String(100), nullable=False) # Guardamos el nombre del equipo
    id_personal_salida = db.Column(db.String(100), nullable=False) # Guardamos el nombre del personal de salida
    fecha_hora_devolucion = db.Column(db.DateTime, nullable=True)
    id_personal_devolucion = db.Column(db.String(100), nullable=True) # Guardamos el nombre del personal de devolución
    estado = db.Column(db.String(50), nullable=False, default='Pendiente')

    def __repr__(self):
        return f"<Registro {self.id} - {self.nombre_equipo}>"

# --- Crear las tablas de la base de datos si no existen ### CAMBIO IMPORTANTE ### ---
# Esta función se ejecutará al iniciar la aplicación para asegurar que la DB esté lista
with app.app_context():
    db.create_all()

# --- Funciones auxiliares para trabajar con los datos (ahora de la DB) ---

# No necesitamos funciones guardar_registros() separadas, SQLAlchemy maneja esto.
# Los datos ahora se obtienen directamente de la DB para los templates.

# --- Rutas de la aplicación web ---

@app.route('/')
def index():
    # Obtener todos los registros, personal y equipos de la base de datos
    registros_db = Registro.query.all()
    personal_db = Personal.query.all()
    equipos_db = Equipo.query.all()

    # Convertir los objetos de la DB a diccionarios para pasarlos al template
    # Formatear las fechas para la visualización en HTML
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


    return render_template('index.html',
                           personal=personal_para_html,
                           equipos=equipos_para_html,
                           registros=registros_para_html)

@app.route('/registrar_salida', methods=['POST'])
def registrar_salida():
    # Obtener datos del formulario
    equipo_nombre = request.form['equipo_id']
    personal_nombre_salida = request.form['personal_id_salida']
    nombre_usuario_actual = request.form['nombre_usuario']

    # Crear una nueva instancia del modelo Registro y añadir a la DB
    nuevo_registro = Registro(
        nombre_usuario=nombre_usuario_actual,
        nombre_equipo=equipo_nombre,
        id_personal_salida=personal_nombre_salida,
        estado='Pendiente' # Estado por defecto al crear
    )
    db.session.add(nuevo_registro)
    db.session.commit() # Guardar los cambios en la base de datos

    return redirect(url_for('index'))

@app.route('/registrar_devolucion', methods=['POST'])
def registrar_devolucion():
    registro_id = request.form['registro_id']
    personal_nombre_devolucion = request.form['personal_id_devolucion']
    fecha_hora_devolucion = datetime.now()

    # Buscar el registro por su ID y actualizarlo
    registro = Registro.query.get(registro_id) # Buscar por primary key (ID)
    if registro:
        registro.id_personal_devolucion = personal_nombre_devolucion
        registro.fecha_hora_devolucion = fecha_hora_devolucion
        registro.estado = 'Completo'
        db.session.commit() # Guardar los cambios en la base de datos

    return redirect(url_for('index'))

# --- Iniciar la aplicación Flask ---
if __name__ == '__main__':
    # La primera vez que corras esto, creará 'site.db'
    # db.create_all() ya se llama dentro de app.app_context()
    app.run(debug=True)