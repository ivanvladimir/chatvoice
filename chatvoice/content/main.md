---
title: Principal
---

<div class="hero min-h-[60vh]">
    <div class="hero-content text-center">
        <div class="max-w-md">
            <h1 class="text-5xl font-bold">Bienvenido a Chatvoice</h1>
            <p class="py-6">Entra para tener una conversación.</p>
            <button class="btn btn-primary btn-lg" @click="showLoginModal = true">
                Comenzar ahora
            </button>
        </div>
    </div>
</div>

<!-- STEP 3: Chat UI (Hidden initially) -->
<div id="chat-box" class="box">
    <div id="messages"></div>
    <input type="text" id="messageText" placeholder="Type a message...">
    <button onclick="sendMessage()" id="sendBtn" disabled>Send</button>
</div>

<script>
    let ws;

    // ==========================================
    // STEP 1: Login to get the JWT
    // ==========================================
    async function handleLogin() {
        const username = document.getElementById("username").value;
        if (!username) return alert("Please enter a username");

        try {
            const res = await fetch(`/login?username=${username}`, { method: 'POST' });
            if (!res.ok) throw new Error("Login failed");
            
            const data = await res.json();
            // Pass the JWT to the next step
            await establishWsSession(data.access_token);
            
        } catch (error) {
            alert(error.message);
        }
    }

    // ==========================================
    // STEP 2: Trade JWT for an HttpOnly Cookie
    // ==========================================
    async function establishWsSession(jwtToken) {
        try {
            // We send the JWT in the header. The server will reply by setting a cookie.
            const res = await fetch('/ws-session', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${jwtToken}` }
            });

            if (!res.ok) throw new Error("Failed to establish WebSocket session");

            // The browser has now automatically stored the httpOnly cookie.
            // We no longer need the JWT in JavaScript memory.
            console.log("Session cookie set. Connecting to WebSocket...");
            
            // Update UI
            document.getElementById("login-box").style.display = "none";
            document.getElementById("chat-box").style.display = "block";
            
            // Move to final step
            connectWebSocket();

        } catch (error) {
            alert(error.message);
        }
    }

    // ==========================================
    // STEP 3: Connect to WebSocket
    // ==========================================
    function connectWebSocket() {
        // Notice the URL is completely clean! 
        // The browser automatically attaches the httpOnly cookie we just received.
        const wsUrl = `ws://${window.location.host}/ws`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            document.getElementById("messageText").disabled = false;
            document.getElementById("sendBtn").disabled = false;
            addSystemMessage("Connected to chat securely!");
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            addChatMessage(msg.user, msg.message);
        };

        ws.onclose = (event) => {
            document.getElementById("messageText").disabled = true;
            document.getElementById("sendBtn").disabled = true;
            
            // Code 1008 means Policy Violation (Auth failed)
            if (event.code === 1008) {
                addSystemMessage(`Disconnected: ${event.reason}`);
            } else {
                addSystemMessage("Disconnected from server.");
            }
        };

        ws.onerror = () => {
            addSystemMessage("Error connecting to WebSocket.");
        };
    }

    // ==========================================
    // Chat Helpers
    // ==========================================
    function sendMessage() {
        const input = document.getElementById("messageText");
        if (ws && ws.readyState === WebSocket.OPEN && input.value) {
            ws.send(input.value);
            input.value = '';
        }
    }

    function addChatMessage(user, text) {
        const div = document.createElement("div");
        div.innerText = `${user}: ${text}`;
        document.getElementById("messages").appendChild(div);
        scrollChat();
    }

    function addSystemMessage(text) {
        const div = document.createElement("div");
        div.className = "system-msg";
        div.innerText = `* ${text}`;
        document.getElementById("messages").appendChild(div);
        scrollChat();
    }

    function scrollChat() {
        const container = document.getElementById("messages");
        container.scrollTop = container.scrollHeight;
    }

    // Allow pressing "Enter" to send
    document.getElementById("messageText").addEventListener("keypress", function(e) {
        if (e.key === "Enter") sendMessage();
    });
</script>


