import { browser } from '$app/environment';
import { addMemory, updateMemory, removeMemory } from '$lib/stores/memories';
import type { Memory } from '$lib/types/memory';

interface WSMessage {
  type: 'memory_created' | 'memory_updated' | 'memory_deleted' | 'connection' | 'error';
  data?: any;
  memory?: Memory;
  memory_id?: string;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  
  connect() {
    if (!browser) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v2/ws`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };
      
      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.scheduleReconnect();
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      this.scheduleReconnect();
    }
  }
  
  private handleMessage(message: WSMessage) {
    switch (message.type) {
      case 'memory_created':
        if (message.memory) {
          addMemory(message.memory);
        }
        break;
        
      case 'memory_updated':
        if (message.memory) {
          updateMemory(message.memory.id, message.memory);
        }
        break;
        
      case 'memory_deleted':
        if (message.memory_id) {
          removeMemory(message.memory_id);
        }
        break;
        
      case 'connection':
        console.log('WebSocket connection established:', message.data);
        break;
        
      case 'error':
        console.error('WebSocket error:', message.data);
        break;
    }
  }
  
  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }
  
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.error('WebSocket is not connected');
    }
  }
}

export const wsClient = new WebSocketClient();