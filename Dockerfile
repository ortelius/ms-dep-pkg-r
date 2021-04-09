#initialize a base image
FROM python:3.8.2-alpine
ADD requirements.txt .
#install the dependencies of the flask app
RUN pip install -r requirements.txt
#define present working directory
WORKDIR /code/
#copy content into working directory
ADD . /code
EXPOSE 5000
#define the cimmand to start the container
CMD ["python", "bubble.py"]
