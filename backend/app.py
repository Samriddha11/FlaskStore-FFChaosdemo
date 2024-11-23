from flask import Flask, jsonify
import redis

app = Flask(__name__)
redis_obj = redis.Redis(host='redis-service', port=6379, db=0, charset="utf-8", decode_responses=True)

# Set product details in Redis (name, description, price)
@app.route('/setproductdetails')
def set_product_details():
    products = {
        "P_Books": {"name": "Books", "description": "Various genres of books", "price": 15.99},
        "P_Laptops": {"name": "Laptops", "description": "High-performance laptops", "price": 799.99},
        "P_Calculators": {"name": "Calculators", "description": "Scientific calculators", "price": 25.99},
        "P_Playstation": {"name": "Playstation", "description": "Gaming console", "price": 499.99},
        "P_Mobile_Phones": {"name": "Mobile Phones", "description": "Latest smartphones", "price": 999.99},
        "P_Televisions": {"name": "Televisions", "description": "Smart 4K TVs", "price": 899.99}
    }
    
    # Store product details in Redis
    for key, product in products.items():
        redis_obj.hmset(key, product)
    
    return jsonify({"status": "Product details set in Redis"})

# Get product details from Redis
@app.route('/getproductdetails')
def get_product_details():
    product_details_list = []
    
    for key in redis_obj.keys():
        product = redis_obj.hgetall(key)
        product_details_list.append(product)
    
    return jsonify(product_details_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8989)
