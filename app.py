from flask import Flask, redirect, url_for, render_template, request, flash
from flask_mysqldb import MySQL
import requests
import bs4
from argon2 import PasswordHasher
import json

app=Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASS'] = ''
app.config['MYSQL_DB'] = 'wiremit'
app.secret_key = "flashes"

mysql= MySQL(app)
ph = PasswordHasher()
dat = requests.get("https://68976304250b078c2041c7fc.mockapi.io/api/wiremit/InterviewAPIS")
sp = bs4.BeautifulSoup(dat.text, 'lxml')
vals = sp.get_text()
rates = json.loads(vals)

eligibleCountries = []
eligibleCountriesRates = []
eligibleCountriesCurrency = ["GBP", "ZAR"]
for val in rates:
    key = list(val.keys())
    if key[0] == "GBP" or key[0] == "ZAR":
        eligibleCountriesRates.append(val[key[0]])
        eligibleCountries.append(val)
def acount():
    cur = mysql.connection.cursor()
    cur.execute("create table if not exists acounts(id int primary key AUTO_INCREMENT, fname varchar(255) not null, lname varchar(255) not null, contact int unique not null, email varchar(255) unique not null, balance varchar(255) default 1000 not null, country varchar(255) not null, password varchar(255) not null, confirm varchar(255) not null)")
    mysql.connection.commit()

def transaction():
    cur = mysql.connection.cursor()
    cur.execute("create table if not exists transactions(id int primary key AUTO_INCREMENT, sender varchar(255) not null, receiver varchar(255) not null, amount varchar(255) not null, transactionTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    mysql.connection.commit()

class User:
    def __init__(self):
        self.username = ""
        self.balance = 0.0
        self.data = None
        self.eligibleCountriesCurrency = eligibleCountriesCurrency
        self.eligibleCountries = eligibleCountries
        self.eligibleCountriesRates = eligibleCountriesRates
    def getUser(self):
        return self.username
    def getData(self):
        return self.data
    def getBalance(self):
        return self.balance
    def setUser(self, username):
        self.username = username
    def setBalance(self, bal):
        self.balance = bal
    def setData(self, data):
        self.data = data
    
user = User()

@app.route('/', methods=["GET",'POST'])
def index():
    acount()
    transaction()
    user.setData(eligibleCountries)
    if request.method == "POST":
        uname = request.form['username']
        password = request.form['password']
        if len(uname) > 0:
            if len(password) > 0:
                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM acounts where email = '"+uname+"' limit 1")
                data = cur.fetchall()
                cur.close()
                try:
                    ph.verify(data[0][7], password)
                    user.setUser(data[0][4] )
                    user.setBalance(data[0][5])
                    flash("Welcome to your Account " + user.getUser())
                    return redirect(url_for('viewTransaction'))
                except Exception:
                    flash("Password and username do not match or username does not exist")
            else:
                flash("Plese insert data")
        else:
            flash("Plese insert data")
    return render_template("index.html")

@app.route('/ads', methods=["GET",'POST'])
def ads():
    if user.getUser() != "":
        return render_template("ads.html", user=user)
    else:
        return render_template("ads.html")

@app.route('/createAccount', methods=["GET","POST"])
def createAccount():
    if request.method == "POST":
        fname = request.form['fname']
        lname = request.form['lname']
        contact = request.form['contact']
        country = request.form['country']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if len(fname) > 0:
            if len(lname) > 0:
                if len(contact) > 4:
                    if len(country) > 0:
                        if len(email) > 0:
                            if len(password) > 5:
                                if len(confirm) > 5:
                                    if password == confirm:
                                        if country == "UK" or country == "SOUTH AFRICA":
                                            cur = mysql.connection.cursor()
                                            h = ph.hash(password)
                                            cur.execute("INSERT INTO acounts (fname, lname, contact, country, email, password, confirm) VALUES (%s,%s,%s,%s,%s,%s,%s)", (fname, lname, contact, country, email, h, h))
                                            mysql.connection.commit()
                                            flash("Data inserted successfully, You can Sign in")
                                            return redirect(url_for('index'))
                                        else:
                                            flash("Your country is not eligible only UK and South Africa are")
                                    else:
                                        flash("Passwords do not match")
                                else:
                                    flash("Password cannot have less than 5 characters")
                            else:
                                flash("Password cannot have less than 5 characters")
                        else:
                            flash("Plese insert data")
                    else:
                        flash("Plese insert data")
                else:
                    flash("Contact cannot be less than 5")
            else:
                flash("Plese insert data")
        else:
            flash("Plese insert data")
    return render_template("createAccount.html")
    
@app.route('/makeTransaction', methods=["GET","POST"])
def makeTransaction():
    if user.getUser() != "":
        if request.method == "POST":
            sender = user.getUser()
            receiver = request.form['receiver']
            amount = request.form['amount']
            cur = mysql.connection.cursor()
            cur.execute("SELECT balance FROM acounts where email = '"+sender+"'")
            senderBalance = cur.fetchall()
            cur.execute("SELECT country FROM acounts where email = '"+sender+"'")
            senderCountry = cur.fetchall()
            cur.execute("SELECT balance FROM acounts where email = '"+receiver+"'")
            receiverBalance = cur.fetchall()
            if len(receiver) > 0:
                if float(amount) > 3:
                    if receiverBalance:
                        if float(senderBalance[0][0]) > float(amount):
                            cur.execute("INSERT INTO transactions (sender, receiver, amount) VALUES (%s, %s, %s)", (sender, receiver, amount))
                            mysql.connection.commit()
                            deducted = float(senderBalance[0][0]) - float(amount)
                            if senderCountry[0][0] == "UK":
                                charges = float(amount) * 0.1
                                deducted = deducted - charges
                            elif senderCountry[0][0] == "SOUTH AFRICA":
                                charges = float(amount) * 0.2
                                deducted = deducted - charges
                            user.setBalance(deducted)
                            added = float(receiverBalance[0][0]) + float(amount)
                            cur.execute("update acounts set balance = '"+str(deducted)+"' where email = '"+sender+"'")
                            mysql.connection.commit()
                            cur.execute("update acounts set balance = '"+str(added)+"' where email = '"+receiver+"'")
                            mysql.connection.commit()
                            flash("Data updated successfully")
                            return redirect(url_for('viewTransaction'))
                        else:
                            flash("Insuficient funds to pursue the transaction")
                    else:
                        flash("Receiver account does not exist")
                else:
                    flash("Not allowed to send an amount less than 3")
            else:
                flash("Please insert receiver account or valid account")
    else:
        return redirect(url_for('index')) 
    return render_template("makeTransaction.html", user=user)
    
@app.route('/viewTransaction', methods=["GET","POST"])
def viewTransaction():
    if user.getUser() != "":
        cur = mysql.connection.cursor()
        if request.method == "POST":
            account = request.form['account']
            if len(account) > 0:
                cur.execute("SELECT * FROM transactions where receiver LIKE '"+account+"%' AND sender LIKE '"+user.getUser()+"%' OR sender LIKE '%"+account+"%' AND receiver LIKE '"+user.getUser()+"%'")
                data = cur.fetchall()
                cur.close()
                flash("Search results")
                if(len(data) == 0):
                    flash("No transactions found corresponding to the account")
                    flash("Search results")
            else:
                cur.execute("SELECT * FROM transactions where receiver LIKE '"+user.getUser()+"%' OR sender LIKE '%"+user.getUser()+"%'")
                data = cur.fetchall()
                cur.close()
                flash("Account cannot be empty for searching")
        else:
            cur.execute("SELECT * FROM transactions where receiver LIKE '"+user.getUser()+"%' OR sender LIKE '%"+user.getUser()+"%'")
            data = cur.fetchall()
            cur.close()
    else:
        return redirect(url_for('index')) 
    return render_template("showTransactions.html", data=data)
    
@app.route('/viewAccounts', methods=["GET","POST"])
def viewAccounts():
    if user.getUser() != "":
        cur = mysql.connection.cursor()
        if request.method == "POST":
            cur.execute("SELECT * FROM acounts order by lname desc")
        else:
            cur.execute("SELECT * FROM acounts")
        data = cur.fetchall()
        cur.close()
    else:
        return redirect(url_for('index')) 
    return render_template("showAccounts.html", data=data)

@app.route('/logout', methods=["GET","POST"])
def logout():
    user.setUser("")
    return render_template("index.html")

if __name__ == '__main__':
    app.run()