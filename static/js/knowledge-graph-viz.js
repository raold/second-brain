/**
 * Knowledge Graph Visualization Component
 * D3.js force-directed graph for Second Brain v2.8.0
 */

class KnowledgeGraphViz {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: options.width || 800,
            height: options.height || 600,
            nodeRadius: options.nodeRadius || 8,
            linkDistance: options.linkDistance || 100,
            chargeStrength: options.chargeStrength || -300,
            ...options
        };
        
        this.svg = null;
        this.simulation = null;
        this.nodes = [];
        this.links = [];
        this.selectedNode = null;
        
        this.colorScale = {
            person: '#FF6B6B',
            organization: '#4ECDC4',
            technology: '#45B7D1',
            concept: '#96CEB4',
            location: '#FECA57',
            event: '#DDA0DD',
            skill: '#98D8C8',
            topic: '#F7DC6F',
            other: '#95A5A6'
        };
        
        this.init();
    }
    
    init() {
        // Create SVG
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.options.width)
            .attr('height', this.options.height)
            .attr('class', 'knowledge-graph');
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });
        
        this.svg.call(zoom);
        
        // Create main group
        this.g = this.svg.append('g');
        
        // Define arrow markers for directed edges
        this.svg.append('defs').selectAll('marker')
            .data(['end'])
            .enter().append('marker')
            .attr('id', 'arrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#999');
        
        // Create force simulation
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(this.options.linkDistance))
            .force('charge', d3.forceManyBody().strength(this.options.chargeStrength))
            .force('center', d3.forceCenter(this.options.width / 2, this.options.height / 2))
            .force('collision', d3.forceCollide().radius(d => d.size || this.options.nodeRadius));
        
        // Create containers for links and nodes
        this.linkGroup = this.g.append('g').attr('class', 'links');
        this.nodeGroup = this.g.append('g').attr('class', 'nodes');
        
        // Tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'graph-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('padding', '10px')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', 'white')
            .style('border-radius', '5px')
            .style('font-size', '12px')
            .style('pointer-events', 'none');
    }
    
    loadData(graphData) {
        this.nodes = graphData.nodes || [];
        this.links = graphData.edges || graphData.links || [];
        
        this.update();
    }
    
    update() {
        // Update links
        const link = this.linkGroup
            .selectAll('line')
            .data(this.links);
        
        link.exit().remove();
        
        const linkEnter = link.enter()
            .append('line')
            .attr('class', 'link')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.sqrt(d.weight || 1) * 2)
            .attr('marker-end', 'url(#arrow)');
        
        linkEnter.append('title')
            .text(d => d.label || d.type);
        
        this.linkSelection = linkEnter.merge(link);
        
        // Update nodes
        const node = this.nodeGroup
            .selectAll('g')
            .data(this.nodes);
        
        node.exit().remove();
        
        const nodeEnter = node.enter()
            .append('g')
            .attr('class', 'node')
            .call(this.drag());
        
        // Add circles
        nodeEnter.append('circle')
            .attr('r', d => d.size || this.options.nodeRadius)
            .attr('fill', d => this.colorScale[d.type] || this.colorScale.other)
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .on('click', (event, d) => this.onNodeClick(event, d))
            .on('mouseover', (event, d) => this.onNodeHover(event, d))
            .on('mouseout', () => this.onNodeOut());
        
        // Add labels
        nodeEnter.append('text')
            .attr('dx', 12)
            .attr('dy', 4)
            .text(d => d.label || d.id)
            .style('font-size', '12px')
            .style('fill', '#333');
        
        this.nodeSelection = nodeEnter.merge(node);
        
        // Update simulation
        this.simulation
            .nodes(this.nodes)
            .on('tick', () => this.tick());
        
        this.simulation.force('link')
            .links(this.links);
        
        this.simulation.alpha(1).restart();
    }
    
    tick() {
        this.linkSelection
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        this.nodeSelection
            .attr('transform', d => `translate(${d.x},${d.y})`);
    }
    
    drag() {
        return d3.drag()
            .on('start', (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on('end', (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            });
    }
    
    onNodeClick(event, node) {
        event.stopPropagation();
        
        // Toggle selection
        if (this.selectedNode === node) {
            this.selectedNode = null;
            this.highlightConnected(null);
        } else {
            this.selectedNode = node;
            this.highlightConnected(node);
        }
        
        // Emit event for external handlers
        if (this.options.onNodeClick) {
            this.options.onNodeClick(node);
        }
    }
    
    onNodeHover(event, node) {
        // Show tooltip
        this.tooltip
            .style('opacity', 1)
            .html(`
                <strong>${node.label}</strong><br>
                Type: ${node.type}<br>
                ${node.metadata ? `${Object.entries(node.metadata).map(([k, v]) => `${k}: ${v}`).join('<br>')}` : ''}
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        
        // Highlight on hover
        this.softHighlight(node);
    }
    
    onNodeOut() {
        this.tooltip.style('opacity', 0);
        
        if (!this.selectedNode) {
            this.clearHighlight();
        }
    }
    
    highlightConnected(node) {
        if (!node) {
            this.clearHighlight();
            return;
        }
        
        // Get connected nodes
        const connectedNodeIds = new Set([node.id]);
        
        this.links.forEach(link => {
            if (link.source.id === node.id) {
                connectedNodeIds.add(link.target.id);
            } else if (link.target.id === node.id) {
                connectedNodeIds.add(link.source.id);
            }
        });
        
        // Update node opacity
        this.nodeSelection.selectAll('circle')
            .attr('opacity', d => connectedNodeIds.has(d.id) ? 1 : 0.2);
        
        this.nodeSelection.selectAll('text')
            .attr('opacity', d => connectedNodeIds.has(d.id) ? 1 : 0.2);
        
        // Update link opacity
        this.linkSelection
            .attr('opacity', d => 
                (d.source.id === node.id || d.target.id === node.id) ? 1 : 0.1
            );
    }
    
    softHighlight(node) {
        if (this.selectedNode) return;
        
        const connectedNodeIds = new Set([node.id]);
        
        this.links.forEach(link => {
            if (link.source.id === node.id) {
                connectedNodeIds.add(link.target.id);
            } else if (link.target.id === node.id) {
                connectedNodeIds.add(link.source.id);
            }
        });
        
        this.nodeSelection.selectAll('circle')
            .attr('opacity', d => connectedNodeIds.has(d.id) ? 1 : 0.6);
    }
    
    clearHighlight() {
        this.nodeSelection.selectAll('circle').attr('opacity', 1);
        this.nodeSelection.selectAll('text').attr('opacity', 1);
        this.linkSelection.attr('opacity', 0.6);
    }
    
    // Filter nodes by type
    filterByType(types) {
        const filteredNodes = this.nodes.filter(n => types.includes(n.type));
        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
        
        const filteredLinks = this.links.filter(l => 
            filteredNodeIds.has(l.source.id || l.source) && 
            filteredNodeIds.has(l.target.id || l.target)
        );
        
        this.update({ nodes: filteredNodes, links: filteredLinks });
    }
    
    // Search nodes
    searchNodes(query) {
        if (!query) {
            this.clearHighlight();
            return;
        }
        
        const matchingNodes = this.nodes.filter(n => 
            n.label.toLowerCase().includes(query.toLowerCase())
        );
        
        this.nodeSelection.selectAll('circle')
            .attr('opacity', d => 
                matchingNodes.some(n => n.id === d.id) ? 1 : 0.2
            );
    }
    
    // Export as image
    exportAsPNG(filename = 'knowledge-graph.png') {
        const svgData = this.svg.node().outerHTML;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        canvas.width = this.options.width;
        canvas.height = this.options.height;
        
        img.onload = function() {
            ctx.drawImage(img, 0, 0);
            canvas.toBlob(function(blob) {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);
            });
        };
        
        img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
    }
    
    // Export as JSON
    exportAsJSON(filename = 'knowledge-graph.json') {
        const data = {
            nodes: this.nodes,
            links: this.links
        };
        
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    // Resize graph
    resize(width, height) {
        this.options.width = width;
        this.options.height = height;
        
        this.svg
            .attr('width', width)
            .attr('height', height);
        
        this.simulation.force('center', d3.forceCenter(width / 2, height / 2));
        this.simulation.alpha(0.3).restart();
    }
}

// Export for use
window.KnowledgeGraphViz = KnowledgeGraphViz;