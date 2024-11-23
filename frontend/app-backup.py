import requests
import boto3
from flask import Flask, render_template, jsonify
from featureflags.client import CfClient
from featureflags.evaluations.auth_target import Target

app = Flask(__name__)

api_key = '8430c8fb-711f-4215-92b9-0f4c738a9899'
client = CfClient(api_key)
client.wait_for_initialization()

beta_testers = Target(identifier="test1", name="test1", attributes={"org": "blue"})

HOST_NAME = 'http://storefront-service:8989'
SERVICE_PATH = '/getproductdetails'

URL = HOST_NAME + SERVICE_PATH


def validate(products):
    """
    Validates the structure of the product data to ensure it contains
    the necessary keys: 'name', 'description', and 'price'.
    """
    if not isinstance(products, list):
        return False
    for product in products:
        if not all(key in product for key in ["name", "description", "price"]):
            return False
    return True

@app.route('/')
def hello():
    return 'Welcome to the Site'

def get_flag_status(flagstate):
    """
    Retrieves the feature flag status for the given flag state and target.
    """
    return client.bool_variation(flagstate, beta_testers, False)

@app.route('/productdetails', methods=['GET'])
def product_details():
    """
    Retrieves product details from the storefront-service and displays them in
    a catalog format if the feature flag is enabled. If the response is invalid,
    returns an appropriate error message.
    """
    result = get_flag_status("ProductDetails")
    if result:
        try:
            response = requests.get(URL)
            products = response.json()  # Try to parse the JSON response

            if validate(products):
                # Pass product data to the HTML template to display in a catalog format
                return render_template('catalog.html', products=products)
            else:
                return "Bad Request, Corrupted Response", 500
        
        except ValueError:  # Catches JSONDecodeError or invalid JSON
            return "Bad Request, Corrupted Response", 500
        except requests.RequestException as e:
            # Handle connection issues or other request-related errors
            return jsonify({"error": "Service unavailable", "details": str(e)}), 503
    else:
        # Return a beautiful webpage when the feature is unavailable
        return render_template('feature_unavailable.html'), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
