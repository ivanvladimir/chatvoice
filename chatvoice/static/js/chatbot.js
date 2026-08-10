document.addEventListener('alpine:init', () => {
    Alpine.data('chatbotApp', (url_start = null, url_ws = null, config = {}) => ({
        messages: [],
        url_start: url_start, 
        url_ws: url_ws,
        
        // ─── Configurable Options ───
        roomName: config.roomName || 'Chat Room',
        showDebug: config.showDebug !== undefined ? config.showDebug : true,
        showExport: config.showExport !== undefined ? config.showExport : true,
        enableUserTypingAnimation: config.enableUserTypingAnimation !== undefined ? config.enableUserTypingAnimation : true,
        userTypingSpeed: config.userTypingSpeed || 25, // ms per character
        
        inputText: '',
        isConnected: false,
        chatWs: null,
        showEmojiPicker: false,
        _isConnecting: false,
        _typingAnimationFrames: [], // Tracks active typing timeouts
        _animationQueue: [],
        _isCurrentlyAnimating: false,        
        debugMode: false,
        isThinking: false,
        isListening: false, 

        init() {
            this.$watch('messages', () => {
                this.$nextTick(() => this.scrollToBottom());
            });

            if (!this.url_start || !this.url_ws) {
                this.addSystemMessage('Error: Chat URLs not configured', 'error');
                return;
            }

            this.startChatSession();
        },

        // ─── State Controls ───
        setThinking(state) {
            this.isThinking = state;
        },
        setListening(state) {
            this.isListening = state;
            if (state) {
                this.isThinking = false;
                this.$nextTick(() => {
                    this.$refs.chatInput?.focus();
                });
            }
        },

        // ─── Data Registration ───
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
            const messageId = Date.now();
            const timestamp = new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
            
            // Apply typing animation ONLY to 'other' (system/bot)
            if (side === 'other' && this.enableUserTypingAnimation) {
                // Store the raw data temporarily
                const data = { id: messageId, user, content, timestamp };
                
                // If nothing is animating right now, start immediately
                if (!this._isCurrentlyAnimating) {
                    this._startNextAnimation(data);
                } else {
                    // Otherwise, add it to the waiting queue
                    this._animationQueue.push(data);
                }
            } else {
                // Standard instant push for user messages
                this.messages.push({
                    id: messageId, 
                    type: 'message', 
                    user, 
                    content, 
                    side,
                    timestamp
                });
            }
            
            if (side === 'other') {
                this.setThinking(false);
            }
        },

        _startNextAnimation(data) {
            this._isCurrentlyAnimating = true;
            
            // 1. Push the raw object into the array (Alpine turns it into a Proxy here)
            this.messages.push({
                id: data.id, 
                type: 'message', 
                user: data.user, 
                content: '', 
                fullContent: data.content,
                _typeIndex: 0, 
                isAnimating: true,
                side: 'other',
                timestamp: data.timestamp
            });
            
            // 2. CRITICAL FIX: Grab the PROXIED version directly from the array!
            const messageObj = this.messages[this.messages.length - 1];
            
            this.$nextTick(() => this.scrollToBottom());
            
            // 3. Pass the Proxy to the animation function
            this._animateMessage(messageObj);
        },

        _animateMessage(messageObj) {
            // Pre-calculate total words once
            const totalWords = messageObj.fullContent.split(/(\s+)/).length;
            const speed = this.userTypingSpeed * 3; 
            
            const animate = () => {
                // If we haven't reached the last word yet
                if (messageObj._typeIndex < totalWords - 1) {
                    messageObj._typeIndex++; // Just add 1 to the number!
                    const frameId = setTimeout(animate, speed); 
                    this._typingAnimationFrames.push(frameId);
                    this.$nextTick(() => this.scrollToBottom());
                } else {
                    // Animation complete. Set final content and clean up.
                    messageObj.content = messageObj.fullContent;
                    messageObj.isAnimating = false;
                    messageObj._typeIndex = 0;
                    this._typingAnimationFrames = [];
                    
                    // Check queue for next message
                    if (this._animationQueue.length > 0) {
                        const nextData = this._animationQueue.shift();
                        this._startNextAnimation(nextData);
                    } else {
                        this._isCurrentlyAnimating = false;
                    }
                }
            };
            animate();
        },

        _cancelTypingAnimations() {
            this._typingAnimationFrames.forEach(id => clearTimeout(id));
            this._typingAnimationFrames = [];
            this.messages.forEach(m => {
                if (m.isAnimating && m.fullContent) {
                    m.content = m.fullContent;
                    m.isAnimating = false;
                    m._typeIndex = 0; // <-- ADD THIS
                }
            });
        },

        addTags(payload) {
            if (typeof payload === 'string') {
                try {
                    payload = JSON.parse(payload);
                } catch (e) {
                    console.error("Failed to parse tags JSON string:", e);
                    this.messages.push({
                        id: Date.now(), 
                        type: 'tags', 
                        tags: [{ color: 'error', key: 'json_error', value: payload }], 
                        timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                    });
                    return;
                }
            }

            const colors = ['primary', 'secondary', 'accent', 'info', 'success', 'warning', 'error'];
            const typeKeys = Object.keys(payload);
            let flatTags = [];

            typeKeys.forEach((typeKey, index) => {
                const color = colors[index % colors.length];
                const val = payload[typeKey];

                if (typeof val === 'string' || typeof val === 'number') {
                    flatTags.push({ color, key: typeKey, value: String(val) });
                } 
                else if (Array.isArray(val)) {
                    val.forEach(item => {
                        flatTags.push({ color, key: typeKey, value: String(item) });
                    });
                } 
                else if (typeof val === 'object' && val !== null) {
                    Object.entries(val).forEach(([innerKey, innerVal]) => {
                        flatTags.push({ color, key: innerKey, value: String(innerVal) });
                    });
                }
            });

            this.messages.push({
                id: Date.now(), 
                type: 'tags', 
                tags: flatTags, 
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            });
        },

        addDivider(tag = '', message = '') {
            this.messages.push({
                id: Date.now(), 
                type: 'divider', 
                tag: tag,
                message: message,
                timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            });
        },

        // ─── Connection ───
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
                
                const res = await fetch(this.url_start, {
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
            const wsUrl = this.url_ws;
            this.chatWs = new WebSocket(wsUrl);

            this.chatWs.onopen = () => {
                this.isConnected = true;
                this._isConnecting = false;
                this.setThinking(false);
                this.addSystemMessage("Connected to chat securely!");
            };

            this.chatWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'message') {
                    this.addMessage(data.user, data.message, 'other');
                } 
                else if (data.type === 'tags') {
                    this.addTags(data.message);
                } 
                else if (data.type === 'divider') {
                    this.addDivider(data.tag, data.message);
                }
                else if (data.type === 'listen') {
                    this.setListening(true);
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
                this.setListening(false);
                this.addMessage('Tú', text, 'user');
                this.chatWs.send(text);
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
            this._cancelTypingAnimations();
            this._animationQueue = [];       // Empty the waiting line
            this._isCurrentlyAnimating = false; // Reset the lock
            this.messages = []; 
            this.addSystemMessage('Chat cleared'); 
        },
        
        copyMessage(htmlContent) {
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
            let exportLines = [];

            this.messages.forEach(m => {
                if (m.type === 'message') {
                    const tempDiv = document.createElement("div");
                    tempDiv.innerHTML = m.content;
                    const cleanText = tempDiv.innerText || tempDiv.textContent;
                    exportLines.push(`[${m.timestamp}] ${m.user || 'Sistema'}: ${cleanText}`);
                } 
                else if (m.type === 'divider' && this.debugMode) {
                    let dividerText = `\n--- [ ${m.tag || 'DEBUG STEP'} ] ---`;
                    if (m.message) {
                        const tempDiv = document.createElement("div");
                        tempDiv.innerHTML = m.message;
                        const cleanMsg = tempDiv.innerText || tempDiv.textContent;
                        dividerText += `\n> ${cleanMsg.trim()}`;
                    }
                    exportLines.push(dividerText);
                } 
                else if (m.type === 'tags' && this.debugMode) {
                    if (m.tags && m.tags.length > 0) {
                        const tagsStr = m.tags.map(t => `${t.key}=${t.value}`).join(' | ');
                        exportLines.push(`[Tags] ${tagsStr}`);
                    }
                }
            });

            const text = exportLines.join('\n');
            
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
