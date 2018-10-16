from flask import Flask, render_template, request, session, redirect, send_from_directory, jsonify
from avitoparser import main_parsing                              # escape - 
from mysql_wrapper import UseDataBase
from functools import wraps
import csv


app = Flask(__name__)
parser_db = UseDataBase()


class AjaxPage():
    default_step = 100
    old_step = 0
    new_step = 0
    step = 50
    def do_refresh(self):
        if self.new_step != 0:
            self.old_step = self.new_step
        else:
            self.old_step = self.default_step
        self.new_step = self.old_step + self.step
    def do_reload(self):
        self.old_step = 0
        self.new_step = 0

page = AjaxPage()


def check_status(func):
    @wraps(func)
    def wrapper(*args, **kwargs):        
        if 'logged_in' in session:
            return func(*args, **kwargs)
        return redirect('/login')
    return wrapper
app.secret_key = '#$Aqk^&45$$2oPfgHnmKloU5i99fG%$#'


def ask_DB(*args):
    if args[-1] == False:        
        cursor = parser_db.create_connection()    
        parser_db.query_insert(*args)
        parser_db.close()
        return True

    cursor = parser_db.create_connection()    
    parser_db.query_insert(*args)
    contents = cursor.fetchall()
    parser_db.close()

    if len(contents) == 0:
        return False
    return contents


@app.route('/signin')
def do_signin():
    return render_template('signin.html')


@app.route('/login')
def do_login():
    return  render_template('login.html')


@app.route('/logout')
def do_logout():
    try:
        session.pop('logged_in')
        session.pop('name')
    except:
        text = 'Вы не в системе'
        return render_template('registration.html', the_text = text)
    text = 'Вы вышли из ситемы'
    return render_template('registration.html', the_text = text)


@app.route('/login_registration', methods = ['GET','POST'])
def check_registration():    
    if request.method == 'POST':
        username = request.form['login']
        password = request.form['password']

        _SQL = 'SELECT username FROM Users WHERE username=%s'
        dbuser = ask_DB(_SQL, (username,))

        _SQL = 'SELECT password FROM Users WHERE username=%s'
        dbpassword = ask_DB(_SQL, (username,))

        if dbuser:
            if password == dbpassword[0][0]:
                session['logged_in'] = True
                session['name'] = username
                return redirect('/entry')
            else:             
                text = 'Имя или пароль не верны'
                return render_template('registration.html', the_text = text)
        else:
            text = 'Такого пользователя не существует'
            return render_template('registration.html', the_text = text)

    return render_template('registration.html')


@app.route('/signin_registration', methods = ['GET','POST'])
def check_signin():
    if request.method == 'POST':
        username = request.form['login']
        password = request.form['password']

        _SQL = 'SELECT username FROM Users WHERE username=%s'
        dbuser = ask_DB(_SQL, (username,))

        if len(password) < 4 or len(username) < 4:
            text = 'Логин и пароль должны содержать не менее 4х символов'
            return render_template('signin.html',the_text=text)
        elif dbuser:
            text = 'Имя "%s" занято' %username
            return render_template('signin.html',the_text=text)
            
        _SQL = ''' INSERT INTO Users
                (username, password) 
                VALUES
                (%s, %s) '''
        ask_DB(_SQL, (username, password), False)
        session['logged_in'] = True 
        session['name'] = username

    return redirect('/entry')


@app.route('/')
@app.route('/entry')
@check_status
def entry_page():
    return render_template('entry.html')


@app.route('/results', methods = ['POST','GET']) 
@check_status
def do_search():
    city = request.form['city']
    phrase = request.form['phrase']

    if request.method == 'POST':
        main_parsing(city, phrase)

    return render_template('results.html',  the_phrase = phrase.upper(),
                                            the_city = city.upper(),)


@app.route('/viewresults')
@check_status
def view_the_parse():
    titles = ('ID', 'Заголовок', 'Цена', 'Время', 'Место', 'URL')
    _SQL = 'UPDATE parse SET time="Время размещения неизвестно" WHERE LENGTH(time) > 60'
    ask_DB(_SQL, False)

    _SQL = 'SELECT * FROM parse WHERE id <= %s' %(page.default_step)
    page.do_reload()
    return render_template('viewresults.html', the_row_titles = titles,
                                               the_data = ask_DB(_SQL), )


@app.route('/viewresultsajax', methods = ['GET'])
def get_ajax_request():
    page.do_refresh()
    titles = ('ID', 'Заголовок', 'Цена', 'Время', 'Место', 'URL')

    _SQL = 'SELECT * FROM parse WHERE id BETWEEN %s AND %s' %(page.old_step + 1, page.new_step)
    data = ask_DB(_SQL)

    if data:
        return render_template('new_ajax_results.html', the_row_titles = titles,
                                                        the_data = data,)
    page.do_reload()
    return jsonify(False)


@app.route('/downloads/<path:filename>')
@check_status
def download_results(filename):
    titles = ('ID', 'Заголовок', 'Цена', 'Время', 'Место', 'URL')
    _SQL = 'SELECT * FROM parse'

    with open('results.csv', 'w') as results:
        writer = csv.writer(results, dialect='excel')
        writer.writerow(titles)
        writer.writerows(ask_DB(_SQL))

    return send_from_directory('', 'results.csv')


if __name__ == '__main__':
    app.run(debug=True)