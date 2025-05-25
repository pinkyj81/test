from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '안녕하세요!'

if __name__ == '__main__':
    app.run(debug=True)
