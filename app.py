from flask import Flask
from application.database import db
app = None

def create_app():
    app = Flask(__name__)
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.sqlite3'
    db.init_app(app)
    app.app_context().push()
    return app
app = create_app()
from application.controllers import *


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        Admin = User.query.filter_by(type='admin').first()
        if Admin is None:
            Admin = User(username='admin', email='admin@example.com', password='admin', type='admin')
            db.session.add(Admin)
            db.session.commit()
    
    app.run()