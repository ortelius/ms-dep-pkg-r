# ortelius-ms-dep-pkg-r
Dependency Package Data Microservice - Read

This is a flask web application which sorts a list of numbers and returns the sorted form as a json string. 

# Dockerization
The flask application has been dockerized and can be ustilized by following the steps below;
- Clone the repository on your local computer
- Build the docker image using the following command
 `docker build -t flask-bubble-sort .`
- Run the docker on local machine by executing the following command 
 `docker run -p 5000:5000 -d flask-bubble-sort`
- You should be able to access the webpage at [localhost:5000](http://www.localhost:5000/)
