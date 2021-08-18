import os

import psycopg2
import pybreaker
import requests
from flask import Flask, request  # module to create an api
from flask_restful import Api, Resource

# Init Flask
app = Flask(__name__)
api = Api(app)
app.url_map.strict_slashes = False

# Init db connection
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "postgres")
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASS", "postgres")
db_port = os.getenv("DB_PORT", "5432") 

conn_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=1,
    reset_timeout=10,
)

@conn_circuit_breaker
def create_conn():
    conn = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    return conn

class EnvironmentResource(Resource):

    @classmethod
    def get(cls):
        conn = create_conn() 
        cursor = conn.cursor()

        compid = request.args.get('compid', None)
        deptype = request.args.get('deptype', None)

        sql = "SELECT packagename, packageversion, name, url, summary FROM dm_componentdeps where compid = %s and deptype = %s"

        params=(compid, deptype, )
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        response_data = []
        valid_url = {}

        for row in rows:
            # check for license on SPDX site if not found just return the license landing page
            packagename = row[0]
            packageversion = row[1]
            name = row[2]
            url = row[3]
            summary = row[4]

            if (not url):
                url = 'https://spdx.org/licenses/'

            if (name not in valid_url):
                r = requests.head(url)
                if (r.status_code == 200):
                    valid_url[name] = url
                else:
                    valid_url[name] = 'https://spdx.org/licenses/'

            url = valid_url[name]

            response_data.append(
                {
                    'packagename': packagename,
                    'packageversion': packageversion,
                    'name': name,
                    'url': url,
                    'summary': summary
                }
            )
        cursor.close()
        return {'data' : response_data}

api.add_resource(EnvironmentResource, '/msapi/deppkg')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5004)
