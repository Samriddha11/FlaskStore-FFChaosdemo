import requests
import boto3
from flask import Flask, render_template, jsonify
from featureflags.client import CfClient
from featureflags.evaluations.auth_target import Target
from botocore.config import Config
from botocore.exceptions import BotoCoreError, EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError
import json

app = Flask(__name__)

# Target for feature flag evaluation
beta_testers = Target(identifier="test1", name="test1", attributes={"org": "blue"})

# External service URL
HOST_NAME = 'http://storefront-service:8989'
SERVICE_PATH = '/getproductdetails'
URL = HOST_NAME + SERVICE_PATH

# Boto3 configuration for timeouts and retries
config = Config(
    connect_timeout=2,         # 2 seconds to connect
    read_timeout=2,            # 2 seconds to read
    retries={
        'max_attempts': 1,     # Retry up to 1 time
        'mode': 'standard'     # Standard retry mode
    }
)

def get_secret():
    """Fetch the API key from AWS Secrets Manager."""
    secret_name = "harness_api_key"
    region_name = "us-east-1"  # Change this to your AWS region

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name, config=config)

    try:
        # Retrieve secret value from AWS Secrets Manager
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)['api_key']  # Assuming the key is stored as a JSON object
    except (ConnectTimeoutError, ReadTimeoutError) as e:
        print(f"Timeout while connecting to Secrets Manager: {e}")
        raise TimeoutError("Timeout while retrieving secret from AWS Secrets Manager")
    except (BotoCoreError, EndpointConnectionError) as e:
        print(f"Connection issue with Secrets Manager: {e}")
        raise e  # Reraise to handle it later
    except Exception as e:
        print(f"Error fetching API key from Secrets Manager: {e}")
        return None

def validate(products):
    """Validate the product data structure."""
    if not isinstance(products, list):
        return False
    for product in products:
        if not all(key in product for key in ["name", "description", "price"]):
            return False
    return True
def get_flag_status(flagstate):
    """Retrieve the feature flag status."""
    try:
        api_key = get_secret()
        if api_key is None:
            print("Failed to retrieve API key, returning False for flag status.")
            return False

        # Initialize the feature flag client with the retrieved API key
        client = CfClient(api_key)

        # Check client initialization and retrieve the flag with a default value
        flag_status = client.bool_variation(flagstate, beta_testers, default=False if not client.is_initialized() else True)

        # Instead of waiting for initialization, attempt to retrieve the flag directly
        # Log and return the flag status
        if not client.is_initialized():
            print("Feature flag client is not initialized, returning False for flag status.")
        return flag_status
        
        # Fetch the flag status without waiting
        #return client.bool_variation(flagstate, beta_testers, True)
    except (TimeoutError, ConnectTimeoutError, ReadTimeoutError) as e:
        print(f"Timeout or connection error in get_flag_status: {e}")
        return False
    except Exception as e:
        print(f"Exception in get_flag_status: {e}")
        return False  # Consider the feature flag off in case of an error


@app.route('/')
def hello():
    """Simple route to confirm the service is running."""
    return 'Welcome to the Site'

@app.route('/productdetails', methods=['GET'])
def product_details():
    """Retrieve and display product details if the feature flag is enabled."""
    try:
        flag_enabled = get_flag_status("ProductDetails")
        print(f"Feature flag status for 'ProductDetails': {flag_enabled}")
        
        if flag_enabled:
            try:
                response = requests.get(URL)
                products = response.json()  # Try to parse the JSON response

                if validate(products):
                    return render_template('catalog.html', products=products)
                else:
                    print("Invalid product data structure received.")
                    return "Bad Request, Corrupted Response", 500
            except ValueError:  # Catches JSONDecodeError or invalid JSON
                print("Invalid JSON response received.")
                return "Bad Request, Corrupted Response", 500
            except requests.RequestException as e:
                print(f"Error during request to external service: {e}")
                return jsonify({"error": "Service unavailable", "details": str(e)}), 503
        else:
            print("Feature flag is disabled or an error occurred. Showing feature unavailable page.")
            return render_template('feature_unavailable.html'), 200
    except TimeoutError:
        print("Timeout while retrieving secret, returning 504 error.")
        return jsonify({"error": "Request to AWS Secrets Manager timed out"}), 504
    except Exception as e:
        print(f"Internal server error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
