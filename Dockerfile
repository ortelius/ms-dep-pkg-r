FROM python:3.8.2-alpine
ADD requirements.txt .
RUN pip install -r requirements.txt
WORKDIR /code/
ADD . /code
EXPOSE 5000
CMD ["python", "bubble.py"]
