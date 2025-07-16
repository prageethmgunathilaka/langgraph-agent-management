# 🚀 FastGraph AWS Deployment Guide

## Prerequisites

1. **AWS Account** - Sign up at [aws.amazon.com](https://aws.amazon.com)
2. **AWS CLI** - Install and configure with your credentials
3. **Node.js** - For Serverless Framework (if using Lambda option)

## Option A: AWS Lambda + API Gateway (Serverless) 💰 Most Cost-Effective

### Step 1: Install Dependencies
```bash
# Install Serverless Framework
npm install -g serverless

# Install Python dependencies
pip install -r requirements.txt

# Install Serverless plugins
npm init -y
npm install serverless-python-requirements
```

### Step 2: Configure AWS Credentials
```bash
# Configure AWS CLI
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region (us-east-1)
# - Default output format (json)
```

### Step 3: Deploy to AWS Lambda
```bash
# Deploy to development
serverless deploy

# Deploy to production
serverless deploy --stage prod

# View deployment info
serverless info
```

### Step 4: Test Your Deployed API
```bash
# Test the endpoints (replace with your actual API Gateway URL)
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/health
```

### Lambda Costs:
- **Free Tier**: 1M requests/month + 400,000 GB-seconds/month
- **After Free Tier**: ~$0.20 per 1M requests + $0.0000166667 per GB-second
- **Estimated Monthly Cost**: $0.20-2.00 for low traffic

---

## Option B: AWS ECS Fargate (Container) 🐳 Production Ready

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY lambda_handler.py .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Build and Push to ECR
```bash
# Create ECR repository
aws ecr create-repository --repository-name fastgraph

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t fastgraph .
docker tag fastgraph:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/fastgraph:latest

# Push to ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/fastgraph:latest
```

### Step 3: Create ECS Service
```bash
# Create cluster
aws ecs create-cluster --cluster-name fastgraph-cluster

# Create task definition (see task-definition.json)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service --cluster fastgraph-cluster --service-name fastgraph-service --task-definition fastgraph:1 --desired-count 1
```

### ECS Costs:
- **Minimum**: ~$15-30/month (0.25 vCPU, 0.5 GB RAM running 24/7)
- **Benefits**: No cold starts, always available, better for production

---

## Option C: AWS App Runner 🏃‍♂️ Simplest Deployment

### Step 1: Create apprunner.yaml
```yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.9
  command: uvicorn src.main:app --host 0.0.0.0 --port 8000
  network:
    port: 8000
    env: PORT
  env:
    - name: PORT
      value: "8000"
```

### Step 2: Deploy via AWS Console
1. Go to AWS App Runner console
2. Create service
3. Choose "Source code repository" 
4. Connect your GitHub repository
5. App Runner will automatically build and deploy

### App Runner Costs:
- **Pay per use**: $0.064 per vCPU per hour + $0.007 per GB per hour
- **Estimated**: ~$10-25/month with auto-scaling

---

## 🎯 Recommendation

**For your FastGraph microservice, I recommend starting with Option A (Lambda):**

✅ **Pros:**
- Nearly free for development/testing
- Serverless (no server management)
- Auto-scaling
- Pay only for requests

❌ **Cons:**
- 1-3 second cold start delay
- 15-minute maximum execution time

**Next Steps:**
1. Set up AWS credentials
2. Install Serverless Framework
3. Run `serverless deploy`
4. Test your deployed API

Would you like me to help you with any specific deployment option? 