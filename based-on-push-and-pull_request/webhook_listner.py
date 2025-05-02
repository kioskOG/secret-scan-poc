from fastapi import FastAPI, Request
import json
import os
import subprocess
import logging
import requests
import shutil
import tempfile
from kafka import KafkaProducer

# ENV variables
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "<update_broker_address>:9092")

# Generate a github PAT
# And then export GITHUB_TOKEN=<Your_pat>

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Init FastAPI
app = FastAPI()

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Kafka
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
except Exception as e:
    logging.error(f"❌ Kafka init failed: {e}")
    producer = None

def set_commit_status(repo_full_name, sha, state, description):
    if not GITHUB_TOKEN:
        logging.warning("🔒 GITHUB_TOKEN not set. Skipping status update.")
        return

    url = f"https://api.github.com/repos/{repo_full_name}/statuses/{sha}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    payload = {
        "state": state,
        "description": description,
        "context": "Secret Scan"
    }

    resp = requests.post(url, headers=headers, json=payload)
    logging.info(f"🔁 GitHub Status: {resp.status_code} - {resp.text}")

@app.post("/webhook")
async def github_webhook(request: Request):
    try:
        payload = await request.json()
        logging.info("✅ Webhook received.")
        event_type = request.headers.get("X-GitHub-Event", "")
        logging.info(f"📦 GitHub event type: {event_type}")

        # Detect event type
        if event_type == "pull_request" and payload["action"] in ["opened", "synchronize"]:
            pr = payload["pull_request"]
            commit_sha = pr["head"]["sha"]
            repo_url = pr["head"]["repo"]["clone_url"]
        # elif event_type == "push":
        #     commit_sha = payload.get("after")
        #     if commit_sha == "0000000000000000000000000000000000000000":
        #         logging.warning("🚫 Skipping deleted branch push event.")
        #         return {"status": "ref deleted"}
        #     repo_url = payload["repository"]["clone_url"]
        else:
            logging.info(f"❌ Unsupported GitHub event: {event_type}")
            return {"status": "ignored"}

        repo_full_name = payload["repository"]["full_name"]

        # Create a temp directory
        repo_dir = tempfile.mkdtemp(prefix="repo-scan-")
        logging.info(f"📁 Temp directory created: {repo_dir}")

        # Clone without checkout
        subprocess.run(["git", "clone", "--no-checkout", repo_url, repo_dir], check=True)
        subprocess.run(["git", "fetch", "origin", commit_sha], cwd=repo_dir, check=True)
        subprocess.run(["git", "checkout", commit_sha], cwd=repo_dir, check=True)

        # Run TruffleHog scan
        logging.info("🚀 Running TruffleHog...")
        result = subprocess.run(
            ["sudo", "/usr/local/bin/trufflehog", "filesystem", "--json", repo_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        findings = []
        for line in result.stdout.strip().splitlines():
            if line:
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    logging.warning(f"⚠️ Skipped bad JSON line: {line}")

        secrets_found = len(findings)
        logging.info(f"🔎 Secrets found: {secrets_found}")

        # Send to Kafka if available
        if secrets_found > 0 and producer:
            try:
                producer.send("secrets.scan.results", {
                    "repository": repo_full_name,
                    "commit_sha": commit_sha,
                    "secrets_found": secrets_found,
                    "findings": findings
                })
                producer.flush()
                logging.info("✅ Kafka message sent.")
            except Exception as e:
                logging.error(f"❌ Kafka send failed: {e}")

        # GitHub commit status
        if event_type in ["push", "pull_request"]:
            state = "failure" if secrets_found > 0 else "success"
            desc = f"{secrets_found} secret(s) found" if secrets_found else "No secrets found"
            set_commit_status(repo_full_name, commit_sha, state, desc)

        return {"status": "scan complete", "secrets_found": secrets_found}

    except Exception as e:
        logging.error(f"❌ Unhandled error: {e}")
        return {"status": "error", "detail": str(e)}

    finally:
        if 'repo_dir' in locals() and os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
            logging.info(f"🧹 Cleaned up temp directory: {repo_dir}")
