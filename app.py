import flask
import openai
import PyPDF2
import json

app = flask.Flask(__name__)

openai.api_key = "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"


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/questions', methods=['POST'])
def questions():
    # read file and get the query
    file = flask.request.files['resume']
    pdfReader = PyPDF2.PdfReader(file)
    resume = ""
    for i in range(len(pdfReader.pages)):
        resume += pdfReader.pages[i].extract_text()
    content = """{resume}
    --------------------------

Given the above resume, generate 10 technical questions that can be asked to the candidate in an interview setting. 
Some of them have to be general and some specific. 
Assume mid-level candidate with 2-3 years of experience. 
Also provide the category of the question and the skills it is testing for. 
Answer MUST be in JSON format with the following structure:
{{
    "questions": [
        {{
            "question": "What is the difference between supervised and unsupervised learning?",
            "category": "ML",
            "skills": ["ML", "supervised learning", "unsupervised learning"]
        }},
    ]
}}
"""

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a principal data scientist/software engineer who is technically proficient. Also provide the category of the question and the skills it is testing for"},
            {"role": "user", "content": content.format(resume=resume)}
        ]
    )
    questions = completion['choices'][0]['message']['content']
    with open('questions.json', 'w') as f:
        f.write(questions)
    answer = json.loads(questions)
    # questions = question.split('\n')
    # return str(answer)
    return flask.render_template('questions.html', questions=dict(answer)['questions'])


if __name__ == '__main__':
    app.run(debug=True)
