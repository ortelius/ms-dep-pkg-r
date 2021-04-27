#import libraries and modules
from flask import Flask, request #library for developing the web application
from flask_restful import Api, Resource
import os
import psycopg2



# create an app instance
app = Flask(__name__)
api = Api(app)

DB_HOST = os.environ['DB_HOST', "localhost"]
DB_USER = os.environ['DB_USER', "postgres"]
DB_PASSWORD = os.environ['DB_PASSWORD', "postgres"]
DB_PORT = os.environ['DB_PORT', "postgres"]
DB_NAME = os.environ['DB_NAME', "postgres"]

conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)

DATABASE_STARTUP_QUERIES = [
    """CREATE TABLE IF NOT EXISTS dm_componentdeps
    (
        compid integer primary key,
        packagename varchar(1024),
        packageversion varchar(256),
        cve varchar(80),
        cve_url varchar(1024),
        license varchar(256),
        license_url varchar(1024)
    );""",
    "COMMENT ON TABLE dm_componentdeps IS 'Component Dependencies';",
    "COMMENT ON COLUMN dm_componentdeps.compid IS 'Component Id';",
    "COMMENT ON COLUMN dm_componentdeps.packagename IS 'Name of the package';",
    "COMMENT ON COLUMN dm_componentdeps.packageversion IS 'Version of the package';",
    "COMMENT ON COLUMN dm_componentdeps.cve IS 'Name of the CVE';",
    "COMMENT ON COLUMN dm_componentdeps.cve_url IS 'Url to the CVE details in the CVE website';",
    "COMMENT ON COLUMN dm_componentdeps.license IS 'Name of the License for the package';",
    "COMMENT ON COLUMN dm_componentdeps.license_url IS 'Url to the License File';"
]


@app.route('/msapi/deppkg', methods=['GET'])
def get_deps():
    rows = conn.execute("SELECT * FROM dm_componentdeps;")
    print(rows)


def pre_startup():
    for query in DATABASE_STARTUP_QUERIES:
        try:
            conn.execute(query)
        except psycopg2._psycopg.OperationalError as e:
            print(f'Executing query: {query} failed: {str(e)}')




if __name__ == '__main__':
    pre_startup()
    app.run(debug=True)
