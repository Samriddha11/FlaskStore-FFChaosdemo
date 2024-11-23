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
    connect_timeout=2,
    read_timeout=2,
    retries={
        'max_attempts': 1,
        'mode': 'standard'
    }
)

def get_secret():
    secret_name = "harness_api_key"
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name, config=config)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)['api_key']
    except (ConnectTimeoutError, ReadTimeoutError) as e:
        print(f"Timeout while connecting to Secrets Manager: {e}")
        raise TimeoutError("Timeout while retrieving secret from AWS Secrets Manager")
    except (BotoCoreError, EndpointConnectionError) as e:
        print(f"Connection issue with Secrets Manager: {e}")
        raise e
    except Exception as e:
        print(f"Error fetching API key from Secrets Manager: {e}")
        return None

def validate(products):
    if not isinstance(products, list):
        return False
    for product in products:
        if not all(key in product for key in ["name", "description", "price"]):
            return False
    return True

def get_flag_status(flagstate):
    try:
        api_key = get_secret()
        if api_key is None:
            return False

        client = CfClient(api_key)
        flag_status = client.bool_variation(flagstate, beta_testers, default=False if not client.is_initialized() else True)
        return flag_status
    except (TimeoutError, ConnectTimeoutError, ReadTimeoutError) as e:
        print(f"Timeout or connection error in get_flag_status: {e}")
        return False
    except Exception as e:
        print(f"Exception in get_flag_status: {e}")
        return False

@app.route('/')
def hello():
    return 'Welcome to the Site'

@app.route('/productdetails', methods=['GET'])
def product_details():
    try:
        product_details_flag = get_flag_status("ProductDetails")
        payment_links_flag = get_flag_status("PaymentLinks")

        if product_details_flag:
            try:
                response = requests.get(URL)
                products = response.json()

                if validate(products):
                    return render_template('catalog.html', products=products, payment_links_enabled=payment_links_flag)
                else:
                    return "Bad Request, Corrupted Response", 500
            except ValueError:
                return "Bad Request, Corrupted Response", 500
            except requests.RequestException as e:
                return jsonify({"error": "Service unavailable", "details": str(e)}), 503
        else:
            return render_template('feature_unavailable.html'), 200
    except TimeoutError:
        return jsonify({"error": "Request to AWS Secrets Manager timed out"}), 504
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
