document.addEventListener('alpine:init', () => {
    Alpine.data('chatbotApp', () => ({
        messages: [],
        inputText: '',
        isConnected: false,
        chatWs: null,
        showEmojiPicker: false,
        _isConnecting: false,
        
        debugMode: false,
        isThinking: false,

        init() {
            this.$watch('messages', () => {
                this.$nextTick(() => this.scrollToBottom());
            });
            this.startChatSession();
        },

        // ─── State Controls ───
        setThinking(state) {
            this.isThinking = state;
        },

        // ─── Data Registration (Independent of Debug Mode) ───

        addSystemMessage(content, sysType = 'info') {
            this.messages.push({
                id: Date.now(), 
                type: 'system', 
                content, 
                sysType,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
            });
        },

        addMessage(user, content, side) {
            this.messages.push({
                id: Date.now(), 
                type: 'message', 
                user, 
                content, 
                side, // 'user' or 'other'
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
            });
            // Turn off thinking state automatically when a message arrives from the backend
            if (side === 'other') {
                this.setThinking(false);
            }
        },
                addTags(payload) {
            // 1. Check if payload is a string and parse it into an object
            if (typeof payload === 'string') {
                try {
                    payload = JSON.parse(payload);
                } catch (e) {
                    console.error("Failed to parse tags JSON string:", e);
                    // If it fails to parse, push it as a single error tag so you can see what went wrong
                    this.messages.push({
                        id: Date.now(), 
                        type: 'tags', 
                        tags: [{ color: 'error', key: 'json_error', value: payload }], 
                        timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                    });
                    return; // Stop execution here
                }
            }

            // 2. Flatten and assign colors
            const colors = ['primary', 'secondary', 'accent', 'info', 'success', 'warning', 'error'];
            const typeKeys = Object.keys(payload);
            let flatTags = [];

            typeKeys.forEach((typeKey, index) => {
                // Assign a consistent color based on the top-level key
                const color = colors[index % colors.length];
                const val = payload[typeKey];

                if (typeof val === 'string' || typeof val === 'number') {
                    // String/Number: use the typeKey as the tag key
                    flatTags.push({ color, key: typeKey, value: String(val) });
                } 
                else if (Array.isArray(val)) {
                    // List: use the typeKey as the tag key for each item
                    val.forEach(item => {
                        flatTags.push({ color, key: typeKey, value: String(item) });
                    });
                } 
                else if (typeof val === 'object' && val !== null) {
                    // Dictionary: use the inner keys as the tag keys
                    Object.entries(val).forEach(([innerKey, innerVal]) => {
                        flatTags.push({ color, key: innerKey, value: String(innerVal) });
                    });
                }
            });

            // 3. Push the flattened array to the messages
            this.messages.push({
                id: Date.now(), 
                type: 'tags', 
                tags: flatTags, 
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            });
        },
        addDivider(label = '') {
            this.messages.push({
                id: Date.now(), 
                type: 'divider', 
                label,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            });
        },

        // ─── Connection ───

        async startChatSession() {
            if (this._isConnecting) return;
            this._isConnecting = true;

            const jwtToken = localStorage.getItem('accessToken'); // Still using token for auth handshake
            if (!jwtToken) {
                this.addSystemMessage('Error: No authentication token found.', 'error');
                return;
            }

            try {
                this.addSystemMessage('Establishing secure session...');
                this.setThinking(true);
                
                const res = await fetch('/api/v1/ws-session/hello_world', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${jwtToken}` }
                });

                if (!res.ok) throw new Error("Failed to establish WebSocket session");
                this.connectWebSocket();

            } catch (error) {
                this.addSystemMessage(error.message, 'error');
                this._isConnecting = false;
                this.setThinking(false);
            }
        },

        connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/api/v1/ws/hello_world`;
            this.chatWs = new WebSocket(wsUrl);

            this.chatWs.onopen = () => {
                this.isConnected = true;
                this._isConnecting = false;
                this.setThinking(false);
                this.addSystemMessage("Connected to chat securely!");
            };

            this.chatWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                // Route directly based on the backend 'type' key
                if (data.type === 'message') {
                    // Everything from WS is treated as 'other' (left side)
                    this.addMessage(data.user, data.message, 'other');
                } 
                else if (data.type === 'tags') {
                    // data.message is expected to be the JSON object
                    this.addTags(data.message);
                } 
                else if (data.type === 'divider') {
                    // data.message is expected to be the string label
                    this.addDivider(data.message);
                }
            };

            this.chatWs.onclose = (event) => {
                this.isConnected = false;
                this._isConnecting = false;
                this.setThinking(false);
                if (event.code === 1008) {
                    this.addSystemMessage(`Disconnected: ${event.reason}`, 'error');
                } else {
                    this.addSystemMessage("Disconnected from server.", 'warning');
                }
            };

            this.chatWs.onerror = () => {
                this.addSystemMessage("Error connecting to WebSocket.", 'error');
                this.setThinking(false);
            };
        },

        // ─── Interactions ───

        sendMessage() {
            const text = this.inputText.trim();
            if (this.chatWs && this.chatWs.readyState === WebSocket.OPEN && text) {
                // 1. Push locally to UI as 'user' side immediately
                this.addMessage('Tú', text, 'user');
                // 2. Send raw text to backend
                this.chatWs.send(text);
                // 3. Clear input and activate thinking state
                this.inputText = '';
                this.setThinking(true);
            }
        },

        scrollToBottom() {
            const container = this.$refs.chatMessages;
            if (container) container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
        },
        
        handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage();
            }
        },
        
        clearChat() { 
            this.messages = []; 
            this.addSystemMessage('Chat cleared'); 
        },
        
        copyMessage(htmlContent) {
            // Extract plain text from HTML for clipboard
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = htmlContent;
            const text = tempDiv.innerText || tempDiv.textContent;
            
            navigator.clipboard.writeText(text).then(() => {
                document.dispatchEvent(new CustomEvent('show-toast', { detail: { message: 'Copiado al portapapeles', type: 'success' } }));
            });
        },
        
        getEmojis() { return ['😀', '😂', '🤔', '👍', '❤️', '🎉', '🔥', '✨', '😊', '🤝', '💡', '🚀']; },
        
        insertEmoji(emoji) {
            this.inputText += emoji;
            this.showEmojiPicker = false;
            this.$refs.chatInput?.focus();
        },
        
        exportChat() {
            // Only export type 'message', strip HTML tags for clean .txt file
            const text = this.messages
                .filter(m => m.type === 'message')
                .map(m => {
                    const tempDiv = document.createElement("div");
                    tempDiv.innerHTML = m.content;
                    const cleanText = tempDiv.innerText || tempDiv.textContent;
                    return `[${m.timestamp}] ${m.user}: ${cleanText}`;
                }).join('\n');
                
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); 
            a.href = url; 
            a.download = `chat-${new Date().toISOString().slice(0,10)}.txt`; 
            a.click();
            URL.revokeObjectURL(url);
        }
    }));
});

document.addEventListener('show-toast', (e) => {
    if (window.authAppInstance) {
        window.authAppInstance.showToast(e.detail.message, e.detail.type);
    }
});

