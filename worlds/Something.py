#setting up communication in my lab😭

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json

clients = []
messages = []

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Lab LAN Chat</title>
<style>
body {
    font-family: Arial;
    background: #111827;
    color: white;
    max-width: 800px;
    margin: 40px auto;
    padding: 20px;
}
h1 { text-align: center; }
#chat {
    height: 450px;
    overflow-y: auto;
    background: #1f2937;
    padding: 15px;
    border-radius: 10px;
}
.msg {
    padding: 8px;
    margin: 6px 0;
    background: #374151;
    border-radius: 6px;
}
input {
    padding: 12px;
    box-sizing: border-box;
}
#name { width: 25%; }
#message { width: 55%; }
button {
    width: 15%;
    padding: 12px;
    cursor: pointer;
}
</style>
</head>

<body>

<h1>💬 Lab LAN Chat</h1>

<input id="name" placeholder="Your name">
<input id="message" placeholder="Type message...">
<button onclick="sendMessage()">Send</button>

<div id="chat"></div>

<script>

let last = 0;

async function loadMessages() {
    const response = await fetch('/messages');
    const data = await response.json();

    if (data.length !== last) {
        document.getElementById("chat").innerHTML =
            data.map(m =>
                `<div class="msg"><b>${m.name}</b>: ${m.text}</div>`
            ).join("");

        last = data.length;

        const chat = document.getElementById("chat");
        chat.scrollTop = chat.scrollHeight;
    }
}

async function sendMessage() {

    const name = document.getElementById("name").value || "Anonymous";
    const text = document.getElementById("message").value;

    if (!text) return;

    await fetch('/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name: name,
            text: text
        })
    });

    document.getElementById("message").value = "";
    loadMessages();
}

document.getElementById("message").addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

setInterval(loadMessages, 500);
loadMessages();

</script>

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/":
            data = HTML.encode()

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(data))
            self.end_headers()

            self.wfile.write(data)

        elif self.path == "/messages":

            data = json.dumps(messages).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(data))
            self.end_headers()

            self.wfile.write(data)

        else:
            self.send_error(404)

    def do_POST(self):

        if self.path == "/send":

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            message = json.loads(body)

            messages.append({
                "name": message.get("name", "Anonymous"),
                "text": message.get("text", "")
            })

            print(
                f"[{message.get('name', 'Anonymous')}] "
                f"{message.get('text', '')}"
            )

            self.send_response(200)
            self.end_headers()

        else:
            self.send_error(404)


server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)

print("=================================")
print("      LAB LAN CHAT SERVER")
print("=================================")
print()
print("Server running on port 8000")
print("Other PCs should open:")
print()
print("http://172.16.47.174:8000")
print()
print("Press CTRL+C to stop.")
print()

server.serve_forever()
