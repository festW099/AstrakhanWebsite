from flask import Flask, render_template, request, redirect, url_for, session
import os
import sqlite3
import secrets
from collections import Counter

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def init_db():
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo TEXT,
            make TEXT,
            model TEXT,
            generation TEXT,
            price REAL,
            color TEXT,
            used BOOLEAN,
            drive_type TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'root' and password == '0000':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        make = request.form['make']
        model = request.form['model']
        generation = request.form['generation']
        price = float(request.form['price'])
        color = request.form['color']
        used = bool(request.form.get('used'))
        drive_type = request.form['drive_type']

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                photo_path = os.path.join('static/photo', photo.filename)
                photo.save(photo_path)
        
        conn = sqlite3.connect(os.path.join('Base', 'database.db'))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cars (photo, make, model, generation, price, color, used, drive_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (photo.filename, make, model, generation, price, color, used, drive_type))
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin'))
    
    return render_template('admin.html')

@app.route('/catalog')
def catalog():
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    make = request.args.get('make', '')
    model = request.args.get('model', '')
    price_min = float(request.args.get('price_min', 0))
    price_max = float(request.args.get('price_max', 1e9))
    color = request.args.get('color', '')
    used = request.args.get('used', '')
    drive_type = request.args.get('drive_type', '')

    query = 'SELECT * FROM cars WHERE 1=1'
    params = []

    if make:
        query += ' AND make = ?'
        params.append(make)
    if model:
        query += ' AND model = ?'
        params.append(model)
    if color:
        query += ' AND color = ?'
        params.append(color)
    if used != '':
        query += ' AND used = ?'
        params.append(int(used))
    if drive_type:
        query += ' AND drive_type = ?'
        params.append(drive_type)

    query += ' AND price BETWEEN ? AND ?'
    params.append(price_min)
    params.append(price_max)

    cursor.execute(query, params)
    cars = cursor.fetchall()

    cursor.execute('SELECT DISTINCT make FROM cars')
    makes = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT model FROM cars')
    models = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT color FROM cars')
    colors = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT MAX(price) FROM cars')
    max_price = cursor.fetchone()[0] or 1000000

    conn.close()

    return render_template('catalog.html',
                           cars=cars,
                           makes=makes,
                           models=models,
                           colors=colors,
                           drive_type=drive_type,
                           max_price=max_price)


@app.route('/')
def catalog_1():
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    make = request.args.get('make', '')
    model = request.args.get('model', '')
    price_min = float(request.args.get('price_min', 0))
    price_max = float(request.args.get('price_max', 1e9))
    color = request.args.get('color', '')
    used = request.args.get('used', '')
    drive_type = request.args.get('drive_type', '')

    query = 'SELECT * FROM cars WHERE 1=1'
    params = []

    if make:
        query += ' AND make = ?'
        params.append(make)
    if model:
        query += ' AND model = ?'
        params.append(model)
    if color:
        query += ' AND color = ?'
        params.append(color)
    if used != '':
        query += ' AND used = ?'
        params.append(int(used))
    if drive_type:
        query += ' AND drive_type = ?'
        params.append(drive_type)

    query += ' AND price BETWEEN ? AND ?'
    params.append(price_min)
    params.append(price_max)

    cursor.execute(query, params)
    cars = cursor.fetchall()

    cursor.execute('SELECT DISTINCT make FROM cars')
    makes = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT model FROM cars')
    models = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT color FROM cars')
    colors = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT MAX(price) FROM cars')
    max_price = cursor.fetchone()[0] or 1000000

    conn.close()

    return render_template('catalog.html',
                           cars=cars,
                           makes=makes,
                           models=models,
                           colors=colors,
                           max_price=max_price)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login_user')
def login_user():
    return render_template('login.html')

@app.route('/register_user')
def register_user():
    return render_template('register.html')

@app.route('/add_to_basket/<int:car_id>', methods=['POST'])
def add_to_basket(car_id):
    if 'basket' not in session:
        session['basket'] = []
    session['basket'].append(car_id)
    session.modified = True
    return redirect(url_for('catalog'))


@app.route('/remove_from_basket/<int:car_id>', methods=['POST'])
def remove_from_basket(car_id):
    if 'basket' not in session or not session['basket']:
        return redirect(url_for('basket'))

    remove_type = request.form.get('remove_type')

    if remove_type == 'one':
        if car_id in session['basket']:
            session['basket'].remove(car_id)
            session.modified = True

    elif remove_type == 'all':
        conn = sqlite3.connect(os.path.join('Base', 'database.db'))
        cursor = conn.cursor()
        cursor.execute('SELECT make, model FROM cars WHERE id = ?', (car_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            make, model = result
            conn = sqlite3.connect(os.path.join('Base', 'database.db'))
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM cars WHERE make = ? AND model = ?', (make, model))
            matching_ids = [row[0] for row in cursor.fetchall()]
            conn.close()

            session['basket'] = [cid for cid in session['basket'] if cid not in matching_ids]
            session.modified = True

    return redirect(url_for('basket'))


@app.route('/basket', methods=['GET', 'POST'])
def basket():
    basket_items = []
    total_price = 0

    if 'basket' in session and session['basket']:
        conn = sqlite3.connect(os.path.join('Base', 'database.db'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        basket_counter = Counter(session['basket'])
        unique_ids = list(basket_counter.keys())

        placeholders = ','.join('?' for _ in unique_ids)
        cursor.execute(f'SELECT * FROM cars WHERE id IN ({placeholders})', unique_ids)
        cars = cursor.fetchall()
        conn.close()

        for car in cars:
            car = dict(car)
            car_id = car['id']
            quantity = basket_counter[car_id]
            car['quantity'] = quantity
            car['total'] = car['price'] * quantity
            basket_items.append(car)

        total_price = sum(item['total'] for item in basket_items)

    if request.method == 'POST':
        if request.form.get('action') == 'buy':
            return redirect(url_for('pay'))
        elif request.form.get('action') == 'clear':
            session.pop('basket', None)
            return redirect(url_for('basket'))


    return render_template('basket.html', basket_items=basket_items, total_price=total_price)

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    basket_items = []
    total_price = 0

    if 'basket' in session and session['basket']:
        conn = sqlite3.connect(os.path.join('Base', 'database.db'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        basket_counter = Counter(session['basket'])
        unique_ids = list(basket_counter.keys())

        placeholders = ','.join('?' for _ in unique_ids)
        cursor.execute(f'SELECT * FROM cars WHERE id IN ({placeholders})', unique_ids)
        cars = cursor.fetchall()
        conn.close()

        for car in cars:
            car = dict(car)
            car_id = car['id']
            quantity = basket_counter[car_id]
            car['quantity'] = quantity
            car['total'] = car['price'] * quantity
            basket_items.append(car)

        total_price = sum(item['total'] for item in basket_items)

    if request.method == 'POST':
        card_number = request.form.get('card_number')
        cvv = request.form.get('cvv')
        expiry = request.form.get('expiry')
        phone_number = request.form.get('phone_number')

        # Создаём базу данных заказов если её нет
        orders_db_path = os.path.join('Base', 'orders.db')
        os.makedirs('Base', exist_ok=True)
        
        conn = sqlite3.connect(orders_db_path)
        cursor = conn.cursor()
        
        # Создаём таблицы для заказов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            phone_number TEXT,
            card_number TEXT,
            total_price REAL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            car_id INTEGER,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        ''')
        
        if (card_number == '0000000000000000' or card_number == '0000 0000 0000') and cvv == '000' and (expiry == '0000' or expiry == '00 00' or expiry == '00/00'):
            # Сохраняем основной заказ
            cursor.execute('''
            INSERT INTO orders (phone_number, card_number, total_price)
            VALUES (?, ?, ?)
            ''', (phone_number, card_number, total_price))
            
            order_id = cursor.lastrowid
            
            # Сохраняем товары заказа
            for item in basket_items:
                cursor.execute('''
                INSERT INTO order_items (order_id, car_id, quantity, price)
                VALUES (?, ?, ?, ?)
                ''', (order_id, item['id'], item['quantity'], item['price']))
            
            conn.commit()
            conn.close()
            
            session.pop('basket', None)
            return "Тестовый платёж прошёл успешно! Спасибо за заказ."
        else:
            # Сохраняем основной заказ
            cursor.execute('''
            INSERT INTO orders (phone_number, card_number, total_price)
            VALUES (?, ?, ?)
            ''', (phone_number, card_number, total_price))
            
            order_id = cursor.lastrowid
            
            # Сохраняем товары заказа
            for item in basket_items:
                cursor.execute('''
                INSERT INTO order_items (order_id, car_id, quantity, price)
                VALUES (?, ?, ?, ?)
                ''', (order_id, item['id'], item['quantity'], item['price']))
            
            conn.commit()
            conn.close()
            
            session.pop('basket', None)
            return "платёж прошёл успешно! Спасибо за заказ."

    return render_template('pay.html', basket_items=basket_items, total_price=total_price)



if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=2709)