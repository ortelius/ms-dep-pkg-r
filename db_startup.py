from psycopg2 import OperationalError

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


def create_dependencies_table(conn):
    cursor = conn.cursor()
    for query in DATABASE_STARTUP_QUERIES:
        try:
            cursor.execute(query)
        except OperationalError as e:
            print(f'Executing query: {query} failed: {str(e)}')
    conn.commit()
    cursor.close()


def seed_dependencies_table(conn):
    dummy_data = (
        (1, 'Package 1', '0.1', 'CVE 1', 'https://google.com/search?q=1', 'License 1', 'https://google.com/search?q=1'),
        (2, 'Package 2', '0.2', 'CVE 2', 'https://google.com/search?q=2', 'License 2', 'https://google.com/search?q=2'),
        (3, 'Package 3', '0.3', 'CVE 3', 'https://google.com/search?q=3', 'License 3', 'https://google.com/search?q=3'),
        (4, 'Package 4', '0.4', 'CVE 4', 'https://google.com/search?q=4', 'License 4', 'https://google.com/search?q=4'),
    )
    cursor = conn.cursor()
    # check if data exists in the table already
    cursor.execute("SELECT * FROM dm_componentdeps;")
    rows = cursor.fetchall()
    if not rows or len(rows) < 1:
        for data_point in dummy_data:
            cursor.execute(f"INSERT INTO dm_componentdeps VALUES (%s, %s, %s, %s, %s, %s, %s)", data_point)
            print(f"Inserted {str(data_point)} into table dm_componentdeps")
    conn.commit()  # to make the insertions made by 'seed_dependencies_table' persistent
    cursor.close()
