from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import qrcode
from io import BytesIO
import base64
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'
PASSWORD = 'adminpassword'  # Change Password
db = SQLAlchemy(app)

businesscards_links = db.Table('businesscards_links',
                               db.Column('businesscard_id', db.Integer, db.ForeignKey('business_cards.id'),
                                         primary_key=True),
                               db.Column('link_id', db.Integer, db.ForeignKey('links.id'), primary_key=True)
                               )


class BusinessCards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(10), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    prename = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    task = db.Column(db.String(100), nullable=True)
    picture = db.Column(db.String(100), nullable=False)
    template = db.Column(db.String(50), nullable=False)
    links = db.relationship('Links', secondary=businesscards_links, lazy='subquery',
                            backref=db.backref('businesscards', lazy=True))
    visits = db.relationship('Visit', backref='business_card', lazy=True)


class Links(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    link = db.Column(db.String(200), nullable=False)


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    businesscard_id = db.Column(db.Integer, db.ForeignKey('business_cards.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())


@app.route('/')
def index():
    cards = BusinessCards.query.all()
    return render_template('index.html', cards=cards)


@app.route('/card/<int:id>')
def view_card(id):
    card = BusinessCards.query.get_or_404(id)
    ip_address = request.remote_addr
    visit = Visit(ip_address=ip_address, business_card=card)
    db.session.add(visit)
    db.session.commit()
    qr_code_img = qrcode.make(url_for('view_links', id=id, _external=True))
    buffer = BytesIO()
    qr_code_img.save(buffer)
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return render_template(f'template{card.template}.html', card=card, qr_code_base64=qr_code_base64)


@app.route('/links/<int:id>')
def view_links(id):
    card = BusinessCards.query.get_or_404(id)
    ip_address = request.remote_addr
    visit = Visit(ip_address=ip_address, business_card=card)
    db.session.add(visit)
    db.session.commit()
    return render_template('view_links.html', card=card)


@app.route('/logs', methods=['GET', 'POST'])
def view_logs():
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            sort_by = request.form.get('sort_by', 'timestamp')
            if sort_by == 'card':
                visits = Visit.query.order_by(Visit.businesscard_id).all()
            else:
                visits = Visit.query.order_by(Visit.timestamp).all()
            return render_template('view_logs.html', visits=visits)
        else:
            return "Invalid password. Please try again."
    return render_template('login.html')


@app.route('/create', methods=['GET', 'POST'])
def create_card():
    if request.method == 'POST':
        picture_file = request.files['picture']
        picture_filename = picture_file.filename
        picture_file.save(os.path.join('static/images', picture_filename))

        card = BusinessCards(
            prefix=request.form.get('prefix'),
            name=request.form['name'],
            prename=request.form['prename'],
            company=request.form.get('company'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            country=request.form.get('country'),
            task=request.form.get('task'),
            picture=picture_filename,
            template=request.form['template']
        )

        for link_name, link_url in zip(request.form.getlist('link_name'), request.form.getlist('link_url')):
            if link_name and link_url:
                link = Links(name=link_name, link=link_url)
                card.links.append(link)

        db.session.add(card)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('create_card.html')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_card(id):
    card = BusinessCards.query.get_or_404(id)
    if request.method == 'POST':
        picture_file = request.files['picture']
        if picture_file:
            picture_filename = picture_file.filename
            picture_file.save(os.path.join('static/images', picture_filename))
            card.picture = picture_filename

        card.prefix = request.form.get('prefix')
        card.name = request.form['name']
        card.prename = request.form['prename']
        card.company = request.form.get('company')
        card.phone = request.form.get('phone')
        card.email = request.form.get('email')
        card.address = request.form.get('address')
        card.country = request.form.get('country')
        card.task = request.form.get('task')
        card.template = request.form['template']

        card.links.clear()
        for link_name, link_url in zip(request.form.getlist('link_name'), request.form.getlist('link_url')):
            if link_name and link_url:
                link = Links(name=link_name, link=link_url)
                card.links.append(link)

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit_card.html', card=card)


if __name__ == '__main__':
    db.create_all()
    app.run()
