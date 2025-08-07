from flask import Flask, request, render_template
from transpiler import convert_c_to_python

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/transpile', methods=['POST'])
def transpile():
    data = request.get_json()
    c_code = data.get('code', '')
    python_code = convert_c_to_python(c_code)
    return python_code

if __name__ == '__main__':
    app.run(debug=True)
