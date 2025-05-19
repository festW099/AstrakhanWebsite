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
            drive_type TEXT,
            engine_type TEXT,
            transmission TEXT,
            year INTEGER,
            mileage INTEGER,
            horsepower INTEGER,
            torque INTEGER,
            fuel_consumption REAL,
            seats INTEGER,
            doors INTEGER,
            trunk_volume REAL,
            safety_rating REAL,
            model_3d TEXT,
            statuc TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            comment TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            status TEXT DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'completed', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def init_order_db():
    orders_db_path = os.path.join('Base', 'orders.db')
    os.makedirs('Base', exist_ok=True)
    
    conn = sqlite3.connect(orders_db_path)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()

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

        init_order_db()
        
        conn = sqlite3.connect(os.path.join('Base', 'orders.db'))
        cursor = conn.cursor()
        
        if (card_number == '0000000000000000' or card_number == '0000 0000 0000') and cvv == '000' and (expiry == '0000' or expiry == '00 00' or expiry == '00/00'):
            cursor.execute('''
            INSERT INTO orders (phone_number, card_number, total_price)
            VALUES (?, ?, ?)
            ''', (phone_number, card_number, total_price))
            
            order_id = cursor.lastrowid

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
            cursor.execute('''
            INSERT INTO orders (phone_number, card_number, total_price)
            VALUES (?, ?, ?)
            ''', (phone_number, card_number, total_price))
            
            order_id = cursor.lastrowid
            
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

@app.route('/admin/comments')
def admin_comments():
    conn = sqlite3.connect('Base/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, comment, rating FROM reviews")
    reviews = cursor.fetchall()
    conn.close()
    return render_template('admin_comments.html', reviews=reviews)

@app.route('/admin/contact')
def contact():
    conn = sqlite3.connect('Base/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone, status, created_at FROM contacts ORDER BY created_at DESC")
    contacts = cursor.fetchall()
    conn.close()
    return render_template('admin_contact.html', contacts=contacts)

@app.route('/update_contact_status', methods=['POST'])
def update_contact_status():
    contact_id = request.form.get('contact_id')
    new_status = request.form.get('new_status')
    
    conn = sqlite3.connect('Base/database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE contacts SET status = ? WHERE id = ?", (new_status, contact_id))
    conn.commit()
    conn.close()
    
    return redirect('/admin/contact')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    main_db_path = os.path.join('Base', 'database.db')
    conn_main = sqlite3.connect(main_db_path)
    cursor_main = conn_main.cursor()
    
    cursor_main.execute('SELECT COUNT(*) FROM cars')
    total_cars = cursor_main.fetchone()[0]
    
    cursor_main.execute('SELECT COUNT(*) FROM contacts')
    total_comment = cursor_main.fetchone()[0]
    
    cursor_main.execute('SELECT COUNT(*) FROM reviews')
    total_reviews = cursor_main.fetchone()[0]
    
    conn_main.close()
    
    orders_db_path = os.path.join('Base', 'orders.db')
    conn_orders = sqlite3.connect(orders_db_path)
    cursor_orders = conn_orders.cursor()
    
    cursor_orders.execute('SELECT COUNT(*) FROM orders')
    total_orders = cursor_orders.fetchone()[0]
    
    cursor_orders.execute('''
        SELECT 
            order_id, 
            order_date, 
            phone_number, 
            total_price
        FROM orders
        ORDER BY order_date DESC
        LIMIT 2
    ''')
    last_orders = cursor_orders.fetchall()
    
    conn_orders.close()
    
    return render_template('admin_panel.html',
                         total_cars=total_cars,
                         total_reviews=total_reviews,
                         total_orders=total_orders,
                         last_orders=last_orders,
                         total_comment=total_comment)

@app.route('/catalog/<int:car_id>')
def car_details(car_id):
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
    car = cursor.fetchone()
    
    conn.close()
    
    if not car:
        return "Car not found", 404
    
    car_data = {
        'id': car[0],
        'photo': car[1],
        'make': car[2],
        'model': car[3],
        'generation': car[4],
        'price': car[5],
        'color': car[6],
        'used': bool(car[7]),
        'drive_type': car[8],
        'engine_type': car[9],
        'transmission': car[10],
        'year': car[11],
        'mileage': car[12],
        'horsepower': car[13],
        'torque': car[14],
        'fuel_consumption': car[15],
        'seats': car[16],
        'doors': car[17],
        'trunk_volume': car[18],
        'safety_rating': car[19],
        'model_3d': car[20]
    }
    
    return render_template('details.html', car=car_data)

@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
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
        
        engine_type = request.form['engine_type']
        transmission = request.form['transmission']
        year = int(request.form['year'])
        mileage = int(request.form['mileage'])
        horsepower = int(request.form['horsepower'])
        torque = int(request.form['torque'])
        fuel_consumption = float(request.form['fuel_consumption'])
        seats = int(request.form['seats'])
        doors = int(request.form['doors'])
        trunk_volume = float(request.form['trunk_volume'])
        safety_rating = float(request.form['safety_rating'])

        photo_filename = ''
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                photo_path = os.path.join('static/photo', photo.filename)
                photo.save(photo_path)
                photo_filename = photo.filename
        
        model_3d_filename = ''
        if 'model_3d' in request.files:
            model_3d = request.files['model_3d']
            if model_3d.filename != '':
                model_3d_path = os.path.join('static/models', model_3d.filename)
                model_3d.save(model_3d_path)
                model_3d_filename = model_3d.filename
        
        conn = sqlite3.connect(os.path.join('Base', 'database.db'))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cars (
                photo, make, model, generation, price, color, used, drive_type,
                engine_type, transmission, year, mileage, horsepower, torque,
                fuel_consumption, seats, doors, trunk_volume, safety_rating, model_3d
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            photo_filename, make, model, generation, price, color, used, drive_type,
            engine_type, transmission, year, mileage, horsepower, torque,
            fuel_consumption, seats, doors, trunk_volume, safety_rating, model_3d_filename
        ))
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin'))
    
    return render_template('admin_add.html')

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

@app.route('/catalog')
def catalog():
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    make = request.args.get('make', '')
    model = request.args.get('model', '')
    generation = request.args.get('generation', '')
    price_min = float(request.args.get('price_min', 0))
    price_max = float(request.args.get('price_max', 1e9))
    engine_type = request.args.get('engine_type', '')
    transmission = request.args.get('transmission', '')
    year = request.args.get('year', '')
    horsepower = request.args.get('horsepower', '')
    color = request.args.get('color', '')
    used = request.args.get('used', '')
    drive_type = request.args.get('drive_type', '')
    mileage = request.args.get('mileage', '')
    seats = request.args.get('seats', '')
    doors = request.args.get('doors', '')
    safety_rating = request.args.get('safety_rating', '')

    query = 'SELECT * FROM cars WHERE 1=1'
    params = []

    if make:
        query += ' AND make = ?'
        params.append(make)
    if model:
        query += ' AND model = ?'
        params.append(model)
    if generation:
        query += ' AND generation = ?'
        params.append(generation)
    if engine_type:
        query += ' AND engine_type = ?'
        params.append(engine_type)
    if transmission:
        query += ' AND transmission = ?'
        params.append(transmission)
    if year:
        query += ' AND year = ?'
        params.append(year)
    if color:
        query += ' AND color = ?'
        params.append(color)
    if used != '':
        query += ' AND used = ?'
        params.append(int(used))
    if drive_type:
        query += ' AND drive_type = ?'
        params.append(drive_type)
    if seats:
        query += ' AND seats = ?'
        params.append(seats)
    if doors:
        query += ' AND doors = ?'
        params.append(doors)
    if safety_rating:
        query += ' AND safety_rating >= ?'
        params.append(float(safety_rating))

    query += ' AND price BETWEEN ? AND ?'
    params.append(price_min)
    params.append(price_max)

    mileage_min = request.args.get('mileage_min')
    mileage_max = request.args.get('mileage_max')
    if mileage_min and mileage_max:
        query += ' AND mileage BETWEEN ? AND ?'
        params.extend([mileage_min, mileage_max])
    elif mileage_min:
        query += ' AND mileage >= ?'
        params.append(mileage_min)
    elif mileage_max:
        query += ' AND mileage <= ?'
        params.append(mileage_max)

    horsepower_min = request.args.get('horsepower_min')
    horsepower_max = request.args.get('horsepower_max')
    if horsepower_min and horsepower_max:
        query += ' AND horsepower BETWEEN ? AND ?'
        params.extend([horsepower_min, horsepower_max])
    elif horsepower_min:
        query += ' AND horsepower >= ?'
        params.append(horsepower_min)
    elif horsepower_max:
        query += ' AND horsepower <= ?'
        params.append(horsepower_max)

    cursor.execute(query, params)
    cars = cursor.fetchall()

    cursor.execute('SELECT DISTINCT make FROM cars ORDER BY make')
    makes = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT model FROM cars ORDER BY model')
    models = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT generation FROM cars ORDER BY generation')
    generations = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT engine_type FROM cars ORDER BY engine_type')
    engine_types = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT transmission FROM cars ORDER BY transmission')
    transmissions = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT year FROM cars ORDER BY year DESC')
    years = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT color FROM cars ORDER BY color')
    colors = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT seats FROM cars ORDER BY seats')
    seats = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT doors FROM cars ORDER BY doors')
    doors = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT MAX(price) FROM cars')
    max_price = max_price = float(cursor.fetchone()[0] or 1000000)

    conn.close()

    return render_template('catalog.html',
                         cars=cars,
                         makes=makes,
                         models=models,
                         generations=generations,
                         engine_types=engine_types,
                         transmissions=transmissions,
                         years=years,
                         colors=colors,
                         seats=seats,
                         doors=doors,
                         drive_type=drive_type,
                         max_price=max_price)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/submit_review', methods=['POST'])
def submit_review():
    name = request.form.get('name')
    review = request.form.get('review')
    rating = request.form.get('rating')
    
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reviews (name, comment, rating)
        VALUES (?, ?, ?)
    ''', (name, review, rating))
    conn.commit()
    conn.close()
    
    return redirect(url_for('about'))

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    phone = request.form.get('phone')
    
    conn = sqlite3.connect(os.path.join('Base', 'database.db'))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO contacts (phone)
        VALUES (?)
    ''', (phone,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('about'))

@app.route('/')
def catalog_1():
    return redirect(url_for('catalog'))

@app.route('/login_user')
def login_user():
    return render_template('login.html')

@app.route('/register_user')
def register_user():
    return render_template('register.html')

@app.route('/test')
def test():
    return render_template('test.html')

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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=2709)