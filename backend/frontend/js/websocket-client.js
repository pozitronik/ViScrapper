// WebSocket client for real-time updates

class WebSocketClient {
    constructor(onProductCreated, onProductUpdated, onProductDeleted, onScrapingStatus) {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.isConnected = false;
        
        // Callback functions
        this.onProductCreated = onProductCreated;
        this.onProductUpdated = onProductUpdated;
        this.onProductDeleted = onProductDeleted;
        this.onScrapingStatus = onScrapingStatus;
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleOpen = this.handleOpen.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
        this.scheduleReconnect = this.scheduleReconnect.bind(this);
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
            console.log('WebSocket already connecting or connected');
            return;
        }
        
        try {
            // Determine WebSocket URL based on current location
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/ws`;
            
            console.log(`Connecting to WebSocket: ${wsUrl}`);
            this.ws = new WebSocket(wsUrl);
            
            // Set up event handlers
            this.ws.onopen = this.handleOpen;
            this.ws.onmessage = this.handleMessage;
            this.ws.onclose = this.handleClose;
            this.ws.onerror = this.handleError;
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }
    
    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.ws) {
            console.log('Disconnecting WebSocket');
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
        this.reconnectAttempts = 0;
    }
    
    /**
     * Handle WebSocket open event
     */
    handleOpen(event) {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Reset delay
        
        // Send initial message to confirm connection
        this.send('client_connected');
    }
    
    /**
     * Handle WebSocket message event
     */
    handleMessage(event) {
        try {
            console.log('Raw WebSocket message:', event.data);
            
            // Skip plain text echo messages from server
            if (event.data.startsWith('Message received:')) {
                console.log('Ignoring server echo message');
                return;
            }
            
            const message = JSON.parse(event.data);
            console.log('Parsed WebSocket message:', message);
            
            switch (message.type) {
                case 'product_created':
                    console.log('Handling product_created event');
                    if (this.onProductCreated) {
                        this.onProductCreated(message.data);
                    } else {
                        console.warn('No onProductCreated handler');
                    }
                    break;
                    
                case 'product_updated':
                    console.log('Handling product_updated event');
                    if (this.onProductUpdated) {
                        this.onProductUpdated(message.data);
                    } else {
                        console.warn('No onProductUpdated handler');
                    }
                    break;
                    
                case 'product_deleted':
                    console.log('Handling product_deleted event');
                    if (this.onProductDeleted) {
                        this.onProductDeleted(message.data.id);
                    } else {
                        console.warn('No onProductDeleted handler');
                    }
                    break;
                    
                case 'scraping_status':
                    console.log('Handling scraping_status event');
                    if (this.onScrapingStatus) {
                        this.onScrapingStatus(message.data.status, message.data.details);
                    } else {
                        console.warn('No onScrapingStatus handler');
                    }
                    break;
                    
                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
        }
    }
    
    /**
     * Handle WebSocket close event
     */
    handleClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnected = false;
        
        // Attempt to reconnect unless explicitly closed
        if (event.code !== 1000) { // 1000 = normal closure
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket error event
     */
    handleError(error) {
        console.error('WebSocket error:', error);
        this.isConnected = false;
    }
    
    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached. Giving up.');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
    
    /**
     * Send message to WebSocket server
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(typeof message === 'string' ? message : JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected. Cannot send message:', message);
        }
    }
    
    /**
     * Get connection status
     */
    getStatus() {
        if (!this.ws) return 'disconnected';
        
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'disconnected';
            default:
                return 'unknown';
        }
    }
}

// Export for use in other modules
window.WebSocketClient = WebSocketClient;