#!/usr/bin/env python3
"""Katsuragi Email Inbound — IMAP poller + attachment processor

Polls Gmail for emails sent to mecha.moby+katsuragi@gmail.com
Downloads PDF attachments, triggers review pipeline, sends acknowledgment.

Usage:
  python3 katsuragi-email.py poll          # Check for new emails (run via cron)
  python3 katsuragi-email.py reply <uid> <message>  # Reply to an email
  python3 katsuragi-email.py status        # Show recent processed emails

State tracked in: ~/.openclaw/workspace/katsuragi-email-state.json
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import json, os, sys, time, re
from pathlib import Path
from datetime import datetime

# Config
GMAIL_USER = "mecha.moby@gmail.com"
ALIAS = "mecha.moby+katsuragi@gmail.com"
CREDS_FILE = Path.home() / ".credentials" / "smtp.env"
STATE_FILE = Path.home() / ".openclaw" / "workspace" / "katsuragi-email-state.json"
ATTACHMENT_DIR = Path.home() / ".openclaw" / "media" / "inbound"
GATEWAY_URL = f"http://localhost:{os.environ.get('OPENCLAW_GATEWAY_PORT', '18789')}"
GATEWAY_TOKEN = os.environ.get('OPENCLAW_GATEWAY_TOKEN', '')

def load_creds():
    env = {}
    with open(CREDS_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"')
    return env["SMTP_PASS"]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_uids": [], "last_poll": None, "emails": []}

def save_state(state):
    state["last_poll"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))

def decode_str(s):
    """Decode email header string."""
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for data, charset in parts:
        if isinstance(data, bytes):
            result.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(data)
    return " ".join(result)

def extract_forwarded_from(body):
    """Try to extract original sender from forwarded email."""
    patterns = [
        r'From:\s*(.+?)(?:\n|<)',
        r'---------- Forwarded message ---------\s*From:\s*(.+?)(?:\n|<)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            return m.group(1).strip()
    return None

def poll():
    """Check for new emails to the Katsuragi alias."""
    password = load_creds()
    state = load_state()
    
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_USER, password)
    imap.select("INBOX")
    
    # Search ALL emails to our alias (don't rely on UNSEEN — Gmail marks read on view)
    status, data = imap.search(None, "TO", ALIAS)
    if status != "OK" or not data[0]:
        print(json.dumps({"new_emails": 0, "message": "No new emails"}))
        save_state(state)
        imap.logout()
        return []
    
    uids = data[0].split()
    new_emails = []
    
    for uid in uids:
        uid_str = uid.decode()
        
        # Skip already processed
        if uid_str in state["processed_uids"]:
            continue
        
        status, msg_data = imap.fetch(uid, "(RFC822)")
        if status != "OK":
            continue
        
        msg = email.message_from_bytes(msg_data[0][1])
        
        from_addr = decode_str(msg.get("From", ""))
        subject = decode_str(msg.get("Subject", ""))
        date = decode_str(msg.get("Date", ""))
        message_id = msg.get("Message-ID", "")
        
        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")
        
        # Extract attachments
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if filename:
                    filename = decode_str(filename)
                    # Save attachment
                    payload = part.get_payload(decode=True)
                    if payload:
                        safe_name = re.sub(r'[^\w\-\.]', '_', filename)
                        ts = int(time.time())
                        save_name = f"email_{ts}_{safe_name}"
                        save_path = ATTACHMENT_DIR / save_name
                        save_path.write_bytes(payload)
                        attachments.append({
                            "filename": filename,
                            "saved_as": str(save_path),
                            "size": len(payload),
                            "size_human": f"{len(payload)/1024:.0f}K" if len(payload) < 1048576 else f"{len(payload)/1048576:.1f}M",
                            "content_type": part.get_content_type(),
                            "is_pdf": filename.lower().endswith(".pdf"),
                        })
        
        forwarded_from = extract_forwarded_from(body)
        
        email_record = {
            "uid": uid_str,
            "from": from_addr,
            "subject": subject,
            "date": date,
            "message_id": message_id,
            "body_preview": body[:500],
            "body_full": body,
            "forwarded_from": forwarded_from,
            "attachments": attachments,
            "pdf_attachments": [a for a in attachments if a["is_pdf"]],
            "processed_at": datetime.now().isoformat(),
            "status": "new",
        }
        
        new_emails.append(email_record)
        state["processed_uids"].append(uid_str)
        state["emails"].append({
            "uid": uid_str,
            "from": from_addr,
            "subject": subject,
            "date": date,
            "attachments": len(attachments),
            "pdfs": len(email_record["pdf_attachments"]),
            "processed_at": email_record["processed_at"],
            "status": "new",
        })
    
    save_state(state)
    imap.logout()
    
    # Output for the agent
    output = {
        "new_emails": len(new_emails),
        "emails": new_emails,
    }
    print(json.dumps(output, indent=2))
    return new_emails

def send_reply(to_addr, subject, body, in_reply_to=None, references=None):
    """Send email reply via SMTP."""
    password = load_creds()
    
    msg = MIMEMultipart()
    msg["From"] = f"Katsuragi <{ALIAS}>"
    msg["To"] = to_addr
    msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = references or in_reply_to
    
    msg.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, password)
        server.send_message(msg)
    
    print(json.dumps({"sent": True, "to": to_addr, "subject": msg["Subject"]}))

def reply_cmd(args):
    """Reply to a specific email by UID."""
    if len(args) < 2:
        print("Usage: reply <uid> <message>", file=sys.stderr)
        sys.exit(1)
    
    uid = args[0]
    message = " ".join(args[1:])
    state = load_state()
    
    # Find email in state
    password = load_creds()
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_USER, password)
    imap.select("INBOX")
    
    status, msg_data = imap.fetch(uid.encode(), "(RFC822)")
    if status != "OK":
        print(f"Could not fetch email UID {uid}", file=sys.stderr)
        sys.exit(1)
    
    orig = email.message_from_bytes(msg_data[0][1])
    from_addr = decode_str(orig.get("From", ""))
    subject = decode_str(orig.get("Subject", ""))
    message_id = orig.get("Message-ID", "")
    
    # Extract just the email address
    addr_match = re.search(r'[\w\.\+\-]+@[\w\.\-]+', from_addr)
    to = addr_match.group(0) if addr_match else from_addr
    
    imap.logout()
    send_reply(to, subject, message, in_reply_to=message_id)

def status_cmd():
    """Show recent processed emails."""
    state = load_state()
    print(json.dumps({
        "last_poll": state.get("last_poll"),
        "total_processed": len(state.get("processed_uids", [])),
        "recent": state.get("emails", [])[-10:],
    }, indent=2))

def send_telegram(chat_id, text):
    """Send a Telegram message via Katsuragi's bot."""
    import urllib.request
    BOT_TOKEN = "8513519191:AAE83iYheyj6PN_XJQGxHI3iTX_HidilHL4"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)
        return False

def notify_agent(email_data):
    """Send notification to Katsuragi agent + Telegram to user."""
    import urllib.request
    
    NICK_CHAT_ID = "8515314184"
    
    pdfs = email_data.get("pdf_attachments", [])
    pdf_info = ", ".join(f"{p['filename']} ({p['size_human']})" for p in pdfs) if pdfs else "none"
    
    message = (
        f"📧 New submittal email received\n"
        f"From: {email_data['from']}\n"
        f"Subject: {email_data['subject']}\n"
        f"PDFs: {pdf_info}\n"
        f"Body preview: {email_data['body_preview'][:200]}\n"
        f"Email UID: {email_data['uid']}\n"
    )
    
    if pdfs:
        message += f"\nPDF paths:\n"
        for p in pdfs:
            message += f"  {p['saved_as']}\n"
    
    # Write to Katsuragi's INBOX.md
    notify_path = Path.home() / ".openclaw" / "workspace-katsuragi" / "INBOX.md"
    with open(notify_path, "a") as f:
        f.write(f"\n---\n## Email {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{message}\n")
    print(f"Notification written to {notify_path}", file=sys.stderr)
    
    # Send Telegram notification
    pdf_names = ", ".join(p['filename'] for p in pdfs) if pdfs else "no attachments"
    # Strip angle brackets from email addresses for clean display
    from_clean = re.sub(r'<[^>]+>', '', email_data['from']).strip()
    tg_msg = (
        f"📧 Submittal received via email\n\n"
        f"From: {from_clean}\n"
        f"Subject: {email_data['subject']}\n"
        f"Attachments: {pdf_names}\n\n"
        f"Processing now — review incoming."
    )
    if send_telegram(NICK_CHAT_ID, tg_msg):
        print("Telegram notification sent", file=sys.stderr)
    else:
        print("Telegram notification failed", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "poll":
        emails = poll()
        # Auto-notify for emails with PDFs
        for e in emails:
            if e["pdf_attachments"]:
                notify_agent(e)
    elif cmd == "reply":
        reply_cmd(sys.argv[2:])
    elif cmd == "status":
        status_cmd()
    elif cmd == "test-send":
        # Send a test email to verify outbound works
        if len(sys.argv) < 4:
            print("Usage: test-send <to> <message>")
            sys.exit(1)
        send_reply(sys.argv[2], "Test from Katsuragi", sys.argv[3])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
