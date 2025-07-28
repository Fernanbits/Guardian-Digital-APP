import pandas as pd
from sqlalchemy import create_engine
import os
from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy
from app import app, db, Personal, Equipo, Registro

LOCAL_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')
local_engine = create_engine(f'sqlite:///{LOCAL_DB_PATH}')

REMOTE_DATABASE_URL = "postgresql://guardiandigital:Hl7giZleBBmGo95kaKUM2o4CLm6WaS8S@dpg-d23cq3m3jp1c739phfcg-a.ohio-postgres.render.com/guardiandigital"
remote_engine = create_engine(REMOTE_DATABASE_URL)

def migrate_data():
    print("Iniciando migración de datos de SQLite a PostgreSQL...")

    original_db_uri = app.config['SQLALCHEMY_DATABASE_URI']

    # Se cambia la URI de la DB en la configuración de la app para que apunte a la remota
    app.config['SQLALCHEMY_DATABASE_URI'] = REMOTE_DATABASE_URL

    with app.app_context():
        # db.create_all() ahora usará la REMOTE_DATABASE_URL
        print("Creando tablas en la base de datos remota si no existen...")
        db.create_all()

        print("\nMigrando Personal...")
        with local_engine.connect() as local_conn:
            local_personal_data = pd.read_sql_table('personal', local_conn)

        for index, row in local_personal_data.iterrows():
            existing_personal = Personal.query.filter_by(nombre_responsable=row['nombre_responsable']).first()
            if not existing_personal:
                new_personal = Personal(nombre_responsable=row['nombre_responsable'], email=row['email'])
                db.session.add(new_personal)
                print(f"  Añadido: {row['nombre_responsable']}")
            else:
                print(f"  Ya existe: {row['nombre_responsable']} en remoto.")
        db.session.commit()
        print("Personal migrado.")

        print("\nMigrando Equipos...")
        with local_engine.connect() as local_conn:
            local_equipos_data = pd.read_sql_table('equipo', local_conn)

        for index, row in local_equipos_data.iterrows():
            existing_equipo = Equipo.query.filter_by(nombre_equipo=row['nombre_equipo']).first()
            if not existing_equipo:
                new_equipo = Equipo(nombre_equipo=row['nombre_equipo'], descripcion=row['descripcion'])
                db.session.add(new_equipo)
                print(f"  Añadido: {row['nombre_equipo']}")
            else:
                print(f"  Ya existe: {row['nombre_equipo']} en remoto.")
        db.session.commit()
        print("Equipos migrados.")

        print("\nMigrando Registros...")
        with local_engine.connect() as local_conn:
            local_registros_data = pd.read_sql_table('registro', local_conn)

        for index, row in local_registros_data.iterrows():
            existing_registro = Registro.query.filter_by(id=row['id']).first()
            if not existing_registro:
                new_registro = Registro(
                    id=row['id'],
                    fecha_hora_salida=row['fecha_hora_salida'],
                    nombre_usuario=row['nombre_usuario'],
                    nombre_equipo=row['nombre_equipo'],
                    id_personal_salida=row['id_personal_salida'],
                    fecha_hora_devolucion=row['fecha_hora_devolucion'],
                    id_personal_devolucion=row['id_personal_devolucion'],
                    estado=row['estado']
                )
                db.session.add(new_registro)
                print(f"  Añadido Registro: {row['id']}")
            else:
                print(f"  Ya existe Registro: {row['id']} en remoto.")
        db.session.commit()
        print("Registros migrados.")

    print("\nProceso de migración finalizado.")

    # Restaurar la URI original de la DB local
    # ¡Esta línea que causaba el error ha sido eliminada!
    app.config['SQLALCHEMY_DATABASE_URI'] = original_db_uri


if __name__ == '__main__':
    migrate_data()