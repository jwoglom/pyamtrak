from flask import Flask, request, jsonify
from amtrak import return_results

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    data = {i: data[i] for i in data}

    if data:
        results = return_results(**data)
        return jsonify(results)
    return jsonify({"error": "No arguments given."})

if __name__ == '__main__':
    app.run(debug=True)