#import libraries and modules
from flask import Flask, request, jsonify #library for developing the web application
import json #module to parse json data

# create an app instance
app = Flask(__name__)

#create the endpoint '/' 
@app.route('/', methods=['GET'])
def result():
    #default string of numbers that will be sorted by the app
    numbers = request.args.get('numbers', "10, 1, 200, -19, 21, 321, 0, 200")
    try:
        num_list = [int(y.strip()) for y in numbers.split(',')] #separate the numbers in the string and save in a list
    except Exception as e:
        return jsonify({'message': 'Pass only numbers, seperated by commas (,).'}), 400
    #sort the numbers using Bubble_sort function and store the result
    result = Bubble_sort(num_list)
    #return a json string of the text
    return jsonify(result)


def Bubble_sort(num_list):
    """ Sorts a list of numbers and returns the sorted list.

    Args:
        num_list(list) : list of numbers to be sorted
    Returns:
        num_list(list) : the sorted list
    """
    for i in range(len(num_list)):
        for j in range(len(num_list)):
            if num_list[i] < num_list[j]:
                swap = num_list[i]
                num_list[i] = num_list[j]
                num_list[j] = swap
    return num_list

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
