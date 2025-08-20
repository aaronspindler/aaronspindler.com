class HomepageKnowledgeGraph {
    constructor() {
        this.initConfig();
        this.initDOM();
        this.initVisualization();
        this.bindEvents();
        this.loadData();
    }
    
    initConfig() {
        // Consolidated configuration
        this.CONFIG = {
            dimensions: { width: 800, height: 500 },
            tooltip: { padding: 20, maxWidth: 380, offset: 20, animDuration: 250 },
            node: { minRadius: 6, maxRadius: 16, externalRadius: 8, baseRadius: 5, multiplier: 1.5 },
            label: { maxLength: 26, shortLength: 18 },
            animation: { rippleDuration: 1000, rippleRadius: 50, resizeDebounce: 150 },
            force: {
                linkDistance: 90, chargeStrength: -200, collisionRadius: 25,
                centerStrength: 0.02, categoryStrength: 0.25, basePadding: 60,
                paddingPerNode: 12, labelRepulsion: 40, labelRadius: 140
            }
        };
        
        // Color scheme
        this.COLORS = {
            blogPost: '#888', externalLink: '#aaa', highlight: '#fff',
            categories: {
                tech: { node: '#5fb4b6', hull: 'rgba(95,180,182,0.2)', border: 'rgba(95,180,182,0.7)', text: '#7dd8da' },
                personal: { node: '#c594c5', hull: 'rgba(197,148,197,0.2)', border: 'rgba(197,148,197,0.7)', text: '#dbb3db' },
                projects: { node: '#fac863', hull: 'rgba(250,200,99,0.2)', border: 'rgba(250,200,99,0.7)', text: '#ffd885' },
                default: { node: '#999', hull: 'rgba(153,153,153,0.2)', border: 'rgba(153,153,153,0.7)', text: '#bbb' }
            }
        };
    }
    
    initDOM() {
        this.svg = d3.select("#knowledge-graph-svg");
        this.container = d3.select("#knowledge-graph-container");
        this.loading = d3.select("#loading");
        
        const rect = this.container.node().getBoundingClientRect();
        this.width = rect.width || this.CONFIG.dimensions.width;
        this.height = rect.height || this.CONFIG.dimensions.height;
    }
    
    initVisualization() {
        // Setup SVG
        this.svg.attr("viewBox", [0, 0, this.width, this.height])
            .attr("width", this.width).attr("height", this.height);
        
        // Setup zoom
        this.zoom = d3.zoom().scaleExtent([0.1, 3])
            .on("zoom", e => this.g.attr("transform", e.transform));
        this.svg.call(this.zoom);
        
        // Create main group
        this.g = this.svg.append("g");
        
        // Initial zoom state
        const initScale = 0.2;
        this.svg.call(this.zoom.transform, d3.zoomIdentity
            .translate(this.width/2*(1-initScale), this.height/2*(1-initScale))
            .scale(initScale));
        
        // Tooltip and controls
        this.tooltipGroup = this.svg.append("g").attr("class", "svg-tooltip");
        this.addControls();
    }
    
    addControls() {
        this.svg.append("text")
            .attr("x", 10).attr("y", this.height - 10)
            .attr("class", "controls-info")
            .text("F: fit • R: reset • Scroll: zoom • Drag: pan");
    }
    
    bindEvents() {
        // Debounced resize handler
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.handleResize(), this.CONFIG.animation.resizeDebounce);
        });
        
        // Keyboard shortcuts
        window.addEventListener('keydown', e => {
            if (!e.ctrlKey && !e.metaKey && !e.altKey) {
                if (e.key === 'f') this.fitGraphToView();
                if (e.key === 'r') this.resetZoom();
            }
        });
    }
    
    async loadData(forceRefresh = false) {
        try {
            this.loading.style("display", "block");
            const url = `/api/knowledge-graph/?${forceRefresh ? 'refresh=true&' : ''}t=${Date.now()}`;
            const response = await fetch(url);
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const result = await response.json();
            if (result.status === 'success') {
                this.renderGraph(result.data);
            } else {
                console.error('API error:', result.error);
            }
        } catch (error) {
            console.error('Failed to load graph data:', error);
        } finally {
            this.loading.style("display", "none");
        }
    }
    
    renderGraph(data) {
        this.g.selectAll("*").remove();
        
        const { nodes, edges, categories } = data;
        if (!nodes?.length) return;
        
        this.graphData = data;
        this.categories = categories || {};
        
        this.initializeNodePositions(nodes);
        this.createSimulation(nodes, edges);
        
        // Create visual elements (order matters for layering)
        this.hullGroup = this.g.append("g").attr("class", "hulls");
        this.createLinks(edges);
        this.createNodes(nodes);
        this.createLabels(nodes);
        // Create category label group AFTER nodes to ensure labels are on top
        this.categoryLabelGroup = this.g.append("g").attr("class", "category-labels");
        
        this.addNodeInteractions();
        
        // Start simulation
        this.simulation.alpha(1.0).alphaDecay(0.01).velocityDecay(0.5).restart();
        // Immediate hull update to show labels right away
        this.updateCategoryHulls();
        // Update again after initial settling
        setTimeout(() => this.updateCategoryHulls(), 500);
        // Final update after more settling
        setTimeout(() => this.updateCategoryHulls(), 1500);
    }
    
    initializeNodePositions(nodes) {
        const centerX = this.width / 2, centerY = this.height / 2;
        const categoryGroups = {}, externalLinks = [];
        
        // Group nodes
        nodes.forEach(node => {
            if (node.type === 'external_link') {
                externalLinks.push(node);
            } else {
                const cat = node.category || 'uncategorized';
                (categoryGroups[cat] = categoryGroups[cat] || []).push(node);
            }
        });
        
        // Position categories
        this.categoryCenters = {};
        const categories = Object.keys(categoryGroups);
        const angleStep = (2 * Math.PI) / Math.max(categories.length, 1);
        const groupRadius = Math.min(this.width, this.height) * 0.28;
        
        categories.forEach((cat, i) => {
            const angle = i * angleStep;
            const cx = centerX + groupRadius * Math.cos(angle);
            const cy = centerY + groupRadius * Math.sin(angle);
            this.categoryCenters[cat] = { x: cx, y: cy };
            
            // Position nodes in category
            this.positionCategoryNodes(categoryGroups[cat], cx, cy);
        });
        
        // Position external links
        if (externalLinks.length) {
            const outerRadius = Math.min(this.width, this.height) * 0.42;
            const extAngleStep = (2 * Math.PI) / externalLinks.length;
            externalLinks.forEach((node, i) => {
                const angle = i * extAngleStep + Math.random() * 0.1;
                const r = outerRadius * (0.95 + Math.random() * 0.1);
                node.x = centerX + r * Math.cos(angle);
                node.y = centerY + r * Math.sin(angle);
            });
        }
    }
    
    positionCategoryNodes(nodes, cx, cy) {
        const count = nodes.length;
        if (count === 1) {
            nodes[0].x = cx;
            nodes[0].y = cy;
        } else {
            const maxRadius = 80;
            let placed = 0, ring = 0;
            
            while (placed < count) {
                const inRing = ring === 0 ? 1 : Math.min(6 * ring, count - placed);
                const r = ring === 0 ? 0 : (maxRadius * ring) / Math.ceil(Math.sqrt(count));
                
                for (let i = 0; i < inRing && placed < count; i++) {
                    const angle = (i / inRing) * 2 * Math.PI;
                    nodes[placed].x = cx + r * Math.cos(angle);
                    nodes[placed].y = cy + r * Math.sin(angle);
                    placed++;
                }
                ring++;
            }
        }
    }
    
    createSimulation(nodes, edges) {
        const linkForce = d3.forceLink(edges).id(d => d.id)
            .distance(d => {
                if (d.source.type === 'external_link' || d.target.type === 'external_link') return this.CONFIG.force.linkDistance * 1.8;
                if (d.source.category === d.target.category) return this.CONFIG.force.linkDistance * 0.8;
                return this.CONFIG.force.linkDistance;
            }).strength(0);
        
        const chargeForce = d3.forceManyBody()
            .strength(d => d.type === 'external_link' ? this.CONFIG.force.chargeStrength * 2 : this.CONFIG.force.chargeStrength * 0.05);
        
        const collisionForce = d3.forceCollide()
            .radius(d => d.type === 'external_link' ? this.CONFIG.force.collisionRadius * 1.8 : this.CONFIG.force.collisionRadius * 0.5)
            .strength(0.3);
        
        this.simulation = d3.forceSimulation(nodes)
            .force("link", linkForce)
            .force("charge", chargeForce)
            .force("collision", collisionForce)
            .force("categoryX", d3.forceX(d => this.getTargetX(d)).strength(0.005))
            .force("categoryY", d3.forceY(d => this.getTargetY(d)).strength(0.005));
        
        this.forces = { link: linkForce, charge: chargeForce, collision: collisionForce };
        
        // Optimized tick handler
        let tickCount = 0;
        let hasUpdatedOnStable = false;
        this.simulation.on("tick", () => {
            const alpha = this.simulation.alpha();
            this.updateForceStrengths(alpha);
            this.updatePositions();
            
            // Update hulls more frequently for first few ticks to ensure labels appear
            if (tickCount < 10 || tickCount % 3 === 0) {
                requestAnimationFrame(() => this.updateCategoryHulls());
            }
            tickCount++;
            
            // Ensure category labels appear when simulation stabilizes
            if (!hasUpdatedOnStable && alpha < 0.5) {
                hasUpdatedOnStable = true;
                requestAnimationFrame(() => this.updateCategoryHulls());
            }
            
            // Auto-fit once
            if (!this.hasAutoFitted && alpha < 0.4) {
                this.hasAutoFitted = true;
                setTimeout(() => this.fitGraphToView(), 500);
            }
        });
    }
    
    getTargetX(d) {
        if (d.type === 'external_link') {
            const angle = Math.atan2(d.y - this.height/2, d.x - this.width/2);
            return this.width/2 + Math.min(this.width, this.height) * 0.42 * Math.cos(angle);
        }
        return this.categoryCenters[d.category || 'uncategorized']?.x || this.width/2;
    }
    
    getTargetY(d) {
        if (d.type === 'external_link') {
            const angle = Math.atan2(d.y - this.height/2, d.x - this.width/2);
            return this.height/2 + Math.min(this.width, this.height) * 0.42 * Math.sin(angle);
        }
        return this.categoryCenters[d.category || 'uncategorized']?.y || this.height/2;
    }
    
    updateForceStrengths(alpha) {
        if (!this.forces) return;
        
        const progress = 1 - alpha;
        const ease = progress < 0.3 ? progress * progress * 0.5 :
                     progress < 0.7 ? 0.045 + (progress - 0.3) * 1.14 :
                     0.5 + Math.sqrt((progress - 0.7) / 0.3) * 0.5;
        
        // Update forces progressively
        this.forces.link.strength(d => {
            const base = d.source.type === 'external_link' || d.target.type === 'external_link' ? 0.5 :
                        d.source.category === d.target.category ? 1.5 : 1.0;
            return base * ease * 0.8;
        });
        
        this.forces.charge.strength(d => {
            const base = d.type === 'external_link' ? this.CONFIG.force.chargeStrength * 2 :
                        this.CONFIG.force.chargeStrength * 0.5;
            return base * Math.min(1, ease * 1.2) * 0.8;
        });
        
        this.forces.collision.radius(d => {
            const base = d.type === 'external_link' ? this.CONFIG.force.collisionRadius * 1.8 :
                        this.CONFIG.force.collisionRadius;
            return base * (0.5 + 0.5 * ease);
        }).strength(0.3 + 0.7 * ease);
        
        const catStrength = d => d.type === 'external_link' ? 0.01 + 0.15 * ease :
                                0.005 + (this.CONFIG.force.categoryStrength - 0.005) * ease * 0.8;
        this.simulation.force("categoryX").strength(catStrength);
        this.simulation.force("categoryY").strength(catStrength);
        
        this.simulation.velocityDecay(0.5 - 0.2 * ease);
    }
    
    createLinks(edges) {
        this.link = this.g.append("g").attr("class", "links")
            .selectAll("line").data(edges).enter().append("line")
            .attr("class", d => `link ${d.type}`)
            .attr("stroke", d => d.type === 'internal' ? this.COLORS.blogPost : this.COLORS.externalLink)
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", d => d.type === 'internal' ? 2 : 1);
    }
    
    createNodes(nodes) {
        this.node = this.g.append("g").attr("class", "nodes")
            .selectAll("circle").data(nodes).enter().append("circle")
            .attr("class", d => d.type === 'blog_post' ? `node blog-post ${d.category || 'uncategorized'}` : `node ${d.type}`)
            .attr("r", d => this.getNodeRadius(d))
            .attr("fill", d => {
                if (d.type === 'blog_post') {
                    const cat = d.category || 'default';
                    return (this.COLORS.categories[cat] || this.COLORS.categories.default).node;
                }
                return this.COLORS.externalLink;
            })
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .call(this.createDragBehavior());
    }
    
    createLabels(nodes) {
        this.labels = this.g.append("g").attr("class", "node-labels-group")
            .selectAll("text").data(nodes).enter().append("text")
            .attr("class", d => `node-label ${d.type === 'blog_post' ? 'blog-post-number' : d.type === 'external_link' ? 'external-link' : ''}`)
            .text(d => this.getNodeLabel(d));
    }
    
    addNodeInteractions() {
        this.node
            .on("mouseover", (e, d) => { this.showTooltip(e, d); this.highlightConnections(d); })
            .on("mouseout", () => { this.hideTooltip(); this.clearHighlights(); })
            .on("click", (e, d) => this.handleNodeClick(e, d));
    }
    
    updatePositions() {
        this.link?.attr("x1", d => d.source.x || 0).attr("y1", d => d.source.y || 0)
                 .attr("x2", d => d.target.x || 0).attr("y2", d => d.target.y || 0);
        
        this.node?.attr("cx", d => d.x || 0).attr("cy", d => d.y || 0);
        
        const allNodes = this.simulation?.nodes() || [];
        this.labels?.each((d, i, nodes) => {
            const pos = this.calculateLabelPosition(d, allNodes);
            d3.select(nodes[i]).attr("x", pos.x).attr("y", pos.y);
        });
    }
    
    calculateLabelPosition(d, allNodes) {
        const radius = this.getNodeRadius(d);
        const x = d.x || 0, y = d.y || 0;
        
        if (d.type === 'external_link') {
            const positions = [
                {x: x + radius + 8, y}, {x: x - radius - 8, y},
                {x, y: y + radius + 15}, {x, y: y - radius - 15}
            ];
            
            // Find least overlapping position
            return positions.reduce((best, pos) => {
                const overlap = allNodes.reduce((sum, other) => {
                    if (other === d) return sum;
                    const dist = Math.hypot(pos.x - (other.x || 0), pos.y - (other.y || 0));
                    const otherR = this.getNodeRadius(other);
                    return sum + Math.max(0, otherR + 20 - dist);
                }, 0);
                return overlap < best.overlap ? {x: pos.x, y: pos.y, overlap} : best;
            }, {x: positions[0].x, y: positions[0].y, overlap: Infinity});
        }
        
        return d.type === 'blog_post' ? {x, y: y + 4} : {x, y: y + radius + 12};
    }
    
    updateCategoryHulls() {
        if (!this.hullGroup) return;
        
        const categoryGroups = {};
        const nodes = this.simulation?.nodes() || [];
        
        // Group nodes by category
        nodes.forEach(node => {
            if (node.type === 'blog_post' && node.category && node.x !== undefined && node.y !== undefined && 
                !isNaN(node.x) && !isNaN(node.y)) {
                (categoryGroups[node.category] = categoryGroups[node.category] || []).push([node.x, node.y]);
            }
        });
        
        // Clear and redraw
        this.hullGroup.selectAll("*").remove();
        this.categoryLabelGroup?.selectAll("*").remove();
        this.categoryLabelBounds = [];
        
        // Draw hulls
        Object.entries(categoryGroups).forEach(([category, points]) => {
            if (!points.length) return;
            
            const color = this.COLORS.categories[category] || this.COLORS.categories.default;
            const padding = this.CONFIG.force.basePadding + points.length * this.CONFIG.force.paddingPerNode;
            
            if (points.length === 1) {
                this.drawSingleNodeHull(points[0], category, color, padding);
            } else if (points.length === 2) {
                this.drawTwoNodeHull(points, category, color, padding);
            } else {
                this.drawMultiNodeHull(points, category, color, padding);
            }
        });
    }
    
    drawSingleNodeHull([x, y], category, color, padding) {
        this.hullGroup.append("circle")
            .attr("class", `category-hull hull-${category}`)
            .attr("cx", x).attr("cy", y).attr("r", padding)
            .style("fill", color.hull).style("stroke", color.border);
        
        // Position label at the top of the hull (inside)
        const labelY = y - padding + 25; // Position near the top inner edge
        this.addCategoryLabel(x, labelY, category, color);
    }
    
    drawTwoNodeHull(points, category, color, padding) {
        const [[x1, y1], [x2, y2]] = points;
        const midX = (x1 + x2) / 2, midY = (y1 + y2) / 2;
        const dist = Math.hypot(x2 - x1, y2 - y1);
        const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        
        this.hullGroup.append("ellipse")
            .attr("class", `category-hull hull-${category}`)
            .attr("cx", midX).attr("cy", midY)
            .attr("rx", dist/2 + padding).attr("ry", padding)
            .attr("transform", `rotate(${angle} ${midX} ${midY})`)
            .style("fill", color.hull).style("stroke", color.border);
        
        // Position label at the top of the hull (inside)
        // Find the topmost point of the two nodes
        const topY = Math.min(y1, y2);
        const labelY = topY - padding + 25; // Position near the top inner edge
        this.addCategoryLabel(midX, labelY, category, color);
    }
    
    drawMultiNodeHull(points, category, color, padding) {
        const hull = d3.polygonHull(points);
        if (!hull) return;
        
        const expanded = this.expandHull(hull, padding);
        const path = d3.line().x(d => d[0]).y(d => d[1]).curve(d3.curveCatmullRomClosed.alpha(0.7))(expanded);
        
        this.hullGroup.append("path")
            .attr("class", `category-hull hull-${category}`)
            .attr("d", path)
            .style("fill", color.hull).style("stroke", color.border);
        
        // Position label at the top of the hull (inside)
        const centroid = d3.polygonCentroid(points);
        const topY = Math.min(...points.map(p => p[1]));
        const labelY = topY - padding + 25; // Position near the top inner edge
        this.addCategoryLabel(centroid[0], labelY, category, color);
    }
    
    expandHull(hull, padding) {
        const centroid = d3.polygonCentroid(hull);
        return hull.map(point => {
            const dx = point[0] - centroid[0], dy = point[1] - centroid[1];
            const dist = Math.hypot(dx, dy);
            if (dist === 0) return point;
            const scale = (dist + padding * (1 + (Math.random() - 0.5) * 0.1)) / dist;
            return [centroid[0] + dx * scale, centroid[1] + dy * scale];
        });
    }
    
    addCategoryLabel(x, y, category, color) {
        if (!this.categoryLabelGroup) return;
        // Ensure position is valid
        if (!isFinite(x) || !isFinite(y)) return;
        
        // Calculate text width approximation  
        const textWidth = category.length * 12 + 20;  // Add padding
        const textHeight = 24;
        
        // Create a group for the label and background
        const labelGroup = this.categoryLabelGroup.append("g")
            .attr("class", "category-label-group");
        
        // Add a semi-transparent background rect for better visibility
        labelGroup.append("rect")
            .attr("x", x - textWidth/2)
            .attr("y", y - textHeight/2)
            .attr("width", textWidth)
            .attr("height", textHeight)
            .attr("rx", 4)  // Rounded corners
            .attr("ry", 4)
            .style("fill", "rgba(26, 26, 26, 0.7)")  // Dark semi-transparent background
            .style("stroke", color.border)
            .style("stroke-width", 1);
        
        // Add label text on top
        labelGroup.append("text")
            .attr("class", "category-label")
            .attr("x", x)
            .attr("y", y)
            .text(category.toUpperCase());
        
        // Log for debugging
        console.log(`Added category label: ${category} at (${x.toFixed(1)}, ${y.toFixed(1)})`);
        
        this.categoryLabelBounds.push({x: x, y: y, width: textWidth, height: textHeight, category});
    }
    
    getNodeRadius(node) {
        if (node.type === 'blog_post') {
            const connections = (node.in_degree || 0) + (node.out_degree || 0);
            return Math.max(this.CONFIG.node.minRadius, 
                           Math.min(this.CONFIG.node.maxRadius, 
                                   this.CONFIG.node.minRadius + connections * this.CONFIG.node.multiplier));
        }
        return node.type === 'external_link' ? this.CONFIG.node.externalRadius : this.CONFIG.node.baseRadius;
    }
    
    getNodeLabel(node) {
        if (node.type === 'blog_post') {
            const match = node.id.match(/^(\d{4})/);
            return match ? match[1] : node.label.substring(0, this.CONFIG.label.shortLength);
        }
        if (node.type === 'external_link') {
            return node.domain ? node.domain.substring(0, this.CONFIG.label.maxLength) : 
                                node.label.substring(0, this.CONFIG.label.shortLength);
        }
        return node.domain || node.label.substring(0, this.CONFIG.label.shortLength);
    }
    
    createDragBehavior() {
        return d3.drag()
            .on("start", (e, d) => { if (!e.active) this.simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
            .on("end", (e, d) => { if (!e.active) this.simulation.alphaTarget(0); d.fx = null; d.fy = null; });
    }
    
    showTooltip(event, node) {
        this.tooltipGroup.selectAll("*").remove();
        
        let label = node.label;
        if (node.type === 'blog_post') {
            label = label.replace(/^\d{1,4}[_\-\s]*/, '').replace(/_/g, ' ').replace(/\.html?$/i, '').trim();
            if (label.length) label = label.charAt(0).toUpperCase() + label.slice(1);
        } else if (node.type === 'external_link' && node.domain) {
            label = node.domain;
        }
        
        const padding = 8, width = Math.min(200, Math.max(label.length * 7 + padding * 2, 60)), height = 24;
        const x = Math.max(10, Math.min((node.x || 0) - width/2, this.width - width - 10));
        const y = Math.max(10, (node.y || 0) - this.getNodeRadius(node) - height - 10);
        
        this.tooltipGroup.append("rect").attr("class", "tooltip-background")
            .attr("x", x).attr("y", y).attr("width", width).attr("height", height);
        
        this.tooltipGroup.append("text")
            .attr("x", x + width/2).attr("y", y + height/2).text(label);
        
        this.tooltipGroup.classed("hidden", false).classed("visible", true);
    }
    
    hideTooltip() {
        this.tooltipGroup.classed("visible", false).classed("hidden", true);
        this.tooltipGroup.selectAll("*").remove();
    }
    
    highlightConnections(targetNode) {
        this.clearHighlights();
        
        const connected = new Set();
        const edges = this.simulation?.force("link").links() || [];
        
        edges.forEach(edge => {
            const sourceId = edge.source.id || edge.source;
            const targetId = edge.target.id || edge.target;
            if (sourceId === targetNode.id || targetId === targetNode.id) {
                connected.add(sourceId);
                connected.add(targetId);
            }
        });
        
        this.node?.classed("highlighted", d => connected.has(d.id));
        this.labels?.classed("highlighted", d => connected.has(d.id));
        this.link?.classed("highlighted", d => {
            const sId = d.source.id || d.source;
            const tId = d.target.id || d.target;
            return sId === targetNode.id || tId === targetNode.id;
        });
    }
    
    clearHighlights() {
        this.node?.classed("highlighted", false);
        this.labels?.classed("highlighted", false);
        this.link?.classed("highlighted", false);
    }
    
    handleNodeClick(event, node) {
        if (node.type === 'blog_post') {
            const url = node.category ? `/b/${node.category}/${node.id}/` : `/b/${node.id}/`;
            window.open(url, '_blank');
        } else if (node.url) {
            window.open(node.url, '_blank');
        }
    }
    
    resetZoom() {
        this.svg.transition().duration(750).ease(d3.easeCubicInOut)
            .call(this.zoom.transform, d3.zoomIdentity);
    }
    
    fitGraphToView() {
        const nodes = this.simulation?.nodes() || [];
        if (!nodes.length) return;
        
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        
        nodes.forEach(node => {
            if (node.x !== undefined && node.y !== undefined) {
                const r = this.getNodeRadius(node) || 10;
                minX = Math.min(minX, node.x - r);
                maxX = Math.max(maxX, node.x + r);
                minY = Math.min(minY, node.y - r);
                maxY = Math.max(maxY, node.y + r);
            }
        });
        
        const padding = 100;
        minX -= padding; maxX += padding; minY -= padding; maxY += padding;
        
        const width = maxX - minX, height = maxY - minY;
        const scale = Math.max(0.25, Math.min(1.0, Math.min(this.width / width, this.height / height)));
        const translateX = this.width/2 - scale * (minX + maxX)/2;
        const translateY = this.height/2 - scale * (minY + maxY)/2;
        
        this.svg.transition().duration(2500).ease(d3.easeQuadInOut)
            .call(this.zoom.transform, d3.zoomIdentity.translate(translateX, translateY).scale(scale));
    }
    
    handleResize() {
        this.width = this.container.node().clientWidth;
        this.height = this.container.node().clientHeight;
        
        this.svg.attr("viewBox", [0, 0, this.width, this.height]);
        this.svg.select(".controls-info").attr("y", this.height - 10);
        
        if (this.simulation) {
            this.simulation.force("center", d3.forceCenter(this.width/2, this.height/2))
                .alpha(0.3).restart();
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    try {
        new HomepageKnowledgeGraph();
    } catch (error) {
        console.error('Failed to initialize knowledge graph:', error);
    }
});
