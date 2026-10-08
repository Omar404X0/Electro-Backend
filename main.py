import os
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Integer, ForeignKey, String, Boolean, create_engine, Float, Column
from passlib.context import CryptContext

# قراءة رابط الداتابيز ديناميكياً لتشغيل PostgreSQL على Render و SQLite محلياً
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///main.db")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

eng = create_engine(DATABASE_URL, connect_args=connect_args)

Base = declarative_base()

pwd_con = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Imgs(Base):
    __tablename__ = 'imgs'
    id = Column(Integer, primary_key=True)
    img_path = Column(String, nullable=False)
    pro_id = Column(Integer, ForeignKey('prodacts.id'), nullable=False)

    pro = relationship('Prodacts', back_populates='img')

class Prodacts(Base):
    __tablename__ = 'prodacts'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    stats = Column(Boolean, nullable=False)
    contity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    img = relationship('Imgs', back_populates='pro')
    orders = relationship('Orders', back_populates='pro')
    cart = relationship('Cart', back_populates='pro')

class Users(Base):
    __tablename__ = 'users' 
    id = Column(Integer, primary_key=True) 
    name = Column(String, nullable=False)
    emil = Column(String, nullable=False) 
    password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)

    orders = relationship('Orders', back_populates='user')
    cart = relationship('Cart', back_populates='user')

class Orders(Base):
    __tablename__= 'orders' 
    id = Column(Integer, primary_key=True) 
    user_id = Column(Integer, ForeignKey('users.id'))
    pro_id = Column(Integer, ForeignKey('prodacts.id'))
    
    pro = relationship('Prodacts', back_populates='orders')
    user = relationship('Users', back_populates='orders')

class Cart(Base):
    __tablename__ = 'cart' 
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    pro_id = Column(Integer, ForeignKey('prodacts.id'))
    quantity = Column(Integer, default=1, nullable=False)  

    user = relationship('Users', back_populates='cart')
    pro = relationship('Prodacts', back_populates='cart')

Base.metadata.create_all(eng)

Session = sessionmaker(bind=eng)
session = Session()

product_images_map = {
    "IPhone 18 Pro Max": ["/apple.webp", "/Apple-iPhone-18-Pro-Max2.webp", "/Apple-iPhone-18-Pro-Max3.webp", "/Apple-iPhone-18-Pro-Max4.webp"],
    "IPhone 18": ["/iphone.webp"],
    "Samsung Galaxy S26 Ultra": ["/samsung.webp", "/samsung1.webp", "/samsung2.webp", "/samsung3.webp", "/samsung4.webp", "/samsung5.webp"],
    "Samsung A17 5G": ["/A17_5G.webp", "/A17_5G_2.webp", "/A17_5G_3.webp", "/A17_5G_4.webp"],
    "MacBook Air M4": ["/mac1.png", "/mac2.png", "/mac3.png"],
    "Gaming Laptop ASUS ROG": ["/rog.webp", "/rog2.webp"],
    "Apple Watch Series 11": ["/Apple-Watch.webp", "/Apple-Watch-2.webp"],
    "Samsung Galaxy Watch 8": ["/sam_watch.webp", "/sam_watch2.webp", "/sam_watch3.webp"],
    "Samsung Galaxy Tab S11": ["/tap1.webp", "/tap2.webp"],
    "Smart TV LG 65-inch 4K": ["/lg1.avif", "/lg2.jpeg", "/lg3.webp"],
    "Xiaomi Redmi Note 14 Pro": ["xiaomi-redmi-note-14-pro-sand-gold-official-image.webp"],
}

list_of_prodacts = [
    {"name": "IPhone 18 Pro Max", "stats": True, "contity": 15, "price": 122000},
    {"name": "IPhone 18", "stats": True, "contity": 25, "price": 78000},
    {"name": "Samsung Galaxy S26 Ultra", "stats": True, "contity": 20, "price": 79999},
    {"name": "Samsung A17 5G", "stats": True, "contity": 40, "price": 18799},
    {"name": "Xiaomi Redmi Note 14 Pro", "stats": True, "contity": 35, "price": 14500},
    {"name": "MacBook Air M4", "stats": True, "contity": 10, "price": 68000},
    {"name": "Gaming Laptop ASUS ROG", "stats": False, "contity": 0, "price": 135000},
    {"name": "Apple Watch Series 11", "stats": True, "contity": 30, "price": 21500},
    {"name": "Samsung Galaxy Watch 8", "stats": True, "contity": 22, "price": 13200},
    {"name": "Samsung Galaxy Tab S11", "stats": True, "contity": 15, "price": 42000},
    {"name": "Smart TV LG 65-inch 4K", "stats": True, "contity": 6, "price": 36000},
]

def pass_inc():
    password_d = pwd_con.hash('1234')
    admin = Users(name='Omar Elmallah', emil='o24@gmail.com', password=password_d, is_admin=True)
    session.add(admin)
    session.commit()
    
def seed_database():
    # لو فيه منتجات بالفعل، يبقى الداتابيز اتعملها seed قبل كده
    if session.query(Prodacts).count() > 0:
        return

    # إضافة المنتجات
    for p in list_of_prodacts:
        new_product = Prodacts(**p)
        session.add(new_product)
        session.flush()

        # إضافة صور كل منتج
        images_paths = product_images_map.get(p["name"], [])

        for path in images_paths:
            new_img = Imgs(
                img_path=path,
                pro=new_product
            )
            session.add(new_img)

    # إضافة الـ Admin
    password_d = pwd_con.hash('1234')

    admin = Users(
        name='Omar Elmallah',
        emil='o24@gmail.com',
        password=password_d,
        is_admin=True
    )

    session.add(admin)


    session.commit()


seed_database()