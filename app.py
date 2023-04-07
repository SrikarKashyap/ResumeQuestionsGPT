import flask
import openai
import PyPDF2
import json
# from presidio_analyzer import AnalyzerEngine
# from presidio_anonymizer import AnonymizerEngine
import spacy
import os
import re
import time


app = flask.Flask(__name__)

openai.api_key = "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"

command = "python -m spacy download en_core_web_sm"

os.system(command)


@app.route('/')
def index():
    return flask.render_template('index.html')


def anonymize_text(text):
    model = spacy.load("en_core_web_sm")
    doc = model(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            text = text.replace(ent.text, "John Doe")
    return text

#     analyzer = AnalyzerEngine()
#     anonymizer = AnonymizerEngine()
#     results = analyzer.analyze(text=text,
#                                entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "LOCATION", "CREDIT_CARD",
#                                          "DOMAIN_NAME", "IP_ADDRESS"],
#                                language='en')
#     anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)

#     return anonymized_text.text


def process_and_identify(text):
    # regular expressions
    email_re = r"[\w\.-]+@[\w\.-]+"
    phone_re = r"\+?\d[\d -]{5,15}\d"
    url_re = r"(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)"
    ssn_re = r"\d{3}-\d{2}-\d{4}"
    pan_re = r"[A-Z]{5}[0-9]{4}[A-Z]{1}"
    aadhar_re = r"\d{4}\s\d{4}\s\d{4}"
    # find all emails, phones and urls
    emails = re.findall(email_re, text)
    phones = re.findall(phone_re, text)
    urls = re.findall(url_re, text)
    ssns = re.findall(ssn_re, text)
    pans = re.findall(pan_re, text)
    aadhars = re.findall(aadhar_re, text)
    # remove emails, phones and urls from text
    text = re.sub(email_re, '<EMAIL>', text)
    text = re.sub(phone_re, '<PHONE>', text)
    text = re.sub(url_re, '<URL>', text)
    text = re.sub(ssn_re, '<SSN>', text)
    text = re.sub(pan_re, '<PAN>', text)
    text = re.sub(aadhar_re, '<AADHAR>', text)

    return text


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
    start_anon = time.time()
    resume = process_and_identify(resume)
    resume = anonymize_text(resume)
    end_anon = time.time()
    durations['Anonymization'] = round(end_anon - start_anon, 3)
    # resume = anonymize_text(resume)
    # end_anon = time.time()
    # durations['anon'] = end_anon - start_anon
    # with open('processed_resume.txt', 'w', encoding='utf8') as f:
    #     f.write(resume)
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
    # with open('questions.json', 'w') as f:
    #     f.write(questions)
    try:
        answer = json.loads(questions)
    except Exception as e:
        answer = {"questions": []}
    end_gpt = time.time()
    durations['ChatGPT API Request'] = round(end_gpt - start_gpt, 3)
    return flask.render_template('questions.html', questions=dict(answer)['questions'], durations=durations)


if __name__ == '__main__':
    app.run(debug=True)
