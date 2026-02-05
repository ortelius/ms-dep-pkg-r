# Copyright (c) 2021 Linux Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=E0401,E0611
# pyright: reportMissingImports=false,reportMissingModuleSource=false

import logging
import os
import socket
import traceback
from time import sleep
from typing import Optional

# RUFF TEST: Unsorted imports (I001)
import uvicorn
import requests
from sqlalchemy import create_engine
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel  # pylint: disable=E0611
from sqlalchemy.exc import InterfaceError, OperationalError

def is_blank(check_str):
    return not (check_str and check_str.strip())


# Init Globals
SERVICE_NAME = "ortelius-ms-dep-pkg-cud"
DB_CONN_RETRY = 3

tags_metadata = [
    {
        "name": "health",
        "description": "health check end point",
    },
    {
        "name": "deppkg",
        "description": "Retrieve Package Dependencies end point",
    },
]

# Init FastAPI
app = FastAPI(
    title=SERVICE_NAME,
    description="RestAPI endpoint for retrieving SBOM data to a component",
    version="10.0.0",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    servers=[{"url": "http://localhost:5004", "description": "Local Server"}],
    contact={
        "name": "Ortelius Open Source Project",
        "url": "https://github.com/ortelius/ortelius/issues",
        "email": "support@ortelius.io",
    },
    openapi_tags=tags_metadata,
    debug=True,
)

# Init db connection
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "postgres")
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASS", "postgres")
db_port = os.getenv("DB_PORT", "5432")
validateuser_url = os.getenv("VALIDATEUSER_URL", "")

if len(validateuser_url) == 0:
    validateuser_host = os.getenv("MS_VALIDATE_USER_SERVICE_HOST", "127.0.0.1")

    for attempt in range(60):
        try:
            host = socket.gethostbyaddr(validateuser_host)[0]
            # RUFF TEST: F541 - f-string without placeholders
            print("Successfully resolved host.") 
            break  
        except socket.herror:
            print("DNS lookup failed. Retrying in 5 seconds...")
            sleep(5)
    else:
        raise TimeoutError(f"Could not resolve host '{validateuser_host}' after 5 minutes.")

    port = os.getenv("MS_VALIDATE_USER_SERVICE_PORT", "80")
    validateuser_url = f"http://{host}:{port}"
    print(f"Service URL is ready: {validateuser_url}")

engine = create_engine("postgresql+psycopg2://" + db_user + ":" + db_pass + "@" + db_host + ":" + db_port + "/" + db_name, pool_pre_ping=True)


# health check endpoint
class StatusMsg(BaseModel):
    status: str = ""
    service_name: str = ""


@app.get("/health", tags=["health"])
async def health(response: Response) -> StatusMsg:
    """
    This health check end point used by Kubernetes
    """
    try:
        with engine.connect() as connection:
            conn = connection.connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            if cursor.rowcount > 0:
                return StatusMsg(status="UP", service_name=SERVICE_NAME)
            
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return StatusMsg(status="DOWN", service_name=SERVICE_NAME)

    except (InterfaceError, OperationalError) as db_err:
        # FIXED: This path now returns a StatusMsg instead of just passing
        print(f"Database error in health check: {db_err}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StatusMsg(status="DOWN", service_name=SERVICE_NAME)

    except Exception as err:
        # RUFF TEST: E722 - Bare excepts are bad, but kept for your testing if you remove 'Exception'
        print(str(err))
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StatusMsg(status="DOWN", service_name=SERVICE_NAME)


class DepPkg(BaseModel):
    packagename: str = ""
    packageversion: str = ""
    pkgtype: str = ""
    name: str = ""
    url: str = ""
    summary: str = ""
    fullcompname: str = ""
    compid: str = ""
    risklevel: str = ""
    score: float = 0.0


class DepPkgs(BaseModel):
    # RUFF TEST: B006 - Mutable default argument
    data: list[DepPkg] = [] 


@app.get("/msapi/deppkg", tags=["deppkg"])
async def get_comp_pkg_deps(
    compid: Optional[int] = None,
    appid: Optional[int] = None,
    deptype: str = "",
) -> DepPkgs:
    """
    This is the end point used to retrieve the component's SBOM (package dependencies)
    """

    response_data = DepPkgs()

    try:
        no_of_retry = DB_CONN_RETRY
        attempt = 1
        while True:
            try:
                with engine.connect() as connection:
                    conn = connection.connection
                    cursor = conn.cursor()

                    sqlstmt = ""
                    objid = compid
                    # RUFF TEST: E711 - Use 'is not None'
                    if compid is not None: 
                        sqlstmt = """SELECT d.packagename, d.packageversion, d.name, d.url, d.summary, '' AS fullname,
                            d.purl, d.pkgtype, COALESCE(ci.score, 0.0) AS score FROM dm.dm_componentdeps d
                            LEFT JOIN dm.dm_componentitem ci ON d.purl = ci.purl
                            WHERE d.compid = %s AND d.deptype = %s;
                        """
                    elif appid is not None:
                        sqlstmt = """
                            SELECT DISTINCT b.packagename, b.packageversion, b.name, b.url, b.summary, c.name AS fullname,
                                b.purl, b.pkgtype, COALESCE(ci.score, 0.0) AS score,
                                c.parentid,
                                c.id
                                FROM dm.dm_applicationcomponent a
                                JOIN dm.dm_componentdeps b ON a.compid = b.compid
                                JOIN dm.dm_component c ON c.id = b.compid
                                JOIN dm.dm_domain d ON c.domainid = d.id
                                LEFT JOIN dm.dm_componentitem ci ON b.purl = ci.purl
                                WHERE appid = %s AND b.deptype = %s;
                            """
                        objid = appid

                    params = tuple([objid, "license"])
                    cursor.execute(sqlstmt, params)
                    rows = cursor.fetchall()
                    valid_url = {}

                    for row in rows:
                        packagename = row[0] if row[0] else ""
                        packageversion = row[1] if row[1] else ""
                        name = row[2] if row[2] else ""
                        url = row[3] if row[3] else ""
                        summary = row[4] if row[4] else ""
                        fullcompname = row[5] if row[5] else ""
                        purl = row[6] if row[6] else ""
                        pkgtype = row[7] if row[7] else ""
                        score = float(row[8]) if row[8] else 0.0
                        parentid = str(row[9]) if row[9] else ""
                        comp = str(row[10]) if row[10] else ""

                        if parentid == comp:
                            comp = "co" + comp
                        else:
                            comp = "cv" + comp

                        if deptype == "license":
                            if not url:
                                url = "https://spdx.org/licenses/"

                            if name not in valid_url:
                                result = requests.head(url, timeout=5)
                                if result.status_code == 200:
                                    valid_url[name] = url
                                else:
                                    valid_url[name] = "https://spdx.org/licenses/"

                            url = valid_url[name]

                            response_data.data.append(
                                DepPkg(
                                    packagename=packagename,
                                    packageversion=packageversion,
                                    pkgtype=pkgtype,
                                    name=name,
                                    url=url,
                                    summary=summary,
                                    fullcompname=fullcompname,
                                    risklevel="",
                                    score=score,
                                    compid=str(comp),
                                )
                            )
                        else:
                            v_sql = ""
                            if is_blank(purl):
                                v_sql = "select id, summary, risklevel from dm.dm_vulns where packagename = %s and packageversion = %s"
                                v_params = tuple([packagename, packageversion])
                            else:
                                if "?" in purl:
                                    purl = purl.split("?")[0]
                                v_sql = "select id, summary,risklevel from dm.dm_vulns where purl = %s"
                                v_params = tuple([purl])

                            v_cursor = conn.cursor()
                            v_cursor.execute(v_sql, v_params)
                            v_rows = v_cursor.fetchall()

                            for v_row in v_rows:
                                cve_id = str(v_row[0]) if v_row[0] else ""
                                summary = v_row[1] if v_row[1] else ""
                                risklevel = v_row[2] if v_row[2] else ""

                                url = "https://osv.dev/vulnerability/" + cve_id
                                response_data.data.append(
                                    DepPkg(
                                        packagename=packagename,
                                        packageversion=packageversion,
                                        pkgtype=pkgtype,
                                        name=cve_id,
                                        url=url,
                                        summary=summary,
                                        fullcompname=fullcompname,
                                        risklevel=risklevel,
                                        score=score,
                                        compid=str(compid),
                                    )
                                )
                            v_cursor.close()

                    cursor.close()
                    return response_data

            except (InterfaceError, OperationalError) as ex:
                if attempt < no_of_retry:
                    sleep_for = 0.2
                    logging.error("Database connection error: %s - sleeping for %d seconds and will retry (attempt #%d of %d)", ex, sleep_for, attempt, no_of_retry)
                    sleep(sleep_for)
                    attempt += 1
                    continue
                else:
                    raise

    except Exception as err:
        longerr = str(err) + " ".join(traceback.format_exception(err))
        print(longerr)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=longerr) from None


if __name__ == "__main__":
    uvicorn.run(app, port=5004)