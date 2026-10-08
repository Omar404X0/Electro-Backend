import os
from datetime import datetime, timedelta
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel

from google import genai
from google.genai import types

from main import Prodacts, session, Users, pwd_con, Cart, Orders


load_dotenv()

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://electro-frontend-khaki.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Gemini client =====
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
print("GEMINI KEY LOADED:", bool(os.getenv("GEMINI_API_KEY")))

# موديل أساسي + fallback
MODELS = [  "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",]

# ===== JWT =====
Algorithm = 'HS256'
Security_key = 'kdjksjdofhsndislasn@ahhsh!kjkjs*nandns%jskdkjksj00MNjasjdjkjasdjkwjsk@!ssckkasdhskdd**jskjkljdjskld)asdknknslkncnscn'


def craete_token(data: dict):
    copy_data = data.copy()
    end_time = datetime.utcnow() + timedelta(hours=1)
    copy_data.update({'exp': end_time})
    return jwt.encode(copy_data, Security_key, algorithm=Algorithm)


class MessageItem(BaseModel):
    sender: str
    text: str


class PromptRequest(BaseModel):
    message: str
    history: Optional[List[MessageItem]] = []


@app.post("/products/ai")
async def ai_assistant(request: PromptRequest):
    try:
        # المنتجات المتاحة من الداتابيز
        products = session.query(Prodacts).filter(Prodacts.stats == True).all()

        if products:
            products_list = "\n".join([
                f"- {p.name} | {p.price} جنيه | المتاح: {p.contity}"
                for p in products
            ])
        else:
            products_list = "مفيش منتجات متاحة دلوقتي."

        github_url = "https://github.com/Omar404X0"

        system_instruction = f"""إنت "Electro AI"، مساعد مبيعات ودود في متجر إلكترونيات اسمه "Electro".

المنتجات المتاحة حالياً (الاسم | السعر بالجنيه | الكمية):
{products_list}

أسلوبك:
- بتتكلم بالعامية المصرية البسيطة، زي بائع محترم ومتعاون.
- ردودك قصيرة (جملتين لتلات) ومباشرة، وبترد على آخر رسالة من العميل.
- لو العميل سلّم أو سأل "عامل إيه"، رد على السلام وبعدين اسأله يحب يشوف إيه.
- لما العميل يسأل عن منتج، اذكر السعر والمتاح من القائمة بس، ولو المنتج مش في القائمة قوله إنه مش متوفر دلوقتي واقترح بديل قريب منه.
- متخترعش منتجات أو أسعار مش في القائمة.
- اكتب الرد النهائي بس.

لو حد سأل مين عمل الموقع أو المتجر أو الـ AI: المطور هو عمر الملاح (Omar El-Mallah)، مطور ويب وMachine Learning عنده 20 سنة، وعمل المشروع كله لوحده. اذكر الرابط بتاعه: {github_url}"""

        # تجهيز الـ history
        history = []
        for item in request.history or []:
            role = "user" if item.sender == "user" else "model"
            history.append((role, item.text))

        
        while history and history[0][0] == "model":
            history.pop(0)

        contents = [
            types.Content(role=role, parts=[types.Part(text=text)])
            for role, text in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=request.message)]))

        errors = []
        for model_name in MODELS:
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        max_output_tokens=2000,
                    ),
                )
                if response.text:
                    return {"reply": response.text.strip()}
                errors.append(f"{model_name}: empty response")
            except Exception as e:
                errors.append(f"{model_name}: {e}")
                print("MODEL ERROR ->", model_name, e)

        raise HTTPException(status_code=500, detail=" | ".join(errors))

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print("Server error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
#                              Auth
# ===================================================================
class User_log(BaseModel):
    emil: str
    password: str


class User_s(BaseModel):
    emil: str
    password: str
    name: str


@app.post('/signup')
async def sign(user: User_s):
    existing = session.query(Users).filter(Users.emil == user.emil).first()
    if existing:
        return False

    new_user = Users(
        emil=user.emil,
        password=pwd_con.hash(user.password),
        name=user.name
    )
    session.add(new_user)
    session.commit()

    token = craete_token({'user_id': new_user.id})
    return {
        'token': token,
        'is_admin': new_user.is_admin
    }


@app.post('/login')
async def log(user: User_log):
    result = session.query(Users).filter(
        Users.emil == user.emil
    ).first()

    if result is None:
        return False

    if pwd_con.verify(user.password, result.password):
        token = craete_token({'user_id': result.id})
        return {
            'token': token,
            'is_admin': result.is_admin
        }
    else:
        return False


# ===================================================================
#                              Products
# ===================================================================
@app.get('/prodacts')
async def get_pro():
    res = []
    pro = session.query(Prodacts).all()
    for p in pro:
        res.append({
            'id': p.id,
            'name': p.name,
            'con': p.contity,
            'price': p.price,
            'stat': p.stats,
            'imgs': [img.img_path for img in p.img]
        })
    return res


class orderReq(BaseModel):
    pro_id: int
    token: str


@app.post('/prodacts/order')
async def buy_pro(order: orderReq):
    pro = session.query(Prodacts).filter(
        Prodacts.id == order.pro_id,
        Prodacts.contity > 0
    ).update({Prodacts.contity: Prodacts.contity - 1})

    if pro == 0:
        return False

    payload = jwt.decode(order.token, Security_key, algorithms=[Algorithm])
    user_id = payload.get("user_id")

    pro_owen = session.query(Prodacts).filter(
        Prodacts.id == order.pro_id,
    ).first()

    user = session.query(Users).filter(
        Users.id == user_id
    ).first()

    new_order = Orders(
        user_id=user.id,
        pro_id=pro_owen.id
    )

    session.add(new_order)
    session.commit()
    return True


# ===================================================================
#                              Cart
# ===================================================================
class Cart_type(BaseModel):
    pro_id: int
    token: str
    quantity: int


@app.post('/prodacts/cart')
async def add_to_car(cart: Cart_type):
    payload = jwt.decode(cart.token, Security_key, algorithms=[Algorithm])
    user_id_from_token = payload.get('user_id')

    new_cart_pro = Cart(
        pro_id=cart.pro_id,
        user_id=user_id_from_token,
        quantity=cart.quantity,
    )

    session.add(new_cart_pro)
    session.commit()
    return True


@app.get('/cart')
async def cart_fun(token: str):
    try:
        payload = jwt.decode(token, Security_key, algorithms=[Algorithm])
        user_id = payload.get('user_id')
        all_pro = []
        one_pro = session.query(Cart).filter(Cart.user_id == user_id).all()
        for item in one_pro:
            all_pro.append({
                'id': item.id,
                'user_id': item.user_id,
                'pro_id': item.pro_id,
                'name': item.pro.name,
                'img': item.pro.img[0].img_path if item.pro.img else None,
                'price': item.pro.price,
                'quantity': item.quantity
            })
        return all_pro
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class remove_item(BaseModel):
    id: int
    token: str


@app.post('/cart/remove')
async def remove_from_cart(item_remove: remove_item):
    try:
        payload = jwt.decode(item_remove.token, Security_key, algorithms=[Algorithm])
        user_id = payload.get('user_id')

        item = session.query(Cart).filter(
            Cart.id == item_remove.id,
            Cart.user_id == user_id
        ).first()

        if item:
            session.delete(item)
            session.commit()
            return {"message": "Item Deleted Successfully"}

        return {"message": "Item not found"}

    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class CheckoutItem(BaseModel):
    id: int          # id بتاع صف الكارت
    quantity: int    # الكمية اللي اليوزر اختارها


class CheckoutReq(BaseModel):
    token: str
    items: List[CheckoutItem]


@app.post('/cart/checkout')
async def checkout(req: CheckoutReq):
    try:
        payload = jwt.decode(req.token, Security_key, algorithms=[Algorithm])
        user_id = payload.get('user_id')

        if not req.items:
            return {"error": "Cart is empty"}

        for it in req.items:
            if it.quantity < 1:
                session.rollback()
                return {"error": "Invalid quantity"}

            cart_row = session.query(Cart).filter(
                Cart.id == it.id,
                Cart.user_id == user_id
            ).first()
            if not cart_row:
                session.rollback()
                return {"error": "Cart item not found"}

            # نفس منطق القديم: خصم من المخزون بشرط إن الكمية متاحة
            updated = session.query(Prodacts).filter(
                Prodacts.id == cart_row.pro_id,
                Prodacts.contity >= it.quantity
            ).update({Prodacts.contity: Prodacts.contity - it.quantity})

            if updated == 0:
                session.rollback()   # بيلغي أي خصم حصل لمنتجات قبله
                return {"error": f"'{cart_row.pro.name}' not available in that quantity"}

            # صف في orders لكل وحدة (زي القديم)
            for _ in range(it.quantity):
                session.add(Orders(user_id=user_id, pro_id=cart_row.pro_id))

            session.delete(cart_row)

        session.commit()
        return True

    except Exception as e:
        session.rollback()
        return {"error": str(e)}


# ===================================================================
#                              Admin
# ===================================================================
def check_admin(token: str):
    payload = jwt.decode(token, Security_key, algorithms=[Algorithm])
    user_id = payload.get('user_id')
    user = session.query(Users).filter(Users.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user


class AdminTokenReq(BaseModel):
    token: str


@app.post('/admin/users')
async def admin_get_users(req: AdminTokenReq):
    try:
        check_admin(req.token)
        users = session.query(Users).all()
        return [
            {'id': u.id, 'name': u.name, 'emil': u.emil, 'is_admin': u.is_admin}
            for u in users
        ]
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class UpdateUserReq(BaseModel):
    token: str
    user_id: int
    is_admin: bool


@app.post('/admin/users/update')
async def admin_update_user(req: UpdateUserReq):
    try:
        check_admin(req.token)
        user = session.query(Users).filter(Users.id == req.user_id).first()
        if not user:
            return {"error": "User not found"}
        user.is_admin = req.is_admin
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class DeleteUserReq(BaseModel):
    token: str
    user_id: int


@app.post('/admin/users/delete')
async def admin_delete_user(req: DeleteUserReq):
    try:
        check_admin(req.token)
        user = session.query(Users).filter(Users.id == req.user_id).first()
        if not user:
            return {"error": "User not found"}
        session.delete(user)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


# ===== Products CRUD =====
@app.post('/admin/products')
async def admin_get_products(req: AdminTokenReq):
    try:
        check_admin(req.token)
        products = session.query(Prodacts).all()
        return [
            {
                'id': p.id, 'name': p.name, 'price': p.price,
                'con': p.contity, 'stat': p.stats,
                'imgs': [img.img_path for img in p.img]
            }
            for p in products
        ]
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class CreateProductReq(BaseModel):
    token: str
    name: str
    price: float
    contity: int
    stats: bool = True


@app.post('/admin/products/create')
async def admin_create_product(req: CreateProductReq):
    try:
        check_admin(req.token)
        new_pro = Prodacts(name=req.name, price=req.price, contity=req.contity, stats=req.stats)
        session.add(new_pro)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class UpdateProductReq(BaseModel):
    token: str
    pro_id: int
    name: str
    price: float
    contity: int
    stats: bool


@app.post('/admin/products/update')
async def admin_update_product(req: UpdateProductReq):
    try:
        check_admin(req.token)
        pro = session.query(Prodacts).filter(Prodacts.id == req.pro_id).first()
        if not pro:
            return {"error": "Product not found"}
        pro.name = req.name
        pro.price = req.price
        pro.contity = req.contity
        pro.stats = req.stats
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


class DeleteProductReq(BaseModel):
    token: str
    pro_id: int


@app.post('/admin/products/delete')
async def admin_delete_product(req: DeleteProductReq):
    try:
        check_admin(req.token)
        pro = session.query(Prodacts).filter(Prodacts.id == req.pro_id).first()
        if not pro:
            return {"error": "Product not found"}
        session.delete(pro)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return {"error": str(e)}


@app.get('/admin/orders')
async def getData():
    list_of_orders = []
    orders = session.query(Orders).all()
    for order in orders:
        list_of_orders.append({
            'id': order.id,
            'customer': order.user.name,
            'product': order.pro.name,
            'qty': 1,
            'status': 'Delivered'
        })
    return list_of_orders


# ===================================================================
#                              Purchases
# ===================================================================
@app.get('/purchases')
async def deels_page(token: str):
    deels_list = []
    payload = jwt.decode(token, Security_key, algorithms=[Algorithm])
    user_id = payload.get('user_id')
    items = session.query(Orders).filter(Orders.user_id == user_id).all()
    for item in items:
        deels_list.append({
            'id': item.id,
            'user_id': item.user_id,
            'pro_id': item.pro_id,
            'name': item.pro.name,
            'img': item.pro.img[0].img_path if item.pro.img else None,
            'price': item.pro.price,
            'quantity': getattr(item, 'quantity', 1)
        })

    return deels_list


# ===================================================================
#                              Forget password
# ===================================================================
class forget_emil(BaseModel):
    emil: str


@app.post('/forget')
async def forget(mail: forget_emil):
    res = session.query(Users).filter(Users.emil == mail.emil).first()
    if res:
        return True
    else:
        return False


class passwords(BaseModel):
    passord: str
    emil: str


@app.post('/forget/reset')
async def forget_reset(user: passwords):
    hashed_pass = pwd_con.hash(user.passord)

    update_pass = session.query(Users).filter(Users.emil == user.emil).update({Users.password: hashed_pass})

    session.commit()

    if update_pass > 0:
        return {"success": True, "message": "Password updated successfully"}
    else:
        return {"success": False, "message": "User not found"}