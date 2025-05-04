from . import db
from datetime import datetime
import enum
from sqlalchemy import Enum, DECIMAL

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    mercadopago_preference_id = db.Column(db.String(255), nullable=True)
    mercadopago_payment_id = db.Column(db.String(255), nullable=True)
    status = db.Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    customer_email = db.Column(db.String(255), nullable=True) # Consider making this mandatory depending on flow
    game_name = db.Column(db.String(100), nullable=False, default='JOGO TESTE')
    price = db.Column(DECIMAL(10, 2), nullable=False) # Store price at the time of order

    def __repr__(self):
        return f'<Order {self.id} - Status: {self.status.name}>'

