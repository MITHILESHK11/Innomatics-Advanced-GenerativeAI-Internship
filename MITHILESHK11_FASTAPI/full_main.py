from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI()

# -----------------------------
# Product Database
# -----------------------------

products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 99, "category": "Stationery", "in_stock": True},
    {"id": 3, "name": "Pen Set", "price": 49, "category": "Stationery", "in_stock": True},
    {"id": 4, "name": "USB Hub", "price": 799, "category": "Electronics", "in_stock": False}
]

orders = []
feedback = []
cart = []

# -----------------------------
# Basic Store APIs
# -----------------------------

@app.get("/")
def home():
    return {"message": "FastAPI Store API Running"}

@app.get("/products")
def get_products():
    return {"products": products, "total": len(products)}

@app.get("/products/category/{category}")
def get_products_by_category(category: str):
    result = [p for p in products if p["category"].lower() == category.lower()]
    if not result:
        return {"error": "No products found in this category"}
    return {"category": category, "products": result}

@app.get("/products/instock")
def get_instock():
    result = [p for p in products if p["in_stock"]]
    return {"in_stock_products": result, "count": len(result)}

@app.get("/products/search/{keyword}")
def search_products(keyword: str):
    result = [p for p in products if keyword.lower() in p["name"].lower()]
    return {"keyword": keyword, "results": result}

@app.get("/products/deals")
def get_deals():
    cheapest = min(products, key=lambda p: p["price"])
    expensive = max(products, key=lambda p: p["price"])
    return {"best_deal": cheapest, "premium_pick": expensive}

# -----------------------------
# Day-2 Filters
# -----------------------------

@app.get("/products/filter")
def filter_products(
    min_price: int = Query(None),
    max_price: int = Query(None),
    category: str = Query(None)
):
    result = products

    if min_price:
        result = [p for p in result if p["price"] >= min_price]

    if max_price:
        result = [p for p in result if p["price"] <= max_price]

    if category:
        result = [p for p in result if p["category"].lower() == category.lower()]

    return {"filtered_products": result}

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return {"name": product["name"], "price": product["price"]}
    return {"error": "Product not found"}

# -----------------------------
# Feedback System
# -----------------------------

class CustomerFeedback(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.dict())
    return {
        "message": "Feedback submitted successfully",
        "feedback": data.dict(),
        "total_feedback": len(feedback)
    }

# -----------------------------
# Product Summary
# -----------------------------

@app.get("/products/summary")
def product_summary():
    in_stock = [p for p in products if p["in_stock"]]
    out_stock = [p for p in products if not p["in_stock"]]

    expensive = max(products, key=lambda p: p["price"])
    cheapest = min(products, key=lambda p: p["price"])

    categories = list(set(p["category"] for p in products))

    return {
        "total_products": len(products),
        "in_stock_count": len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive": {"name": expensive["name"], "price": expensive["price"]},
        "cheapest": {"name": cheapest["name"], "price": cheapest["price"]},
        "categories": categories
    }

# -----------------------------
# Bulk Orders
# -----------------------------

class OrderItem(BaseModel):
    product_id: int
    quantity: int

class BulkOrder(BaseModel):
    company_name: str
    contact_email: str
    items: List[OrderItem]

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):

    confirmed = []
    failed = []
    grand_total = 0

    for item in order.items:

        product = next((p for p in products if p["id"] == item.product_id), None)

        if not product:
            failed.append({"product_id": item.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})

    return {"company": order.company_name, "confirmed": confirmed, "failed": failed, "grand_total": grand_total}

# -----------------------------
# CART SYSTEM (Day-5)
# -----------------------------

def calculate_total(product, quantity):
    return product["price"] * quantity

@app.post("/cart/add")
def add_to_cart(product_id: int, quantity: int = 1):

    product = next((p for p in products if p["id"] == product_id), None)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product["in_stock"]:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")

    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            item["subtotal"] = calculate_total(product, item["quantity"])
            return {"message": "Cart updated", "cart_item": item}

    subtotal = calculate_total(product, quantity)

    cart_item = {
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "subtotal": subtotal
    }

    cart.append(cart_item)

    return {"message": "Added to cart", "cart_item": cart_item}

@app.get("/cart")
def view_cart():

    if not cart:
        return {"message": "Cart is empty"}

    grand_total = sum(item["subtotal"] for item in cart)

    return {
        "items": cart,
        "item_count": len(cart),
        "grand_total": grand_total
    }

@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):

    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": "Item removed from cart"}

    raise HTTPException(status_code=404, detail="Item not found in cart")

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str

@app.post("/cart/checkout")
def checkout(data: CheckoutRequest):

    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")

    grand_total = 0
    created_orders = []

    for item in cart:

        order_id = len(orders) + 1

        order = {
            "order_id": order_id,
            "customer_name": data.customer_name,
            "delivery_address": data.delivery_address,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "total_price": item["subtotal"]
        }

        grand_total += item["subtotal"]
        orders.append(order)
        created_orders.append(order)

    cart.clear()

    return {"orders_placed": created_orders, "grand_total": grand_total}

@app.get("/orders")
def view_orders():
    return {"orders": orders, "total_orders": len(orders)}