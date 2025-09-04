from flask import Flask, render_template, request, flash, session, redirect, jsonify, send_file, Response
from flask_login import LoginManager, UserMixin, AnonymousUserMixin, login_user, login_required, logout_user, \
    current_user
from urllib.parse import unquote
import sqlite3
import os
from dotenv import load_dotenv
from hash import hash_password
import pandas as pd
import zipfile
import io

app = Flask(__name__)
app.debug = True
login_manager = LoginManager()
login_manager.init_app(app)
load_dotenv()

connection = sqlite3.connect('database/userData.db', check_same_thread=False)
connection2 = sqlite3.connect('database/moneyData.db', check_same_thread=False)
userdata = connection.cursor()
moneydata = connection2.cursor()
userdata.execute(
    "CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY, name text NOT NULL, lastname text NOT NULL, login text NOT NULL, password text NOT NULL)")
"""
                        Для moneydata существует 2 БД: Доход - income и Расход - expense
                        Обе сохраняют текущий логин пользователя для привязки данных к аккаунту, поэтому стоит сделать так, чтобы незарегистрированные и не зашедшие
                            в аккаунт Пользователи не могли ничего сделать. Можно поставить всплывающее окно с просьбой войти, при попытки ввода в поля.

"""
moneydata.execute(
    "CREATE TABLE IF NOT EXISTS income (id INTEGER PRIMARY KEY, login text NOT NULL, amount text NOT NULL, source text NOT NULL)")
moneydata.execute(
    "CREATE TABLE IF NOT EXISTS expense (id INTEGER PRIMARY KEY, login text NOT NULL, amount text NOT NULL, category text NOT NULL)")

app.secret_key = os.getenv("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = 'uploads'


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    user = userdata.execute(f"SELECT * FROM user WHERE id = {user_id}").fetchone()
    if user:
        return User(id=user[0], username=user[1], password=user[-1])
    return None


@app.route("/", methods=["GET", "POST"])
def grandpage():
    # print(current_user.id)
    if current_user.is_anonymous is True:
        print("Анонимчик на сервере")
    else:
        login = userdata.execute(f"SELECT login FROM user WHERE id = {current_user.id}").fetchone()[0]
    if 'income' not in session or "expense" not in session:
        session["income"] = {
            "Зарплата": 0,
            "Фриланс": 0,
            "Инвестиции": 0
        }
        session["expense"] = {
            "Продукты": 0,
            "Одежда": 0,
            "Транспорт": 0,
            "Развлечения": 0,
            "Стройматериалы": 0,
            "Мебель": 0,
            "Рестораны и кафе": 0,
            "Салоны красоты и косметика": 0,
            "Лекарства": 0,
            "Аренда/Ипотека": 0,
            "Коммунальные услуги": 0,
            "Налоги": 0,
            "Внезапные расходы": 0
        }
    print(request.form, 123)
    if request.method == "POST":
        if len(list(request.form)) != 0:
            if list(request.form)[0] == "LoginButton":
                return redirect("/autorization")
            if list(request.form)[0] == "datareset":
                session["income"] = {
                    "Зарплата": 0,
                    "Фриланс": 0,
                    "Инвестиции": 0
                }
                session["expense"] = {
                    "Продукты": 0,
                    "Одежда": 0,
                    "Транспорт": 0,
                    "Развлечения": 0,
                    "Стройматериалы": 0,
                    "Мебель": 0,
                    "Рестораны и кафе": 0,
                    "Салоны красоты и косметика": 0,
                    "Лекарства": 0,
                    "Аренда/Ипотека": 0,
                    "Коммунальные услуги": 0,
                    "Налоги": 0,
                    "Внезапные расходы": 0
                }
                flash("Данные успешно сброшены")
            if list(request.form)[0] == "addData":
                if current_user.is_anonymous:
                    flash("Необходимо войти в аккаунт, чтобы загрузить данные в базу")
                else:
                    addData(login, session['income'], session['expense'])
            if list(request.form)[0] == "downloadData":
                if current_user.is_anonymous:
                    flash("Необходимо войти в аккаунт, чтобы скачать данные из базы данных")
                else:
                    return redirect(f"/download")

        if (request.form.get("income-amount") != None) or (request.form.get("income-source") != None):
            print('123')
            income_amount = request.form.get("income-amount")
            income_source = request.form.get("income-source")
            session['income'][income_source] += int(income_amount)
        if (request.form.get("expense-amount") != None) or (request.form.get("expense-category") != None):
            expense_amount = request.form.get("expense-amount")
            expense_category = request.form.get("expense-category")
            session["expense"][expense_category] += int(expense_amount)
        if not session.modified:
            session.modified = True
    money_income = session['income']
    money_expense = get_money_expense(session['expense'])
    print(money_income, money_expense)
    money_income = session['income']
    money_expense = get_money_expense(session['expense'])
    return render_template("grandpage.html")


@app.route('/update', methods=['POST'])
def update_diagrams():
    if len(str(request.data)) == 3:
        money_income = session['income']
        money_expense = get_money_expense(session['expense'])
        return jsonify({'money_income': money_income, 'money_expense': list(money_expense)})
    data = str(request.data)[2:].split('&')
    print(len(str(request.data)), "data")
    category = unquote(data[0].split('=')[1])
    amount = int(data[1].split("=")[1][:-1])
    print(category, amount)
    if category in ["Зарплата", "Фриланс", "Инвестиции"]:
        session['income'][category] += amount
    else:
        session['expense'][category] += amount
    if not session.modified:
        session.modified = True
    money_income = session['income']
    money_expense = get_money_expense(session['expense'])
    return jsonify({'money_income': money_income, 'money_expense': list(money_expense)})


def addData(login, income_dict, expense_dict):
    for i in income_dict:
        if income_dict[i] != 0:
            moneydata.execute(f"INSERT INTO income (login, amount, source) VALUES ('{login}','{income_dict[i]}','{i}')")
    for i in expense_dict:
        if expense_dict[i] != 0:
            moneydata.execute(
                f"INSERT INTO expense (login, amount, category) VALUES ('{login}','{expense_dict[i]}','{i}')")
    connection2.commit()
    flash("Данные успешно сохранены в базу данных")
    return


def get_money_expense(money_expense):
    a = {"Продукты": 0,
         "Одежда": 0,
         "Транспорт": 0,
         "Развлечения": 0,
         "Стройматериалы": 0,
         "Мебель": 0,
         "Рестораны и кафе": 0,
         "Салоны красоты и косметика": 0,
         "Лекарства": 0,
         "Аренда/Ипотека": 0,
         "Коммунальные услуги": 0,
         "Налоги": 0,
         "Внезапные расходы": 0
         }
    for i in money_expense:
        a[i] = money_expense[i]
    return list(a.values())


def check_login(login, userdata):
    result = userdata.execute(f"SELECT * FROM user WHERE login = '{login}'").fetchone()
    if result is None:
        return True
    return False


@app.route("/registration", methods=["GET", "POST"])
def registration():
    if request.method == "GET":
        return render_template("registration.html")
    elif request.method == "POST":
        name = request.form.get("name")
        lastname = request.form.get("lastname")
        login = request.form.get("login")
        password = hash_password(request.form.get("password"))
        if check_login(login, userdata):
            userdata.execute(
                f"INSERT INTO user (name, lastname, login,password) VALUES ('{str(name)}','{str(lastname)}','{str(login)}','{str(password)}')")
            connection.commit()
            user = userdata.execute(
                f"SELECT * FROM user WHERE login = '{login}' and password = '{password}'").fetchone()
            login_user(User(id=user[0], username=user[1], password=user[-1]))
        else:
            flash('Пользователь с данным логином уже существует')
            return render_template("registration.html")
        return redirect("/")


@app.route("/autorization", methods=["GET", "POST"])
def auth():
    if request.method == "GET":
        return render_template("autorization.html")
    elif request.method == "POST":
        if list(request.form)[-1] == "RegisterButton":
            return redirect("/registration")
        elif list(request.form)[-1] == "LoginButton":
            login = request.form.get("login")
            password = request.form.get("password")
            if login == "" or password == "":
                return redirect("/autorization")
            else:
                user = userdata.execute(
                    f"SELECT * FROM user WHERE login = '{login}' and password = '{hash_password(password)}'").fetchone()
                if user is None:
                    flash("Неверно введены логин или пароль")
                    return render_template("autorization.html")
                else:
                    login_user(User(id=user[0], username=user[1], password=user[-1]))
                    return redirect("/")


@app.route('/createReport', methods=["POST"])
def createReport():
    print(session["income"], session["expense"])

    reportJSON = {"AllIncome": 0, "AllExpense": 0, "MostSpendCategories": []}

    a = sorted(dict(session["expense"]).items(), key=lambda x: x[1], reverse=True)

    for i in session["income"]:
        reportJSON["AllIncome"] += session["income"][i]
    for i in session["expense"]:
        reportJSON["AllExpense"] += session["expense"][i]

    for i in a:
        if i[1] != 0 and len(reportJSON["MostSpendCategories"]) != 3:
            reportJSON["MostSpendCategories"].append(i[0])
    print(reportJSON)
    return jsonify(reportJSON)


def createDataFile(login):
    incomes = moneydata.execute(f"SELECT amount,source FROM income WHERE login = '{login}'").fetchall()
    expenses = moneydata.execute(f"SELECT amount, category FROM expense WHERE login = '{login}'").fetchall()
    print(incomes, expenses)

    incomes_data = {"amount": [int(i[0]) for i in incomes], "source": [i[1] for i in incomes]}
    expenses_data = {"amount": [int(i[0]) for i in expenses], 'category': [i[1] for i in expenses]}
    print(incomes_data)
    print(expenses_data)

    df_income = pd.DataFrame(incomes_data)
    df_expense = pd.DataFrame(expenses_data)

    df_income.to_csv(f'uploads/{login}_income.csv', index=False, encoding='cp1251')
    df_expense.to_csv(f'uploads/{login}_expense.csv', index=False, encoding='cp1251')

    return


@app.route("/download")
@login_required
def download():
    if current_user.is_anonymous is True:
        return "Чтобы скачать данные, зарегистрируйтесь в системе"
    else:
        login = userdata.execute(f"SELECT login FROM user WHERE id = {current_user.id}").fetchone()[0]
        createDataFile(login)
        file_path_income = os.path.join(app.config['UPLOAD_FOLDER'], f'{login}_income.csv')
        file_path_expense = os.path.join(app.config['UPLOAD_FOLDER'], f'{login}_expense.csv')

        file_paths = [file_path_expense, file_path_income]

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    zip_file.write(file_path, os.path.basename(file_path))

        zip_buffer.seek(0)

        return Response(
            zip_buffer,
            mimetype='application/zip',
            headers={
                'Content-Disposition': 'attachment; filename=files.zip',
                'Content-Length': str(zip_buffer.getbuffer().nbytes)
            }
        )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect('/')


if "__main__" == __name__:
    app.run()
