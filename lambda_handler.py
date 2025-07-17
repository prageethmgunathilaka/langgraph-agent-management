import json
from mangum import Mangum

# Import the correct app from the app directory
from app.main import app

# Create the Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """
    AWS Lambda handler function
    """
    return handler(event, context) 