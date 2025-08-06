<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';
  import { memories } from '$lib/stores/memories';
  
  let canvas: HTMLCanvasElement;
  let ctx: CanvasRenderingContext2D;
  let nodes: any[] = [];
  let links: any[] = [];
  let simulation: any;
  
  onMount(async () => {
    ctx = canvas.getContext('2d')!;
    
    // Set canvas size
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight - 64; // Account for nav
    };
    resize();
    window.addEventListener('resize', resize);
    
    // Load memories and create graph
    await loadGraph();
    
    // Simple force simulation
    animate();
    
    return () => {
      window.removeEventListener('resize', resize);
    };
  });
  
  async function loadGraph() {
    try {
      const response = await api.listMemories({ limit: 100 });
      memories.set(response.memories);
      
      // Create nodes from memories
      nodes = response.memories.map((memory, i) => ({
        id: memory.id,
        label: memory.memory_type,
        content: memory.content.slice(0, 50) + '...',
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: 0,
        vy: 0,
        importance: memory.importance_score,
        tags: memory.tags
      }));
      
      // Create links based on shared tags
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const sharedTags = nodes[i].tags.filter((tag: string) => 
            nodes[j].tags.includes(tag)
          );
          if (sharedTags.length > 0) {
            links.push({
              source: i,
              target: j,
              strength: sharedTags.length
            });
          }
        }
      }
    } catch (e) {
      console.error('Failed to load graph:', e);
    }
  }
  
  function animate() {
    // Simple physics simulation
    const alpha = 0.1;
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // Apply forces
    nodes.forEach((node, i) => {
      // Gravity towards center
      node.vx += (centerX - node.x) * 0.001;
      node.vy += (centerY - node.y) * 0.001;
      
      // Repulsion between nodes
      nodes.forEach((other, j) => {
        if (i !== j) {
          const dx = node.x - other.x;
          const dy = node.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            const force = (100 - dist) / dist * 0.5;
            node.vx += dx * force;
            node.vy += dy * force;
          }
        }
      });
      
      // Apply velocity
      node.vx *= 0.9; // Damping
      node.vy *= 0.9;
      node.x += node.vx;
      node.y += node.vy;
      
      // Keep within bounds
      node.x = Math.max(20, Math.min(canvas.width - 20, node.x));
      node.y = Math.max(20, Math.min(canvas.height - 20, node.y));
    });
    
    // Draw
    ctx.fillStyle = '#f3f4f6';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw links
    ctx.strokeStyle = '#e5e7eb';
    links.forEach(link => {
      const source = nodes[link.source];
      const target = nodes[link.target];
      ctx.lineWidth = link.strength;
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();
    });
    
    // Draw nodes
    nodes.forEach(node => {
      const radius = 10 + node.importance * 20;
      
      // Node circle
      ctx.fillStyle = node.importance > 0.7 ? '#ef4444' : 
                      node.importance > 0.4 ? '#f59e0b' : '#6b7280';
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fill();
      
      // Label
      ctx.fillStyle = '#1f2937';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y - radius - 5);
    });
    
    requestAnimationFrame(animate);
  }
</script>

<div class="relative w-full h-screen">
  <canvas
    bind:this={canvas}
    class="absolute inset-0"
  />
  
  <!-- Info Panel -->
  <div class="absolute top-4 left-4 bg-white dark:bg-gray-800 p-4 rounded-lg shadow-lg max-w-xs">
    <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">
      Knowledge Graph
    </h2>
    <p class="text-sm text-gray-600 dark:text-gray-300 mb-4">
      Visualizing {nodes.length} memories connected by shared tags.
    </p>
    <div class="space-y-2 text-xs">
      <div class="flex items-center">
        <div class="w-4 h-4 bg-red-500 rounded-full mr-2"></div>
        <span class="text-gray-700 dark:text-gray-300">High importance</span>
      </div>
      <div class="flex items-center">
        <div class="w-4 h-4 bg-amber-500 rounded-full mr-2"></div>
        <span class="text-gray-700 dark:text-gray-300">Medium importance</span>
      </div>
      <div class="flex items-center">
        <div class="w-4 h-4 bg-gray-500 rounded-full mr-2"></div>
        <span class="text-gray-700 dark:text-gray-300">Low importance</span>
      </div>
    </div>
  </div>
</div>

<style>
  canvas {
    cursor: grab;
  }
  
  canvas:active {
    cursor: grabbing;
  }
</style>