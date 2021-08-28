import os
from http import HTTPStatus

import psycopg2
import pybreaker
import requests
from flask import Flask, request  # module to create an api
from flask_restful import Api, Resource
import sqlalchemy.pool as pool
from flask_swagger_ui import get_swaggerui_blueprint
from webargs.flaskparser import abort, parser

#pylint: disable=unused-argument


@parser.error_handler
def handle_request_parsing_error(err, req, schema, *, error_status_code, error_headers):
    abort(HTTPStatus.BAD_REQUEST, errors=err.messages)


# Init Flask
app = Flask(__name__)
api = Api(app)
app.url_map.strict_slashes = False


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


# swagger config
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yml'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "ortelius-ms-dep-pkg-r"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

# Init db connection
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "postgres")
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASS", "postgres")
db_port = os.getenv("DB_PORT", "5432")
validateuser_url = os.getenv("VALIDATEUSER_URL", "http://localhost:5000")

# connection pool config
conn_pool_size = int(os.getenv("POOL_SIZE", "3"))
conn_pool_max_overflow = int(os.getenv("POOL_MAX_OVERFLOW", "2"))
conn_pool_timeout = float(os.getenv("POOL_TIMEOUT", "30.0"))

conn_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=1,
    reset_timeout=10,
)


@conn_circuit_breaker
def create_conn():
    conn = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    return conn


# connection pool init
mypool = pool.QueuePool(create_conn, max_overflow=conn_pool_max_overflow, pool_size=conn_pool_size, timeout=conn_pool_timeout)


class HealthCheck(Resource):
    def get(self):
        try:
            conn = mypool.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            if cursor.rowcount > 0:
                return ({"status": 'UP', "service_name": 'ortelius-ms-dep-pkg-r'}), HTTPStatus.OK
            return ({"status": 'DOWN'}), HTTPStatus.SERVICE_UNAVAILABLE

        except Exception as err:
            print(err)
            return ({"status": 'DOWN'}), HTTPStatus.SERVICE_UNAVAILABLE


api.add_resource(HealthCheck, '/health')


class EnvironmentResource(Resource):

    def get(self):

        result = requests.get(validateuser_url + "/msapi/validateuser", cookies=request.cookies)
        if (result is None):
            return None, HTTPStatus.UNAUTHORIZED

        if (result.status_code != 200):
            return result.json(), HTTPStatus.UNAUTHORIZED

        conn = mypool.connect()
        cursor = conn.cursor()

        compid = request.args.get('compid', None)
        deptype = request.args.get('deptype', None)

        sql = "SELECT packagename, packageversion, name, url, summary FROM dm_componentdeps where compid = %s and deptype = %s"

        params = (compid, deptype, )
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
        return {'data': response_data}


api.add_resource(EnvironmentResource, '/msapi/deppkg')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5004)
