import os

import psycopg2
from flask import Flask
from flask_restful import Api, Resource

from db_startup import create_dependencies_table, seed_dependencies_table

app = Flask(__name__)
api = Api(app)

DB_HOST = os.environ.get('DB_HOST', "localhost")
DB_USER = os.environ.get('DB_USER', "postgres")
DB_PASSWORD = os.environ.get('DB_PASSWORD', "postgres")
DB_PORT = os.environ.get('DB_PORT', 5432)
DB_NAME = os.environ.get('DB_NAME', "postgres")

conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)

@app.route('/')
def homepage():
    return """<a href="http://localhost:5000/msapi/deppkg"> Click Here"""

class EnvironmentResource(Resource):
    def get(self):
        query = f"SELECT compid, packagename, packageversion, cve, cve_url, license, license_url FROM dm_componentdeps;"
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        response_data = []
        for row in rows:
            response_data.append(
                {
                    'compid': row[0],
                    'packagename': row[1],
                    'packageversion': row[2],
                    'cve': row[3],
                    'cve_url': row[4],
                    'license': row[5],
                    'license_url': row[6],
                }
            )
        cursor.close()
        return response_data


api.add_resource(EnvironmentResource, '/msapi/deppkg')

if __name__ == '__main__':
    create_dependencies_table(conn)
    seed_dependencies_table(conn)
    app.run(host="0.0.0.0", port=5000, debug=True)
