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

import logging
import os
import socket
from time import sleep
from typing import List, Optional

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel  # pylint: disable=E0611
from sqlalchemy import create_engine
from sqlalchemy.exc import InterfaceError, OperationalError


def isBlank(myString):
    return not (myString and myString.strip())


# Init Globals
service_name = "ortelius-ms-dep-pkg-r"
db_conn_retry = 3

app = FastAPI(title=service_name, description=service_name)

# Init db connection
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "postgres")
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASS", "postgres")
db_port = os.getenv("DB_PORT", "5432")
validateuser_url = os.getenv("VALIDATEUSER_URL", "")

if len(validateuser_url) == 0:
    validateuser_host = os.getenv("MS_VALIDATE_USER_SERVICE_HOST", "127.0.0.1")
    host = socket.gethostbyaddr(validateuser_host)[0]
    validateuser_url = "http://" + host + ":" + str(os.getenv("MS_VALIDATE_USER_SERVICE_PORT", 80))  # Devskim: ignore DS137138

engine = create_engine("postgresql+psycopg2://" + db_user + ":" + db_pass + "@" + db_host + ":" + db_port + "/" + db_name, pool_pre_ping=True)


# health check endpoint
class StatusMsg(BaseModel):
    status: str
    service_name: str


@app.get("/health")
async def health(response: Response) -> StatusMsg:
    try:
        with engine.connect() as connection:
            conn = connection.connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            if cursor.rowcount > 0:
                return StatusMsg(status="UP", service_name=service_name)
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return StatusMsg(status="DOWN", service_name=service_name)

    except Exception as err:
        print(str(err))
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StatusMsg(status="DOWN", service_name=service_name)


# end health check


class DepPkg(BaseModel):
    packagename: str
    packageversion: str
    pkgtype: str
    name: str
    url: str
    summary: str
    fullcompname: str
    risklevel: str


class DepPkgs(BaseModel):
    data: List[DepPkg]


@app.get("/msapi/deppkg")
async def getCompPkgDeps(
    request: Request,
    compid: Optional[int] = None,
    appid: Optional[int] = None,
    deptype: str = Query(..., regex="(?:license|cve)"),
) -> DepPkgs:
    try:
        result = requests.get(validateuser_url + "/msapi/validateuser", cookies=request.cookies)
        if result is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization Failed")

        if result.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization Failed status_code=" + str(result.status_code),
            )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Failed:" + str(err),
        ) from None

    response_data = DepPkgs(data=list())

    try:
        # Retry logic for failed query
        no_of_retry = db_conn_retry
        attempt = 1
        while True:
            try:
                with engine.connect() as connection:
                    conn = connection.connection
                    cursor = conn.cursor()

                    sqlstmt = ""
                    id = compid
                    if compid is not None:
                        sqlstmt = "SELECT packagename, packageversion, name, url, summary, '', purl, pkgtype FROM dm_componentdeps where compid = %s and deptype = %s"
                    elif appid is not None:
                        sqlstmt = "select distinct b.packagename, b.packageversion, b.name, b.url, b.summary, fulldomain(c.domainid, c.name), b.purl, b.pkgtype from dm.dm_applicationcomponent a, dm.dm_componentdeps b, dm.dm_component c where appid = %s and a.compid = b.compid and c.id = b.compid and b.deptype = %s"
                        id = appid

                    params = tuple([id, "license"])
                    cursor.execute(sqlstmt, params)
                    rows = cursor.fetchall()
                    valid_url = {}

                    for row in rows:
                        packagename = row[0]
                        packageversion = row[1]
                        name = row[2]
                        url = row[3]
                        summary = row[4]
                        fullcompname = row[5]
                        purl = row[6]
                        pkgtype = row[7] if row[7] else ""

                        if deptype == "license":
                            if not url:
                                url = "https://spdx.org/licenses/"

                            # check for license on SPDX site if not found just return the license landing page
                            if name not in valid_url:
                                r = requests.head(url)
                                if r.status_code == 200:
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
                                )
                            )
                        else:
                            v_sql = ""
                            if isBlank(purl):
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
                                cve_id = str(v_row[0])
                                summary = v_row[1]
                                risklevel = v_row[2]

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
                                    )
                                )
                            v_cursor.close()

                    cursor.close()
                    return response_data

            except (InterfaceError, OperationalError) as ex:
                if attempt < no_of_retry:
                    sleep_for = 0.2
                    logging.error("Database connection error: {} - sleeping for {}s" " and will retry (attempt #{} of {})".format(ex, sleep_for, attempt, no_of_retry))
                    # 200ms of sleep time in cons. retry calls
                    sleep(sleep_for)
                    attempt += 1
                    continue
                else:
                    raise

    except HTTPException:
        raise
    except Exception as err:
        print(str(err))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from None


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5004)
