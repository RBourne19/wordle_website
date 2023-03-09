from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from requests import RequestException
from sqlalchemy import Column, Integer, String, Float, DateTime, asc, desc
from datetime import datetime, date
from twilio.twiml.messaging_response import MessagingResponse
import math
import inflect

app = Flask(__name__, template_folder="\\ADKWORDLE\\templates", static_folder="\\ADKWORDLE\\static")
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////ADKWORDLE/flask/users.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class users(db.Model):
    id = Column('user_id', Integer, primary_key = True)
    userName = Column(String(100), nullable = True)
    phoneNumber = Column(String(12), nullable = True)
    joinStatus = Column(String(10), nullable = True)
    todayGuess = Column(Integer, nullable = True)
    totalGuess = Column(Integer)
    avgGuess = Column(Float)
    totalScore = Column(Integer)
    guessDate = Column(DateTime, nullable = True)
    guessOutline = Column(String(100), nullable = True)
    guessString = Column(String(1))
    
    def __init__(self, userName, phoneNumber, joinStatus, todayGuess, totalGuess, avgGuess, totalScore, guessDate, guessOutline, guessString):
        self.userName = userName
        self.phoneNumber = phoneNumber
        self.joinStatus = joinStatus
        self.todayGuess = todayGuess
        self.totalGuess = totalGuess
        self.avgGuess = avgGuess
        self.totalScore = totalScore
        self.guessDate = guessDate
        self.guessOutline = guessOutline
        self.guessString = guessString

def phoneFind(phoneNumber):
    user = users.query.filter(users.phoneNumber == phoneNumber).first()
    return user

def todayRank(user):
    people = users.query.filter(users.todayGuess != 0).order_by(users.todayGuess)
    for idx, search in enumerate(people):
        if(user.id == search.id):
            return idx + 1
def avgRank(user):
    people = users.query.filter(users.avgGuess != 0).order_by(users.avgGuess)
    for idx, search in enumerate(people):
        if(user.id == search.id):
            return idx + 1
    return 0
def stringRank(rank):
    p = inflect.engine()
    return p.ordinal(rank)

@app.route('/player/<int:var>')
def player(var):
    viewPerson = users.query.filter(users.id == var).first()
    personRank = todayRank(viewPerson)
    avg = avgRank(viewPerson)
    strRank = stringRank(personRank)
    strAvgRank = stringRank(avg)
    return render_template('playerView.html', user = viewPerson, rank = strRank, strAvgRank = strAvgRank)

@app.route("/")
def index():
    people = users.query.filter(users.todayGuess != 0).order_by(users.todayGuess)
    avgPeople = users.query.filter(users.avgGuess != 0).order_by(users.avgGuess)
    return render_template("view.html", users = people, avgUsers = avgPeople)

@app.route("/sms", methods=['GET','POST'])
def sms():
    resp = MessagingResponse()
    number = request.values.get('From')
    message_body = request.values.get('Body')
    if "join adk" in message_body.lower():
        if phoneFind(number) == None:
            newUser = users(None, number, "joinedNoName", 0,0,0,0, None, None, "NA")
            db.session.add(newUser)
            db.session.commit()
            
            resp.message("You have joined Group: ADK\nPlease enter your firstname and last initial.")
        else:
            resp.message("You have already joined the group")

    elif phoneFind(number) != None:
        user = phoneFind(number)
        if "joinedNoName" in user.joinStatus:
            user.userName = message_body
            user.joinStatus = "Joined"
            db.session.commit()
            resp.message("Thank you " + user.userName + " for joining")
            
        if "Joined" in user.joinStatus:
            if "Wordle" in message_body:
                if(user.guessDate != None):
                    userDate = user.guessDate.strftime("%d/%m/%Y")
                    tod = datetime.today().strftime("%d/%m/%Y")
                    if userDate == tod:
                        resp.message("You have already guessed today")
                else:

                    slashIndex = int(message_body.index("/"))

                    score = message_body[slashIndex - 1:slashIndex]
                    user.guessString = score
                    if "X" in score:
                        score = 7
                    else:
                        score = int(score)
                    user.totalGuess = user.totalGuess + 1

                    user.todayGuess = score
                    user.totalScore = user.totalScore + score
                    user.avgGuess = math.floor(float(user.totalScore/user.totalGuess) *100)/100.0
                    
                    user.guessDate = datetime.today()
                    message_body = message_body[message_body.rindex(" "):]
                    user.guessOutline = message_body[5:]
                    db.session.commit()
                    message = "Well Done!\n"
                    message += "View everyone's stats at: www.adkwordle.com\n"
                    message += ("View your stats at: www.adkwordle.com/player/" + str(user.id))
                    resp.message(message)
    return str(resp)

def reset():
    people = users.query.all()
    
    for user in people:
        user.todayGuess = 0
        user.guessDate = None
        user.guessOutline = None
        db.session.commit()
    print("RESET")

#daily reset timer
scheduler = BackgroundScheduler()
scheduler.add_job(func=reset, trigger="interval", days= 1, start_date='2022-06-15 00:00:00')
scheduler.start()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run('0.0.0.0', port=5000, debug = True)