from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import docx
from groq import Groq
import os
import re

app = FastAPI()

client = Groq(api_key="***")

DATABASE_URL = "sqlite:///./qnabase.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class QnaBase(Base):
    __tablename__ = "qnabase"
    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(Text)
    generated_output = Column(Text)

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    qna_id = Column(Integer)
    question_type = Column(Text)
    question_text = Column(Text)
    option1 = Column(Text, nullable=True)
    option2 = Column(Text, nullable=True)
    option3 = Column(Text, nullable=True)
    option4 = Column(Text, nullable=True)
    correct_option = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_mcqs(text: str):
    pattern = re.compile(
        r"(?P<question>\d+\.\s+.*?\?)\s*"
        r"a\)\s*(?P<a>.*?)\s*"
        r"b\)\s*(?P<b>.*?)\s*"
        r"c\)\s*(?P<c>.*?)\s*"
        r"d\)\s*(?P<d>.*?)\s*"
        r"(?:Correct Answer|Correct answer)[:\s]+(?P<correct>[abcdABCD])",
        re.DOTALL
    )

    results = []
    for match in pattern.finditer(text):
        results.append({
            "type": "mcq",
            "question": match.group("question").strip(),
            "choices": {
                "a": match.group("a").strip(),
                "b": match.group("b").strip(),
                "c": match.group("c").strip(),
                "d": match.group("d").strip(),
            },
            "correct_option": match.group("correct").strip().lower()
        })
    return results

def parse_shorts(text: str):
    short_section = ""
    match = re.search(r"(6\..*)", text, re.DOTALL)
    if match:
        short_section = match.group(1)
    else:
        return []

    # parssing descriptive questions 
    pattern = re.compile(
        r"(?P<q_num>[6-9]|10)\.\s*(?P<question>.*?)\s*\[Sample answer:\s*(?P<answer>.*?)\]",
        re.DOTALL | re.IGNORECASE
    )

    results = []
    for match in pattern.finditer(short_section):
        question = match.group("question").strip()
        answer = match.group("answer").strip()
        results.append({
            "type": "short",
            "question": question,
            "answer": answer
        })

    return results

'''

def parse_shorts(text: str):
    
    pattern = re.compile(
        r"(?:Q:\s*)?(?P<question>.*?)\s*(?:Sample Answer|Answer):\s*(?P<answer>.*?)(?=\nQ:|\n\d+\.\s|\Z)",
        re.DOTALL | re.IGNORECASE
    )

    results = []
    for match in pattern.finditer(text):
        question = match.group("question").strip()
        answer = match.group("answer").strip()
        if question:  # Optional: skip if no question
            results.append({
                "type": "short",
                "question": question,
                "answer": answer
            })
    return results
'''

@app.get("/")
async def root():
    return {"message": "program running"}

@app.post("/generate-questions/")
async def generate_questions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".docx"):
        return JSONResponse(content={"error": "Only .docx files allowed"}, status_code=400)

    try:
        contents = await file.read()
        with open("temp.docx", "wb") as f:
            f.write(contents)

        doc = docx.Document("temp.docx")
        text = "\n".join([para.text for para in doc.paragraphs])
        os.remove("temp.docx")

        # Calling Groq API
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[  
                
                {"role": "system", "content": "You are a helpful education assistant."},
                {"role": "user",
                  "content":
                        f"Generate exactly 5 multiple-choice questions (numbered 1-5) with 4 options each (a–d), and specify the correct answer like 'Correct answer: a'.\n"
                        f"Then, generate exactly 5 short-answer questions (numbered 6–10) each followed by '(Sample answer: ...)' in brackets.\n\n{text}"},
                            
            ],
            temperature=0.7,
        )

        generated = response.choices[0].message.content.strip()
        print("LLM raw response:\n", generated)

        # Save base entry
        db_entry = QnaBase(original_text=text, generated_output=generated)
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)

        # Parse MCQs and shorts
        mcqs = parse_mcqs(generated)  or []
        shorts = parse_shorts(generated)  or []
        print("Parsed SHORT ANSWERS:\n", shorts) 
        print("Parsed MCQs:", mcqs)
        print("Parsed Short Answers:", shorts)
      
        if mcqs:
         for q in mcqs:
            db.add(Question(
                qna_id=db_entry.id,
                question_type="mcq",
                question_text=q["question"],
                option1=q["choices"]["a"],
                option2=q["choices"]["b"],
                option3=q["choices"]["c"],
                option4=q["choices"]["d"],
                correct_option=q["correct_option"]
            ))
        if shorts:
         for q in shorts:
            db.add(Question(
                qna_id=db_entry.id,
                question_type="short",
                question_text=q["question"],
                answer_text=q["answer"]
            ))

        db.commit()
        return {"saved_id": db_entry.id}

    except Exception as e:
        print("Error:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/questions/{qna_id}")
def get_questions_by_test_id(qna_id: int, db: Session = Depends(get_db)):
    questions = db.query(Question).filter(Question.qna_id == qna_id).all()
    print(f"🧪 Loaded {len(questions)} questions for qna_id={qna_id}")
    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "type": q.question_type,
            "question": q.question_text,
            "choices": {
                "a": q.option1,
                "b": q.option2,
                "c": q.option3,
                "d": q.option4
            } if q.question_type == "mcq" else None,
            "correct_option": q.correct_option,
            "answer": q.answer_text
        })
    return result

from pydantic import BaseModel
from fastapi import FastAPI
from groq import Groq
import json

class EvalRequest(BaseModel):
    prompt: str
    expected: str
    student: str

@app.post("/evaluate-answer/")
async def evaluate_answer(data: EvalRequest):
    client = Groq(api_key="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")  
    full_prompt = f"""
You are a strict but fair evaluator.

Question:
{data.prompt}

Expected Answer:
{data.expected}

Student's Answer:
{data.student}

Give JSON output in this format: {{"score": float (0-5), "feedback": string}}
"""

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.2
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return result
    except:
        return {"score": 0.0, "feedback": "Could not parse Groq response."}



