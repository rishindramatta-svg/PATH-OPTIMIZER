from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Base, engine, SessionLocal, User, Concept, Question, Mastery, Interaction, Misconception
from .seed import seed
from .learning import bkt_update, calibration_label
import hashlib, hmac, os, random

app = FastAPI(title="PNG9 Learning Path Optimizer", version="0.1.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET","POST"], allow_headers=["Content-Type","Authorization"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def startup(): seed()

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/api/courses")
def courses(db: Session = Depends(get_db)):
    return [{"id":"python-foundations","title":"Python Programming","conceptCount":db.query(Concept).count()}]

@app.get("/api/courses/python-foundations/graph")
def graph(db: Session = Depends(get_db)):
    concepts = db.scalars(select(Concept).order_by(Concept.order)).all()
    return {"concepts":[{"id":c.slug,"title":c.title,"description":c.description,"prerequisites":c.prerequisites,"order":c.order} for c in concepts]}

@app.post("/api/auth/register")
def register(body: dict, db: Session = Depends(get_db)):
    email = str(body.get("email", "")).strip().lower(); password = str(body.get("password", ""))
    if "@" not in email or len(password) < 8: raise HTTPException(422,"Enter a valid email and a password of at least 8 characters")
    if db.scalar(select(User).where(User.email == email)): raise HTTPException(409,"Email already registered")
    user = User(email=email, hashed_password=hashlib.sha256(password.encode()).hexdigest()); db.add(user); db.commit(); db.refresh(user)
    return {"accessToken":f"dev-{user.id}","user":{"id":user.id,"email":email,"role":user.role}}

@app.get("/api/questions/next")
def next_question(db: Session = Depends(get_db)):
    q = db.scalar(select(Question).order_by(Question.id).limit(1))
    return {"id":q.id,"conceptId":q.concept_slug,"prompt":q.prompt,"options":q.options}

class AnswerIn(BaseModel):
    questionId: int
    answer: str = Field(max_length=500)
    confidence: int = Field(ge=1, le=5)
    timeTakenMs: int = Field(ge=0, le=3600000)
    userId: int = Field(default=1, ge=1)

@app.post("/api/interactions")
def interact(body: AnswerIn, db: Session = Depends(get_db)):
    q = db.get(Question, body.questionId)
    if not q: raise HTTPException(404,"Question not found")
    try: selected = int(body.answer)
    except ValueError: raise HTTPException(422,"Answer must be an option index")
    if selected not in range(len(q.options)): raise HTTPException(422,"Answer option is out of range")
    user = db.get(User, body.userId)
    if not user:
        user = User(id=body.userId,email=f"student{body.userId}@local.test",hashed_password="",role="student"); db.add(user); db.flush()
    correct = selected == q.correct_index
    prior = db.scalar(select(Mastery).where(Mastery.user_id==user.id,Mastery.concept_slug==q.concept_slug))
    if not prior: prior = Mastery(user_id=user.id,concept_slug=q.concept_slug,probability=.2); db.add(prior)
    flagged = body.timeTakenMs < 2000
    if not flagged:
        prior.probability = bkt_update(prior.probability, correct)
    prior.confidence=body.confidence
    db.add(Interaction(user_id=user.id,question_id=q.id,answer=body.answer,correct=correct,confidence=body.confidence,time_taken_ms=body.timeTakenMs,flagged=flagged))
    found = None
    if not correct and q.misconception_ids[selected]:
        key=q.misconception_ids[selected]; found=db.scalar(select(Misconception).where(Misconception.user_id==user.id,Misconception.key==key))
        if not found: found=Misconception(user_id=user.id,concept_slug=q.concept_slug,key=key,title=key.replace('_',' ').title()); db.add(found)
        found.severity=min(5,found.severity+1+(body.confidence>=4)); found.status="repairing" if body.confidence>=4 else "active"
    db.commit()
    concepts=db.scalars(select(Concept).order_by(Concept.order)).all()
    mastery={m.concept_slug:m.probability for m in db.scalars(select(Mastery).where(Mastery.user_id==user.id)).all()}
    active=db.scalars(select(Misconception).where(Misconception.user_id==user.id,Misconception.status!="resolved")).all()
    path=[]
    for c in concepts:
        if mastery.get(c.slug,.2)<.75 and all(mastery.get(p,.2)>=.6 for p in c.prerequisites):
            path.append({"conceptId":c.slug,"title":c.title,"reason":"Strengthen this concept before moving forward"}); break
    return {"correct":correct,"mastery":prior.probability,"calibrationGap":body.confidence/5-prior.probability,"calibrationLabel":calibration_label(body.confidence,prior.probability),"flagged":flagged,"misconception":({"title":found.title,"severity":found.severity,"status":found.status,"explanation":q.explanation} if found else None),"path":path,"feedback":q.explanation}

@app.get("/api/learner/state")
def learner_state(userId:int=1, db:Session=Depends(get_db)):
    concepts=db.scalars(select(Concept).order_by(Concept.order)).all(); mastery={m.concept_slug:m.probability for m in db.scalars(select(Mastery).where(Mastery.user_id==userId)).all()}
    return {"mastery":[{"conceptId":c.slug,"title":c.title,"probability":mastery.get(c.slug,.2)} for c in concepts],"averageMastery":sum(mastery.values())/len(mastery) if mastery else 0,"streak":0}

@app.get("/api/misconceptions")
def misconceptions(userId:int=1, db:Session=Depends(get_db)):
    return [{"id":m.id,"conceptId":m.concept_slug,"title":m.title,"severity":m.severity,"status":m.status} for m in db.scalars(select(Misconception).where(Misconception.user_id==userId)).all()]
