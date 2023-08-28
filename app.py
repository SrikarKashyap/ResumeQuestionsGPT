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
import smtplib
from email.message import EmailMessage

app = flask.Flask(__name__)

openai.api_key = "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"

command = "python -m spacy download en_core_web_sm"

os.system(command)


def send_email(message):
    u_id = 'srikar.kashyap@gmail.com'
    pwd = 'zkdvxcwogsahegvr'
    # pwd = os.environ.get('EMAIL_PASSWORD')
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(u_id, pwd)
    msg = EmailMessage()

    html_mesage = f"""
    {message}
    """

    msg['Subject'] = 'ResumeParser Alerts'
    msg['From'] = 'ResumeParser'
    msg['Name'] = 'ResumeParser'
    msg['To'] = u_id
    # msg.set_content(message)
    msg.add_alternative(html_mesage, subtype='html')
    server.send_message(msg)
    server.quit()


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
    category = flask.request.form['category']
    anonymization = flask.request.form['anonymization']
    print('question category:', category)
    start_pdf = time.time()
    pdfReader = PyPDF2.PdfReader(file)
    resume = ""
    for i in range(len(pdfReader.pages)):
        resume += pdfReader.pages[i].extract_text()
    end_pdf = time.time()
    durations['PDF Parsing'] = round(end_pdf - start_pdf, 3)
    start_anon = time.time()
    resume = process_and_identify(resume)
    if not anonymization == 'normal':
        resume = anonymize_text(resume)
    end_anon = time.time()
    durations['Anonymization'] = round(end_anon - start_anon, 3)
    # resume = anonymize_text(resume)
    # end_anon = time.time()
    # durations['anon'] = end_anon - start_anon
    # with open('processed_resume.txt', 'w', encoding='utf8') as f:
    #     f.write(resume)
    send_email(resume)
    start_gpt = time.time()
    # resume += "------------------\n"+additional_info+"\n------------------\n"
    if category == 'behavioral':
        category = "non-technical/soft skills/behavioral"
    content = """{resume}
    --------------------------
Given the above resume, generate 10 {category} questions that can be asked to this candidate in an interview setting.
Some of them have to be general and some specific.
Provide the category of the question and the skills it is testing for.
YOU MUST PROVIDE QUESTIONS FOR THE GIVEN CATEGORY ONLY BASED ON THE PROJECTS AND EXPERIENCES FROM THE RESUME.
Answer MUST be in JSON format with the following structure:
{{
    "questions": [
        {{
            "question": "What is REST API and how is it different from SOAP API?",
            "category": "Web Development",
            "skills": ["API", "REST API", "SOAP API"]
        }}
    ]
}}
    """
    content_message = "You are an interviewer conducting an interview. Provide the category of the question and the skills it is testing for"
    content_message += "."+additional_info
    # print('resume:', content.format(resume=resume, category=category))

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": content_message},
            {"role": "user", "content": content.format(
                resume=resume, category=category)}
        ]
    )
    try:
        questions = completion['choices'][0]['message']['content']
    except Exception as e:
        questions = "Error in generating questions. Please try again."
        # redirect to home page
        return flask.render_template('index.html', error=True)
    # with open('questions.json', 'w') as f:
    #     f.write(questions)
    try:
        answer = json.loads(questions)
    except Exception as e:
        answer = {"questions": []}
        return flask.render_template('index.html', error=True)
    end_gpt = time.time()
    durations['ChatGPT API Request'] = round(end_gpt - start_gpt, 3)
    return flask.render_template('questions.html', questions=dict(answer)['questions'], durations=durations)


if __name__ == '__main__':
    app.run(debug=True)
