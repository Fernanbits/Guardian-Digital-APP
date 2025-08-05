#========================================================
# Imports y Configuración
#========================================================
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

ADMIN_USER = 'admin'
ADMIN_PASSWORD = 'password'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

BUENOS_AIRES_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

#========================================================
# Funciones Auxiliares
#========================================================
def generate_uuid():
    return str(uuid.uuid4())

#========================================================
# Modelos de la Base de Datos
#========================================================
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
    id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
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

#========================================================
# Autenticación y Rutas Principales
#========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Inicio de sesión exitoso como administrador.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Credenciales incorrectas. Inténtalo de nuevo.', 'danger')
    return render_template('login.html', datetime=datetime)

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('index'))

@app.route('/')
def index():
    responsable_filter = request.args.get('responsable_filter')
    pc_filter = request.args.get('pc_filter')

    query = Registro.query
    
    if responsable_filter:
        query = query.filter(or_(
            Registro.id_personal_salida.ilike(f'%{responsable_filter}%'),
            Registro.id_personal_devolucion.ilike(f'%{responsable_filter}%')
        ))
    
    if pc_filter:
        query = query.filter(Registro.nombre_equipo.ilike(f'%{pc_filter}%'))

    query = query.order_by(Registro.fecha_hora_salida.desc())

    if not responsable_filter and not pc_filter:
        registros_db = query.limit(35).all()
    else:
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
            'Estado': reg.estado,
        })

    personal_para_html = [{'Nombre Responsable': p.nombre_responsable} for p in personal_db]
    equipos_para_html = [{'Nombre Equipo': e.nombre_equipo} for e in equipos_db]

    return render_template('index.html',
                           personal=personal_para_html,
                           equipos=equipos_para_html,
                           registros=registros_para_html,
                           responsable_filter=responsable_filter,
                           pc_filter=pc_filter,
                           is_admin=session.get('is_admin'),
                           datetime=datetime)

#========================================================
# Rutas de Gestión de Personal (Admin)
#========================================================
@app.route('/manage_personal')
def manage_personal():
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    personal_list = Personal.query.all()
    return render_template('personal_management.html', personal_list=personal_list, is_admin=True, datetime=datetime)

@app.route('/add_personal', methods=['POST'])
def add_personal():
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    nombre_responsable = request.form['nombre_responsable']
    email = request.form['email']
    if nombre_responsable:
        new_personal = Personal(nombre_responsable=nombre_responsable, email=email)
        db.session.add(new_personal)
        db.session.commit()
        flash(f'Persona "{nombre_responsable}" agregada con éxito.', 'success')
    return redirect(url_for('manage_personal'))

@app.route('/delete_personal/<int:id>', methods=['POST'])
def delete_personal(id):
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    personal_to_delete = Personal.query.get_or_404(id)
    db.session.delete(personal_to_delete)
    db.session.commit()
    flash(f'Persona "{personal_to_delete.nombre_responsable}" eliminada con éxito.', 'success')
    return redirect(url_for('manage_personal'))

#========================================================
# Rutas de Gestión de Equipos (Admin)
#========================================================
@app.route('/manage_equipment')
def manage_equipment():
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    equipment_list = Equipo.query.all()
    return render_template('equipment_management.html', equipment_list=equipment_list, is_admin=True, datetime=datetime)

@app.route('/add_equipment', methods=['POST'])
def add_equipment():
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    nombre_equipo = request.form['nombre_equipo']
    descripcion = request.form['descripcion']
    if nombre_equipo:
        new_equipment = Equipo(nombre_equipo=nombre_equipo, descripcion=descripcion)
        db.session.add(new_equipment)
        db.session.commit()
        flash(f'Equipo "{nombre_equipo}" agregado con éxito.', 'success')
    return redirect(url_for('manage_equipment'))

@app.route('/delete_equipment/<int:id>', methods=['POST'])
def delete_equipment(id):
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    equipment_to_delete = Equipo.query.get_or_404(id)
    db.session.delete(equipment_to_delete)
    db.session.commit()
    flash(f'Equipo "{equipment_to_delete.nombre_equipo}" eliminado con éxito.', 'success')
    return redirect(url_for('manage_equipment'))

@app.route('/delete_registro/<string:id>', methods=['POST'])
def delete_registro(id):
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    registro_to_delete = Registro.query.get_or_404(id)
    db.session.delete(registro_to_delete)
    db.session.commit()
    flash('Registro eliminado con éxito.', 'success')
    return redirect(url_for('index'))

#========================================================
# Rutas de Acciones (Salida y Devolución)
#========================================================
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
    flash('Salida de equipo registrada con éxito!', 'success')
    return redirect(url_for('index'))

@app.route('/devolucion/<string:registro_id>', methods=['GET', 'POST'])
def devolucion(registro_id):
    registro = Registro.query.get(registro_id)
    if not registro:
        flash('Error: Registro no encontrado.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        personal_nombre_devolucion = request.form.get('personal_id_devolucion')
        if not personal_nombre_devolucion:
            flash('Error: Debe seleccionar un responsable para la devolución.', 'danger')
            return redirect(url_for('devolucion', registro_id=registro_id))

        fecha_hora_devolucion_utc = datetime.now(timezone.utc)
        registro.id_personal_devolucion = personal_nombre_devolucion
        registro.fecha_hora_devolucion = fecha_hora_devolucion_utc
        registro.estado = 'Completo'
        db.session.commit()
        flash('Devolución de equipo registrada con éxito!', 'success')
        return redirect(url_for('index'))

    personal_list = Personal.query.all()
    return render_template('devolucion_form.html', registro=registro, personal_list=personal_list, datetime=datetime)

@app.route('/batch_update', methods=['POST'])
def batch_update():
    if not session.get('is_admin'):
        flash('Acceso denegado. Se requiere ser administrador.', 'danger')
        return redirect(url_for('login'))
    selected_records_ids = request.form.getlist('selected_records')
    responsible_devolucion = request.form['batch_responsible_devolucion']
    batch_action = request.form['batch_action']

    if not selected_records_ids:
        flash('No se seleccionó ningún registro para la acción en lote.', 'warning')
        return redirect(url_for('index'))

    if batch_action == 'complete' and not responsible_devolucion:
        flash('Error: Debe seleccionar un responsable para la devolución en lote.', 'danger')
        return redirect(url_for('index'))

    updated_count = 0
    for record_id in selected_records_ids:
        registro = Registro.query.get(record_id)
        if registro:
            if batch_action == 'complete':
                if registro.estado == 'Pendiente':
                    registro.id_personal_devolucion = responsible_devolucion
                    registro.fecha_hora_devolucion = datetime.now(timezone.utc)
                    registro.estado = 'Completo'
                    updated_count += 1
    
    db.session.commit()
    flash(f'{updated_count} registros actualizados en lote como {batch_action}.', 'success')
    return redirect(url_for('index'))

#========================================================
# Inicio de la Aplicación
#========================================================
if __name__ == '__main__':
    app.run(debug=True)