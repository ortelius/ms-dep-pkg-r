import os
from http import HTTPStatus
from typing import List, Optional

import psycopg2
import psycopg2.extras
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import create_engine

# Init Globals
service_name = 'ortelius-ms-dep-pkg-r'

app = FastAPI(
    title=service_name,
    description=service_name
)

# Init db connection
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "postgres")
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASS", "postgres")
db_port = os.getenv("DB_PORT", "5432")
validateuser_url = os.getenv("VALIDATEUSER_URL", "http://localhost:5000")

engine = create_engine("postgresql+psycopg2://" + db_user + ":" + db_pass + "@" + db_host + ":" + db_port + "/" + db_name)

# health check endpoint


class StatusMsg(BaseModel):
    status: str
    service_name: Optional[str] = None


@app.get("/health",
         responses={
             503: {"model": StatusMsg,
                   "description": "DOWN Status for the Service",
                   "content": {
                       "application/json": {
                           "example": {"status": 'DOWN'}
                       },
                   },
                   },
             200: {"model": StatusMsg,
                   "description": "UP Status for the Service",
                   "content": {
                       "application/json": {
                           "example": {"status": 'UP', "service_name": service_name}
                       }
                   },
                   },
         }
         )
async def health(response: Response):
    try:
        with engine.connect() as connection:
            conn = connection.connection
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            if cursor.rowcount > 0:
                return {"status": 'UP', "service_name": service_name}
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": 'DOWN'}

    except Exception as err:
        print(str(err))
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": 'DOWN'}
# end health check


class DepPkg(BaseModel):
    packagename: str
    packageversion: str
    name: str
    url: str
    summary: str


class DepPkgs(BaseModel):
    data: List[DepPkg]


class Message(BaseModel):
    detail: str


@app.get('/msapi/deppkg',
         responses={
             401: {"model": Message,
                   "description": "Authorization Status",
                   "content": {
                       "application/json": {
                           "example": {"detail": "Authorization failed"}
                       },
                   },
                   },
             500: {"model": Message,
                   "description": "SQL Error",
                   "content": {
                       "application/json": {
                           "example": {"detail": "SQL Error: 30x"}
                       },
                   },
                   },
             200: {
                 "model": DepPkgs,
                 "description": "Component Paackage Dependencies"},
             "content": {
                 "application/json": {
                     "example": {"data": [{"packagename": "Flask", "packageversion": "1.2.2", "name": "BSD-3-Clause", "url": "https://spdx.org/licenses/BSD-3-Clause.html", "summary": ""}]}
                 }
             }
         }
         )
async def getCompPkgDeps(request: Request, compid: int, deptype: str = Query(..., regex="(?:license|cve)")):
    try:
        result = requests.get(validateuser_url + "/msapi/validateuser", cookies=request.cookies)
        if (result is None):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization Failed")

        if (result.status_code != status.HTTP_200_OK):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization Failed status_code=" + str(result.status_code))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization Failed:" + str(err)) from None

    response_data = []

    try:
        with engine.connect() as connection:
            conn = connection.connection
            cursor = conn.cursor()

            sql = "SELECT packagename, packageversion, name, url, summary FROM dm_componentdeps where compid = %s and deptype = %s"

            params = tuple([compid, deptype])
            cursor.execute(sql, params)
            rows = cursor.fetchall()
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

    except HTTPException:
        raise
    except Exception as err:
        print(str(err))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from None

