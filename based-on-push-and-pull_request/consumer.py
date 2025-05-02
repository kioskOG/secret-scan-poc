from kafka import KafkaConsumer
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

recipient_email = [
        {'name': '<update name>', 'email': '<update email>'}
    ]

sender_email = "<update email>".strip()
password = "<update_your_password>".strip()  # https://myaccount.google.com/apppasswords

host = "smtp.gmail.com"
port = 587


def send_email_alert(subject, body):
    try:
        logging.info("Connecting to SMTP server...")
        with smtplib.SMTP(host=host, port=port) as smtp_server:
            smtp_server.starttls()
            smtp_server.login(user=sender_email, password=password)
            logging.info("TLS connection established.")

            for recipient in recipient_email:
                message = MIMEMultipart('alternative')
                message['Subject'] = subject
                message['To'] = recipient['email']
                message['From'] = sender_email

                # Add plain fallback
                plain_text = "Secret found in GitHub repo. Please view this email in HTML mode."
                part1 = MIMEText(plain_text, "plain")
                part2 = MIMEText(body, "html")

                message.attach(part1)
                message.attach(part2)

                smtp_server.sendmail(
                    from_addr=sender_email,
                    to_addrs=recipient['email'],
                    msg=message.as_string()
                )
                logging.info(f"📩 Email sent to {recipient['email']}")

    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"Authentication failed: {e}")
    except smtplib.SMTPConnectError as e:
        logging.error(f"SMTP connection failed: {e}")
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


def consumer_group():
    try:
        consumer = KafkaConsumer(
            'secrets.scan.results',
            bootstrap_servers=['<update_broker_address>:9092'],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='secrets-consumer-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print("🚀 Kafka Consumer started, waiting for messages...")
    except Exception as e:
        logging.error(f"Failed to initialize Kafka consumer: {e}")
        return  # Exit early

    for message in consumer:
        data = message.value
        print("✅ Received secret scan result:")
        print(json.dumps(data, indent=2))

        if data.get("secrets_found", 0) > 0:
            print("🚨 Secrets Detected! Sending email alert...")

            # Prepare email content
            email_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.5;">
    <h2 style="color: red;">🚨 GitHub Secret Leak Detected!</h2>
    <p><strong>Repository:</strong> {data.get('repository')}</p>
    <p><strong>Commit SHA:</strong> <code>{data.get('commit_sha')}</code></p>
    <p><strong>Secrets Found:</strong> <span style="color:red; font-weight:bold;">{data.get('secrets_found')}</span></p>

    <h3>🔍 Details:</h3>
    <ul style="background:#f9f9f9; padding:10px; border-radius:8px; border:1px solid #ddd;">
"""

            for idx, finding in enumerate(data.get('findings', []), start=1):
                email_body += f"""
      <li>
        <strong>Finding #{idx}</strong><br/>
        <span><strong>File:</strong> {finding.get('SourceMetadata', {}).get('Data', {}).get('File')}</span><br/>
        <span><strong>Detector:</strong> {finding.get('DetectorName')}</span><br/>
        <span><strong>Raw:</strong> <code>{finding.get('Raw')}</code></span>
      </li>
      <br/>
"""

            email_body += """
    </ul>
    <p>✅ Please rotate affected secrets and investigate commit history.</p>
    <hr/>
    <p style="font-size: 0.9em; color: #888;">Automated email from GitHub Secret Scanning System</p>
  </body>
</html>
"""
            send_email_alert(subject="🚨 Secrets Found in GitHub Repo", body=email_body)
        else:
            print("✅ No secrets detected. No action taken.")



if __name__ == "__main__":
    consumer_group()
