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
    except Exception as e:
        print(f"Error fetching API key: {e}")
        return None

def get_flag_status(flag_name):
    try:
        api_key = get_secret()
        if api_key is None:
            return False

        client = CfClient(api_key)
        return client.bool_variation(flag_name, beta_testers, default=False)
    except Exception as e:
        print(f"Error fetching feature flag '{flag_name}': {e}")
        return False

@app.route('/productdetails', methods=['GET'])
def product_details():
    try:
        product_details_flag = get_flag_status("ProductDetails")
        gateway1_flag = get_flag_status("Gateway1")
        gateway2_flag = get_flag_status("Gateway2")
        gateway3_flag = get_flag_status("Gateway3")

        if product_details_flag:
            response = requests.get(URL)
            products = response.json()
            return render_template(
                'catalog.html',
                products=products,
                gateway1_enabled=gateway1_flag,
                gateway2_enabled=gateway2_flag,
                gateway3_enabled=gateway3_flag
            )
        else:
            return render_template('feature_unavailable.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
