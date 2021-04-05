from flask import Flask, render_template, redirect, url_for, request, jsonify
import json

app = Flask(__name__)

@app.route('/', methods=['GET'])
def result():
    numbers = request.args.get('numbers', "10, 1, 200, -19, 21, 321, 0, 200")
    try:
        num_list = [int(y.strip()) for y in numbers.split(',')]
    except Exception as e:
        return jsonify({'message': 'Pass only numbers, seperated by commas (,).'}), 400
    result = Bubble_sort(num_list)
    return jsonify(result)


def Bubble_sort(num_list):
    for i in range(len(num_list)):
        for j in range(len(num_list)):
            if num_list[i] < num_list[j]:
                swap = num_list[i]
                num_list[i] = num_list[j]
                num_list[j] = swap
    return num_list

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)