from fastapi import FastAPI, Request
import json
import os
import subprocess
from kafka import KafkaProducer
from kafka import KafkaConsumer
import logging  # Added for more robust logging


# Initialize Kafka producer globally
try:
    producer = KafkaProducer(
        bootstrap_servers=['13.234.114.162:9092'],  # Or use your Kafka broker address
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except Exception as e:
    logging.error(f"Failed to initialize Kafka producer: {e}")
    producer = None  # Ensure producer is None if initialization fails

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (e.g., INFO, DEBUG, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.post("/webhook")
async def github_webhook(request: Request):
    try:
        payload = await request.json()
        logging.info("✅ Received Webhook Event:")
        logging.info(json.dumps(payload, indent=2))

        event_type = request.headers.get("X-GitHub-Event", "")
        print(event_type)

        # Extract repository clone URL and commit SHA
        repo_url = payload['repository']['clone_url']
        commit_sha = payload['after']

        logging.info(f"🔍 Repo URL: {repo_url}")
        logging.info(f"🔍 Commit SHA: {commit_sha}")

        # Directory to clone temporarily
        repo_dir = "/tmp/repo-scan"

        # Clean old dir if exists
        if os.path.exists(repo_dir):
            logging.info(f"🧹 Removing existing repo directory: {repo_dir}")
            subprocess.run(["rm", "-rf", repo_dir], check=True)  # Use check=True

        # Clone repo shallow (only latest snapshot)
        logging.info(f"📥 Cloning repository (shallow) to: {repo_dir}")
        try:
            subprocess.run(["git", "clone", "--depth", "1", repo_url, repo_dir], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Git clone failed: {e}")
            return {"status": "Error cloning repository", "error": str(e)}

        # Checkout specific commit (safety)
        logging.info(f"🔀 Checking out commit: {commit_sha}")
        try:
            subprocess.run(["git", "checkout", commit_sha], cwd=repo_dir, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Git checkout failed: {e}")
            return {"status": "Error checking out commit", "error": str(e)}

        # Run TruffleHog scan inside cloned directory
        logging.info("🚀 Running TruffleHog Scan...")
        try:
            result = subprocess.run(
                ["sudo" , "/usr/local/bin/trufflehog", "filesystem", "--json", repo_dir],  # IMPORTANT: Scan the repo_dir
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True  # Ensure TruffleHog ran successfully
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"TruffleHog scan failed: {e}")
            logging.error(f"TruffleHog stderr: {e.stderr}")  # Log stderr
            return {"status": "Trufflehog scan failed", "error": str(e)}

        findings = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    finding = json.loads(line)
                    findings.append(finding)
                except json.JSONDecodeError:
                    logging.warning(f"Skipping invalid JSON line from TruffleHog: {line}")

        if findings:
            logging.warning(f"🚨 Secrets Found: {len(findings)}")  # Use warning for secrets

            # Prepare a message
            message = {
                "repository": payload['repository']['full_name'],
                "commit_sha": payload['after'],
                "secrets_found": len(findings),
                "findings": findings
            }
            # Send to Kafka topic
            if producer:  # Check if Kafka producer was initialized successfully
                try:
                    producer.send('secrets.scan.results', message)
                    producer.flush()
                    logging.info("✅ Secrets pushed to Kafka topic: secrets.scan.results")
                except Exception as e:
                    logging.error(f"Failed to send message to Kafka: {e}")
            else:
                logging.warning("Kafka producer is not available.  Secrets not sent to Kafka.")

            return {"status": "Trufflehog scan completed", "secrets_found": len(findings)}
        else:
            logging.info("✅ No secrets found.")
            return {"status": "Trufflehog scan completed", "secrets_found": 0}


    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"status": "Error processing webhook", "error": str(e)}
