#!/usr/bin/env node
/**
 * Cipher MCP Server for Warp Terminal
 * This creates a proper MCP server that Warp can communicate with
 */

const { spawn } = require('child_process');
const readline = require('readline');

// MCP Protocol Handler
class CipherMCPServer {
  constructor() {
    this.cipher = null;
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });
    
    this.setupEnvironment();
    this.setupHandlers();
  }
  
  setupEnvironment() {
    // Set Cipher environment
    process.env.CIPHER_CONFIG_PATH = process.env.CIPHER_CONFIG_PATH || `${process.env.HOME}/.cipher/config.yaml`;
    process.env.VECTOR_STORE_PROVIDER = 'qdrant';
    process.env.VECTOR_STORE_URL = 'http://localhost:6333';
    process.env.MCP_TRANSPORT = 'stdio';
  }
  
  setupHandlers() {
    // Handle incoming MCP messages from Warp
    this.rl.on('line', (line) => {
      try {
        const message = JSON.parse(line);
        this.handleMessage(message);
      } catch (e) {
        // Not JSON, might be a direct command
        this.handleDirectCommand(line);
      }
    });
    
    // Handle shutdown
    process.on('SIGINT', () => this.shutdown());
    process.on('SIGTERM', () => this.shutdown());
  }
  
  handleMessage(message) {
    // MCP protocol message handling
    switch (message.method) {
      case 'initialize':
        this.sendResponse(message.id, {
          capabilities: {
            tools: true,
            prompts: true,
            resources: true,
            sampling: true
          },
          serverInfo: {
            name: 'cipher-warp',
            version: '1.0.0'
          }
        });
        break;
        
      case 'tools/list':
        this.sendResponse(message.id, {
          tools: [
            {
              name: 'memory_search',
              description: 'Search through stored memories',
              inputSchema: {
                type: 'object',
                properties: {
                  query: { type: 'string', description: 'Search query' },
                  limit: { type: 'number', description: 'Max results' }
                },
                required: ['query']
              }
            },
            {
              name: 'memory_add',
              description: 'Add a new memory',
              inputSchema: {
                type: 'object',
                properties: {
                  content: { type: 'string', description: 'Memory content' },
                  metadata: { type: 'object', description: 'Additional metadata' }
                },
                required: ['content']
              }
            },
            {
              name: 'analyze_context',
              description: 'Analyze current context',
              inputSchema: {
                type: 'object',
                properties: {
                  path: { type: 'string', description: 'Path to analyze' }
                }
              }
            },
            {
              name: 'get_similar',
              description: 'Find similar code or commands',
              inputSchema: {
                type: 'object',
                properties: {
                  code: { type: 'string', description: 'Code to find similarities for' }
                },
                required: ['code']
              }
            }
          ]
        });
        break;
        
      case 'tools/call':
        this.handleToolCall(message);
        break;
        
      case 'prompts/list':
        this.sendResponse(message.id, {
          prompts: [
            {
              name: 'debug_help',
              description: 'Get debugging assistance with context',
              arguments: [
                { name: 'error', description: 'Error message', required: true }
              ]
            },
            {
              name: 'explain_command',
              description: 'Explain a terminal command',
              arguments: [
                { name: 'command', description: 'Command to explain', required: true }
              ]
            }
          ]
        });
        break;
        
      case 'prompts/get':
        this.handlePromptGet(message);
        break;
        
      case 'sampling/createMessage':
        this.handleSampling(message);
        break;
        
      default:
        this.sendError(message.id, `Unknown method: ${message.method}`);
    }
  }
  
  handleToolCall(message) {
    const { name, arguments: args } = message.params;
    
    // Start Cipher if not running
    if (!this.cipher) {
      this.startCipher();
    }
    
    switch (name) {
      case 'memory_search':
        this.executeCommand(`memory search "${args.query}" --limit ${args.limit || 10}`, (result) => {
          this.sendResponse(message.id, { content: result });
        });
        break;
        
      case 'memory_add':
        const metadata = args.metadata ? JSON.stringify(args.metadata) : '{}';
        this.executeCommand(`memory add "${args.content}" --metadata '${metadata}'`, (result) => {
          this.sendResponse(message.id, { content: 'Memory added successfully' });
        });
        break;
        
      case 'analyze_context':
        this.executeCommand(`context analyze ${args.path || '.'}`, (result) => {
          this.sendResponse(message.id, { content: result });
        });
        break;
        
      case 'get_similar':
        this.executeCommand(`similar "${args.code}"`, (result) => {
          this.sendResponse(message.id, { content: result });
        });
        break;
        
      default:
        this.sendError(message.id, `Unknown tool: ${name}`);
    }
  }
  
  handlePromptGet(message) {
    const { name, arguments: args } = message.params;
    
    switch (name) {
      case 'debug_help':
        this.sendResponse(message.id, {
          description: 'Debug assistance',
          messages: [
            {
              role: 'user',
              content: `Help me debug this error: ${args.error}\n\nContext from recent commands and similar past issues.`
            }
          ]
        });
        break;
        
      case 'explain_command':
        this.sendResponse(message.id, {
          description: 'Command explanation',
          messages: [
            {
              role: 'user',
              content: `Explain this command: ${args.command}\n\nInclude examples from my command history if relevant.`
            }
          ]
        });
        break;
        
      default:
        this.sendError(message.id, `Unknown prompt: ${name}`);
    }
  }
  
  handleSampling(message) {
    // Handle AI sampling requests
    const { messages, modelPreferences } = message.params;
    
    // Forward to Cipher for processing
    this.executeCommand(`chat "${messages[messages.length - 1].content}"`, (result) => {
      this.sendResponse(message.id, {
        model: modelPreferences?.hints?.find(h => h.name === 'model')?.value || 'gpt-4',
        stopReason: 'end_turn',
        content: result
      });
    });
  }
  
  handleDirectCommand(command) {
    // Handle direct terminal commands
    if (command.startsWith('cipher ')) {
      this.executeCommand(command.substring(7), (result) => {
        this.sendNotification('terminal_output', { content: result });
      });
    }
  }
  
  startCipher() {
    // Start Cipher subprocess
    this.cipher = spawn('cipher', ['cli'], {
      env: process.env,
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    this.cipher.stdout.on('data', (data) => {
      // Process Cipher output
      const output = data.toString();
      if (this.pendingCallback) {
        this.pendingCallback(output);
        this.pendingCallback = null;
      }
    });
    
    this.cipher.stderr.on('data', (data) => {
      console.error(`Cipher error: ${data}`);
    });
  }
  
  executeCommand(command, callback) {
    if (!this.cipher) {
      this.startCipher();
    }
    
    this.pendingCallback = callback;
    this.cipher.stdin.write(`${command}\n`);
  }
  
  sendResponse(id, result) {
    const response = {
      jsonrpc: '2.0',
      id: id,
      result: result
    };
    console.log(JSON.stringify(response));
  }
  
  sendError(id, error) {
    const response = {
      jsonrpc: '2.0',
      id: id,
      error: {
        code: -32000,
        message: error
      }
    };
    console.log(JSON.stringify(response));
  }
  
  sendNotification(method, params) {
    const notification = {
      jsonrpc: '2.0',
      method: method,
      params: params
    };
    console.log(JSON.stringify(notification));
  }
  
  shutdown() {
    if (this.cipher) {
      this.cipher.kill();
    }
    process.exit(0);
  }
}

// Start the server
const server = new CipherMCPServer();

// Log startup
const fs = require('fs');
fs.appendFileSync(
  `${process.env.HOME}/.cipher/warp.log`,
  `[${new Date().toISOString()}] Cipher MCP server started for Warp\n`
);