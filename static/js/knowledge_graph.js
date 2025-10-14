class HomepageKnowledgeGraph {
    constructor() {
        this.initConfig();
        this.initDOM();
        this.initVisualization();
        this.bindEvents();
        this.loadData();
    }
    
    initConfig() {
        this.CONFIG = {
            dimensions: { width: 800, height: 500 },
            tooltip: { padding: 20, maxWidth: 380, offset: 20, animDuration: 250 },
            node: { 
                blogPostRadius: 20,  // Fixed size for all blog post nodes
                baseRadius: 10        // Default radius fallback
            },
            label: { maxLength: 26, shortLength: 18 },
            animation: { rippleDuration: 1000, rippleRadius: 50, resizeDebounce: 150 },
            force: {
                linkDistance: 280,       // Balanced distance for natural hull formation
                chargeStrength: -100,    // Moderate repulsion for natural spacing with spring-back
                collisionRadius: 40,     // Moderate minimum space between nodes
                centerStrength: 0.01,    // Slight pull toward center for stability
                categoryStrength: 0.25,  // Stronger pull toward category centers for spring-back
                basePadding: 50,         // Reduced base hull padding to better fit nodes
                paddingPerNode: 8,       // Reduced additional padding per node
                labelRepulsion: 60,      // More space for labels
                labelRadius: 180         // Larger detection radius
            }
        };
        
        // Read category colors from CSS custom properties (single source of truth)
        this.COLORS = {
            blogPost: '#888', highlight: '#fff',
            categories: this.getCategoryColorsFromCSS()
        };
    }
    
    getCategoryColorsFromCSS() {
        const root = getComputedStyle(document.documentElement);
        const categories = ['tech', 'personal', 'projects', 'guides', 'smart_home', 'reviews', 'default'];
        const colors = {};
        
        categories.forEach(category => {
            colors[category] = {
                node: root.getPropertyValue(`--category-${category}-node`).trim(),
                hull: root.getPropertyValue(`--category-${category}-hull`).trim(),
                border: root.getPropertyValue(`--category-${category}-border`).trim(),
                text: root.getPropertyValue(`--category-${category}-text`).trim()
            };
        });
        
        return colors;
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
        this.svg.attr("viewBox", [0, 0, this.width, this.height])
            .attr("width", this.width).attr("height", this.height);
        
        this.zoom = d3.zoom().scaleExtent([0.1, 3])
            .on("zoom", e => this.g.attr("transform", e.transform));
        this.svg.call(this.zoom);
        
        this.g = this.svg.append("g");
        
        // Start zoomed out to show entire graph (20% scale)
        const initScale = 0.2;
        this.svg.call(this.zoom.transform, d3.zoomIdentity
            .translate(this.width/2*(1-initScale), this.height/2*(1-initScale))
            .scale(initScale));
        
        this.tooltipGroup = this.svg.append("g").attr("class", "svg-tooltip");
    }

    bindEvents() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.handleResize(), this.CONFIG.animation.resizeDebounce);
        });
        
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
            }
        } catch (error) {
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
        
        // Layer order: hulls < links < nodes < labels < category labels
        this.hullGroup = this.g.append("g").attr("class", "hulls");
        this.createLinks(edges);
        this.createNodes(nodes);
        this.createLabels(nodes);
        this.categoryLabelGroup = this.g.append("g").attr("class", "category-labels");
        
        this.addNodeInteractions();
        
        this.simulation.alpha(1.0).alphaDecay(0.01).velocityDecay(0.5).restart();
        this.updateCategoryHulls();
        setTimeout(() => this.updateCategoryHulls(), 500);
        setTimeout(() => this.updateCategoryHulls(), 1500);
    }
    
    initializeNodePositions(nodes) {
        const centerX = this.width / 2, centerY = this.height / 2;
        const categoryGroups = {};
        
        nodes.forEach(node => {
            const cat = node.category || 'uncategorized';
            (categoryGroups[cat] = categoryGroups[cat] || []).push(node);
        });
        
        this.categoryCenters = {};
        const categories = Object.keys(categoryGroups);
        // Distribute categories evenly around a circle
        const angleStep = (2 * Math.PI) / Math.max(categories.length, 1);
        const groupRadius = Math.min(this.width, this.height) * 0.4;   // Further increased to 40% of viewport
        
        categories.forEach((cat, i) => {
            const angle = i * angleStep;
            const cx = centerX + groupRadius * Math.cos(angle);
            const cy = centerY + groupRadius * Math.sin(angle);
            this.categoryCenters[cat] = { x: cx, y: cy };
            
            this.positionCategoryNodes(categoryGroups[cat], cx, cy);
        });
    }
    
    positionCategoryNodes(nodes, cx, cy) {
        const count = nodes.length;
        if (count === 1) {
            nodes[0].x = cx;
            nodes[0].y = cy;
        } else {
            // Concentric ring placement: center node, then 6 per ring expanding outward
            const maxRadius = 150;  // Further increased to spread nodes even more
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
                // Same-category links pulled closer (0.8x)
                if (d.source.category === d.target.category) return this.CONFIG.force.linkDistance * 0.8;
                return this.CONFIG.force.linkDistance;
            }).strength(0);
        
        const chargeForce = d3.forceManyBody()
            .strength(d => this.CONFIG.force.chargeStrength * 0.05);
        
        const collisionForce = d3.forceCollide()
            .radius(d => this.CONFIG.force.collisionRadius * 0.8)
            .strength(0.2);
        
        this.simulation = d3.forceSimulation(nodes)
            .force("link", linkForce)
            .force("charge", chargeForce)
            .force("collision", collisionForce)
            .force("categoryX", d3.forceX(d => this.getTargetX(d)).strength(0.02))
            .force("categoryY", d3.forceY(d => this.getTargetY(d)).strength(0.02))
            .alphaMin(0.001)  // Lower threshold for simulation to stop completely
            .alphaDecay(0.02); // Slower decay for smoother settling
        
        this.forces = { link: linkForce, charge: chargeForce, collision: collisionForce };
        
        let tickCount = 0;
        let hasUpdatedOnStable = false;
        let lastHullUpdate = 0;
        this.simulation.on("tick", () => {
            const alpha = this.simulation.alpha();
            this.updateForceStrengths(alpha);
            this.updatePositions();
            
            // Only update hulls when simulation is actively moving
            // Stop updating hulls when alpha drops below threshold for stability
            if (alpha > 0.05) {
                if (tickCount < 10 || tickCount % 3 === 0) {
                    requestAnimationFrame(() => this.updateCategoryHulls());
                    lastHullUpdate = tickCount;
                }
            } else if (tickCount - lastHullUpdate > 10 && !hasUpdatedOnStable) {
                // One final hull update when simulation has settled
                hasUpdatedOnStable = true;
                requestAnimationFrame(() => this.updateCategoryHulls());
            }
            tickCount++;
            
            if (!this.hasAutoFitted && alpha < 0.4) {
                this.hasAutoFitted = true;
                setTimeout(() => this.fitGraphToView(), 500);
            }
        });
    }
    
    getTargetX(d) {
        return this.categoryCenters[d.category || 'uncategorized']?.x || this.width/2;
    }
    
    getTargetY(d) {
        return this.categoryCenters[d.category || 'uncategorized']?.y || this.height/2;
    }
    
    updateForceStrengths(alpha) {
        if (!this.forces) return;
        
        const progress = 1 - alpha;
        // Smoother easing curve to prevent instability
        const ease = progress < 0.5 ? 2 * progress * progress : 
                     1 - 2 * (1 - progress) * (1 - progress);
        
        // Balanced link forces for natural spreading with spring-back
        this.forces.link.strength(d => {
            const base = d.source.category === d.target.category ? 0.4 : 0.2;
            return base * ease * 0.3;
        });
        
        // Dramatically reduce charge at low alpha to eliminate jittering
        this.forces.charge.strength(d => {
            if (alpha < 0.1) {
                // At rest, use minimal charge to prevent jittering
                return this.CONFIG.force.chargeStrength * 0.1 * ease;
            }
            const base = this.CONFIG.force.chargeStrength * 0.6;
            return base * Math.min(1, ease * 0.9);
        });
        
        this.forces.collision.radius(d => {
            const base = this.CONFIG.force.collisionRadius;
            return base * (0.85 + 0.15 * ease);
        }).strength(alpha < 0.1 ? 0.05 : 0.15 + 0.25 * ease);  // Reduce collision strength at rest
        
        // Stronger category forces for spring-back behavior
        const catStrength = d => 0.01 + (this.CONFIG.force.categoryStrength * 0.6) * ease;
        this.simulation.force("categoryX").strength(catStrength);
        this.simulation.force("categoryY").strength(catStrength);
        
        // Higher velocity decay at rest to dampen movement quickly
        this.simulation.velocityDecay(alpha < 0.1 ? 0.85 : 0.65 - 0.15 * ease);
    }
    
    createLinks(edges) {
        this.link = this.g.append("g").attr("class", "links")
            .selectAll("line").data(edges).enter().append("line")
            .attr("class", "link internal")
            .attr("stroke", this.COLORS.blogPost)
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", 2);
    }
    
    createNodes(nodes) {
        this.node = this.g.append("g").attr("class", "nodes")
            .selectAll("circle").data(nodes).enter().append("circle")
            .attr("class", d => `node blog-post ${d.category || 'uncategorized'}`)
            .attr("r", d => this.getNodeRadius(d))
            .attr("fill", d => {
                const cat = d.category || 'default';
                return (this.COLORS.categories[cat] || this.COLORS.categories.default).node;
            })
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .call(this.createDragBehavior());
    }
    
    createLabels(nodes) {
        this.labels = this.g.append("g").attr("class", "node-labels-group")
            .selectAll("text").data(nodes).enter().append("text")
            .attr("class", "node-label blog-post-number")
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
        
        return {x, y: y + 4};
    }
    
    updateCategoryHulls() {
        if (!this.hullGroup) return;
        
        const categoryGroups = {};
        const nodes = this.simulation?.nodes() || [];
        
        nodes.forEach(node => {
            if (node.category && 
                node.x !== undefined && node.y !== undefined && 
                !isNaN(node.x) && !isNaN(node.y) &&
                isFinite(node.x) && isFinite(node.y)) {
                (categoryGroups[node.category] = categoryGroups[node.category] || []).push([node.x, node.y]);
            }
        });
        
        this.hullGroup.selectAll("*").remove();
        this.categoryLabelGroup?.selectAll("*").remove();
        this.categoryLabelBounds = [];
        
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
        if (!isFinite(x) || !isFinite(y)) return;
        
        this.hullGroup.append("circle")
            .attr("class", `category-hull hull-${category}`)
            .attr("cx", x).attr("cy", y).attr("r", padding)
            .style("fill", color.hull).style("stroke", color.border);
        
        const labelY = y - padding + 25;
        this.addCategoryLabel(x, labelY, category, color);
    }
    
    drawTwoNodeHull(points, category, color, padding) {
        const [[x1, y1], [x2, y2]] = points;
        if (!isFinite(x1) || !isFinite(y1) || !isFinite(x2) || !isFinite(y2)) return;
        
        const midX = (x1 + x2) / 2, midY = (y1 + y2) / 2;
        const dist = Math.hypot(x2 - x1, y2 - y1);
        const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        
        this.hullGroup.append("ellipse")
            .attr("class", `category-hull hull-${category}`)
            .attr("cx", midX).attr("cy", midY)
            .attr("rx", dist/2 + padding).attr("ry", padding)
            .attr("transform", `rotate(${angle} ${midX} ${midY})`)
            .style("fill", color.hull).style("stroke", color.border);
        
        const topY = Math.min(y1, y2);
        const labelY = topY - padding + 25;
        this.addCategoryLabel(midX, labelY, category, color);
    }
    
    drawMultiNodeHull(points, category, color, padding) {
        // Validate all points before processing
        const validPoints = points.filter(([x, y]) => isFinite(x) && isFinite(y));
        if (validPoints.length < 3) return;
        
        const hull = d3.polygonHull(validPoints);
        if (!hull) return;
        
        const expanded = this.expandHull(hull, padding);
        const path = d3.line().x(d => d[0]).y(d => d[1]).curve(d3.curveCatmullRomClosed.alpha(0.7))(expanded);
        
        this.hullGroup.append("path")
            .attr("class", `category-hull hull-${category}`)
            .attr("d", path)
            .style("fill", color.hull).style("stroke", color.border);
        
        const centroid = d3.polygonCentroid(validPoints);
        const topY = Math.min(...validPoints.map(p => p[1]));
        const labelY = topY - padding + 25;
        this.addCategoryLabel(centroid[0], labelY, category, color);
    }
    
    expandHull(hull, padding) {
        const centroid = d3.polygonCentroid(hull);
        if (!isFinite(centroid[0]) || !isFinite(centroid[1])) return hull;
        
        return hull.map(point => {
            const dx = point[0] - centroid[0], dy = point[1] - centroid[1];
            const dist = Math.hypot(dx, dy);
            if (dist === 0) return point;
            // Add 10% random variation to hull padding for organic appearance
            const scale = (dist + padding * (1 + (Math.random() - 0.5) * 0.1)) / dist;
            return [centroid[0] + dx * scale, centroid[1] + dy * scale];
        });
    }
    
    addCategoryLabel(x, y, category, color) {
        if (!this.categoryLabelGroup) return;
        if (!isFinite(x) || !isFinite(y)) return;
        
        const textWidth = category.length * 12 + 20;
        const textHeight = 24;
        
        const labelGroup = this.categoryLabelGroup.append("g")
            .attr("class", "category-label-group");
        
        labelGroup.append("rect")
            .attr("x", x - textWidth/2)
            .attr("y", y - textHeight/2)
            .attr("width", textWidth)
            .attr("height", textHeight)
            .attr("rx", 4)
            .attr("ry", 4)
            .style("fill", "rgba(0, 0, 0, 0.5)")
            .style("stroke", "rgba(255, 255, 255, 0.3)")
            .style("stroke-width", 1);
        
        labelGroup.append("text")
            .attr("class", "category-label")
            .attr("x", x)
            .attr("y", y)
            .text(category.toUpperCase());
        
        this.categoryLabelBounds.push({x: x, y: y, width: textWidth, height: textHeight, category});
    }
    
    getNodeRadius(node) {
        return this.CONFIG.node.blogPostRadius;
    }
    
    getNodeLabel(node) {
        // Extract any leading numeric identifier from blog post ID
        const numericMatch = node.id.match(/^(\d+)/);
        if (numericMatch) {
            return numericMatch[1];
        }
        // Fallback: if no leading digits, return empty string to show just the node circle
        return '';
    }
    
    createDragBehavior() {
        return d3.drag()
            .on("start", (e, d) => { 
                if (!e.active) this.simulation.alphaTarget(0.5).restart(); 
                d.fx = d.x; 
                d.fy = d.y; 
            })
            .on("drag", (e, d) => { 
                d.fx = e.x; 
                d.fy = e.y; 
            })
            .on("end", (e, d) => { 
                if (!e.active) this.simulation.alphaTarget(0.1).restart();
                d.fx = null; 
                d.fy = null;
                // Let simulation continue briefly for spring-back effect
                setTimeout(() => {
                    if (this.simulation.alpha() < 0.15) {
                        this.simulation.alphaTarget(0);
                    }
                }, 300);
            });
    }
    
    showTooltip(event, node) {
        this.tooltipGroup.selectAll("*").remove();
        
        // Clean up blog post filename to readable title:
        // Remove year prefix, replace underscores with spaces, remove .html extension
        // Preserve original casing of the filename
        let label = node.label.replace(/^\d{1,4}[_\-\s]*/, '').replace(/_/g, ' ').replace(/\.html?$/i, '').trim();
        
        // Increased padding for better spacing around text
        const paddingX = 16, paddingY = 8;
        const width = Math.min(250, Math.max(label.length * 7 + paddingX * 2, 80));
        const height = 32;
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
        const url = node.category ? `/b/${node.category}/${node.id}/` : `/b/${node.id}/`;
        window.open(url, '_blank');
    }
    
    resetZoom() {
        this.svg.transition().duration(750).ease(d3.easeCubicInOut)
            .call(this.zoom.transform, d3.zoomIdentity);
    }
    
    fitGraphToView() {
        const nodes = this.simulation?.nodes() || [];
        if (!nodes.length) return;
        
        // Calculate bounding box of all nodes including their radii
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
        // Calculate scale to fit graph in viewport (min 25%, max 100%)
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
        // Control info text removed
        // this.svg.select(".controls-info").attr("y", this.height - 10);
        
        if (this.simulation) {
            this.simulation.force("center", d3.forceCenter(this.width/2, this.height/2))
                .alpha(0.3).restart();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        new HomepageKnowledgeGraph();
    } catch (error) {
    }
});
