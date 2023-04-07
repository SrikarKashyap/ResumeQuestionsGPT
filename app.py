import flask
import openai
import PyPDF2
import json
# from presidio_analyzer import AnalyzerEngine
# from presidio_anonymizer import AnonymizerEngine
import os
import time


app = flask.Flask(__name__)

openai.api_key = "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"

# command = "python -m spacy download en_core_web_lg"

# os.system(command)


@app.route('/')
def index():
    return flask.render_template('index.html')


# def anonymize_text(text):
#     analyzer = AnalyzerEngine()
#     anonymizer = AnonymizerEngine()
#     results = analyzer.analyze(text=text,
#                                entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "LOCATION", "CREDIT_CARD",
#                                          "DOMAIN_NAME", "IP_ADDRESS"],
#                                language='en')
#     anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)

#     return anonymized_text.text


@app.route('/questions', methods=['POST'])
def questions():
    durations = {}
    file = flask.request.files['resume']
    additional_info = flask.request.form['additional-text']
    start_pdf = time.time()
    pdfReader = PyPDF2.PdfReader(file)
    resume = ""
    for i in range(len(pdfReader.pages)):
        resume += pdfReader.pages[i].extract_text()
    end_pdf = time.time()
    durations['PDF Parsing'] = round(end_pdf - start_pdf, 3)
    # start_anon = time.time()
    # resume = anonymize_text(resume)
    # end_anon = time.time()
    # durations['anon'] = end_anon - start_anon
    start_gpt = time.time()
    resume += "------------------\n"+additional_info+"\n------------------\n"
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
    try:
        answer = json.loads(questions)
    except Exception as e:
        answer = {"questions": []}
    end_gpt = time.time()
    durations['ChatGPT API Request'] = round(end_gpt - start_gpt, 3)
    return flask.render_template('questions.html', questions=dict(answer)['questions'], durations=durations)


if __name__ == '__main__':
    app.run(debug=False)
