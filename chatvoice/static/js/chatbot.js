// static/js/chatbot.js

document.addEventListener('alpine:init', () => {
    Alpine.data('chatbotApp', () => ({
        messages: [],
        inputText: '',
        isConnected: false,
        chatWs: null,
        showEmojiPicker: false,
        _isConnecting: false, // Lock to prevent double connections
        
        init() {
            this.$watch('messages', () => {
                this.$nextTick(() => this.scrollToBottom());
            });
            
            this.startChatSession();
        },

        async startChatSession() {
            // PREVENT DOUBLE EXECUTION (Fixes the double log issue)
            if (this._isConnecting) return;
            this._isConnecting = true;

            const jwtToken = localStorage.getItem('accessToken');
            if (!jwtToken) {
                this.addSystemMessage('Error: No authentication token found.', 'error');
                return;
            }

            try {
                this.addSystemMessage('Establishing secure session...');
                
                // We MUST call this to get the cookie from your /ws-session endpoint
                const res = await fetch('/api/v1/ws-session/hello_world', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${jwtToken}` }
                });

                if (!res.ok) throw new Error("Failed to establish WebSocket session");

                console.log("Cookie set. Connecting to WebSocket...");
                
                // Cookie is now in the browser, connect the WS
                this.connectWebSocket();

            } catch (error) {
                this.addSystemMessage(error.message, 'error');
                this._isConnecting = false; // Reset lock on error so they can retry
            }
        },

        connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/api/v1/ws/hello_world`;
            this.chatWs = new WebSocket(wsUrl);

            this.chatWs.onopen = () => {
                this.isConnected = true;
                this.addSystemMessage("Connected to chat securely!");
            };

            this.chatWs.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                this.addChatMessage(msg.user, msg.message);
            };

            this.chatWs.onclose = (event) => {
                this.isConnected = false;
                this._isConnecting = false; // Reset lock when disconnected
                
                if (event.code === 1008) {
                    this.addSystemMessage(`Disconnected: ${event.reason}`, 'error');
                } else {
                    this.addSystemMessage("Disconnected from server.", 'warning');
                }
            };

            this.chatWs.onerror = () => {
                this.addSystemMessage("Error connecting to WebSocket.", 'error');
            };
        },

        // ... (Keep all the other functions: sendMessage, addChatMessage, etc. exactly the same as before)
        sendMessage() {
            const text = this.inputText.trim();
            if (this.chatWs && this.chatWs.readyState === WebSocket.OPEN && text) {
                this.chatWs.send(text);
                this.inputText = '';
            }
        },

        addChatMessage(user, text) {
            const currentUser = localStorage.getItem('username');
            const role = (user === currentUser) ? 'user' : 'other';
            this.messages.push({
                id: Date.now(), role, user, content: text,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
            });
        },
        
        addSystemMessage(text, type = 'info') {
            this.messages.push({
                id: Date.now(), role: 'system', content: text, type,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
            });
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
        
        clearChat() { this.messages = []; this.addSystemMessage('Chat cleared'); },
        
        copyMessage(text) {
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
            const text = this.messages.filter(m => m.role !== 'system').map(m => `[${m.timestamp}] ${m.user || m.role}: ${m.content}`).join('\n');
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `chat-${new Date().toISOString().slice(0,10)}.txt`; a.click();
            URL.revokeObjectURL(url);
        }
    }));
});

document.addEventListener('show-toast', (e) => {
    if (window.authAppInstance) window.authAppInstance.showToast(e.detail.message, e.detail.type);
});

document.addEventListener('show-toast', (e) => {
    if (window.authAppInstance) {
        window.authAppInstance.showToast(e.detail.message, e.detail.type);
    }
});

