document.addEventListener('alpine:init', () => {
    Alpine.data('chatbotApp', () => ({
        messages: [],
        inputText: '',
        isConnected: false,
        chatWs: null,
        showEmojiPicker: false,
        _isConnecting: false,
        
        // New States
        debugMode: false,
        isThinking: false,

        init() {
            this.$watch('messages', () => {
                this.$nextTick(() => this.scrollToBottom());
            });
            
            this.startChatSession();
        },

        // ─── NEW: Thinking State Control ───
        setThinking(state) {
            this.isThinking = state;
        },

        // ─── NEW: Inline Debug Functions ───
        addDebugDivider(label = '') {
            this.messages.push({
                id: Date.now(), 
                role: 'debug-divider', 
                label: label,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            });
        },

        addDebugTags(tagsObject) {
            this.messages.push({
                id: Date.now(), 
                role: 'debug-tags', 
                tags: tagsObject,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            });
        },

        // ─── Connection Methods ───
        async startChatSession() {
            if (this._isConnecting) return;
            this._isConnecting = true;

            const jwtToken = localStorage.getItem('accessToken');
            if (!jwtToken) {
                this.addSystemMessage('Error: No authentication token found.', 'error');
                return;
            }

            try {
                this.addSystemMessage('Establishing secure session...');
                this.setThinking(true); // Activate thinking state
                
                const res = await fetch('/api/v1/ws-session/hello_world', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${jwtToken}` }
                });

                if (!res.ok) throw new Error("Failed to establish WebSocket session");

                this.connectWebSocket();

            } catch (error) {
                this.addSystemMessage(error.message, 'error');
                this._isConnecting = false;
                this.setThinking(false); // Deactivate on error
            }
        },

        connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/api/v1/ws/hello_world`;
            this.chatWs = new WebSocket(wsUrl);

            this.chatWs.onopen = () => {
                this.isConnected = true;
                this._isConnecting = false;
                this.setThinking(false); // Deactivate thinking when connected
                this.addSystemMessage("Connected to chat securely!");
            };

            this.chatWs.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                this.addChatMessage(msg.user, msg.message);
            };

            this.chatWs.onclose = (event) => {
                this.isConnected = false;
                this._isConnecting = false;
                this.setThinking(false); // Deactivate thinking
                
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

        // ─── Message Methods ───
        sendMessage() {
            const text = this.inputText.trim();
            if (this.chatWs && this.chatWs.readyState === WebSocket.OPEN && text) {
                
                // Example of using the new debug functions before sending:
                if (this.debugMode) {
                    this.addDebugDivider('Outgoing Message');
                    this.addDebugTags({ 'chars': text.length, 'encoding': 'utf-8' });
                }

                this.chatWs.send(text);
                this.inputText = '';
                
                // Optional: Activate thinking while waiting for response
                // this.setThinking(true);
            }
        },

        addChatMessage(user, text) {
            const currentUser = localStorage.getItem('username');
            const role = (user === currentUser) ? 'user' : 'other';
            
            // Example of using debug tags on incoming messages
            if (this.debugMode && role === 'other') {
                this.addDebugDivider('Incoming Payload');
                this.addDebugTags({ 'from': user, 'size': text.length });
            }

            this.messages.push({
                id: Date.now(), 
                role, 
                user, 
                content: text,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
            });

            // Remember to turn off thinking state when the message arrives!
            this.setThinking(false);
        },
        
        addSystemMessage(text, type = 'info') {
            this.messages.push({
                id: Date.now(), 
                role: 'system', 
                content: text, 
                type,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
            });
        },
        
        // ─── UI Methods ───
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
            const text = this.messages
                .filter(m => m.role !== 'system' && m.role !== 'debug-tags' && m.role !== 'debug-divider')
                .map(m => `[${m.timestamp}] ${m.user || m.role}: ${m.content}`)
                .join('\n');
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
