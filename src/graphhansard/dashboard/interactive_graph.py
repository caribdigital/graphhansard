"""Interactive graph component with click handlers for MP-5 and MP-6.

Extends PyVis visualization with JavaScript event handlers to capture
node and edge clicks, enabling MP profile display (MP-5) and mention
details display (MP-6).
"""

from __future__ import annotations

from pyvis.network import Network


def add_interaction_handlers(net: Network, session_id: str = "") -> str:
    """Add JavaScript event handlers for node/edge clicks to PyVis HTML.
    
    This function generates HTML with embedded JavaScript that:
    1. Captures node click events → displays MP profile (MP-5)
    2. Captures edge click events → displays mention details (MP-6)
    3. Enables drag-and-drop (already supported by PyVis physics)
    
    Args:
        net: PyVis Network object
        session_id: Session identifier for generating YouTube links
        
    Returns:
        HTML string with interactive event handlers
    """
    # Generate base PyVis HTML
    base_html = net.generate_html()
    
    # Custom JavaScript for click event handling
    interaction_script = """
    <script type="text/javascript">
    // Wait for network to be ready
    network.on("stabilized", function() {
        console.log("Network stabilized and ready for interaction");
    });
    
    // MP-5: Node click handler → Show MP profile
    network.on("click", function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeData = nodes.get(nodeId);
            
            // Post node click event to Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                key: 'graph_interaction',
                value: {
                    event_type: 'node_click',
                    node_id: nodeId,
                    node_data: nodeData
                }
            }, '*');
            
            console.log("Node clicked:", nodeId);
        }
        // MP-6: Edge click handler → Show mention details
        else if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            const edgeData = edges.get(edgeId);
            
            // Post edge click event to Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                key: 'graph_interaction',
                value: {
                    event_type: 'edge_click',
                    edge_id: edgeId,
                    edge_data: edgeData
                }
            }, '*');
            
            console.log("Edge clicked:", edgeId);
        }
    });
    
    // MP-11: Drag-and-drop is already enabled by PyVis physics configuration
    network.on("dragEnd", function(params) {
        if (params.nodes.length > 0) {
            console.log("Node repositioned:", params.nodes[0]);
        }
    });
    
    // Hover effects
    network.on("hoverNode", function(params) {
        network.canvas.body.container.style.cursor = 'pointer';
    });
    
    network.on("blurNode", function(params) {
        network.canvas.body.container.style.cursor = 'default';
    });
    
    network.on("hoverEdge", function(params) {
        network.canvas.body.container.style.cursor = 'pointer';
    });
    
    network.on("blurEdge", function(params) {
        network.canvas.body.container.style.cursor = 'default';
    });
    </script>
    """
    
    # Insert interaction script before closing body tag
    enhanced_html = base_html.replace('</body>', f'{interaction_script}</body>')
    
    return enhanced_html


def format_youtube_timestamp_link(
    video_url: str,
    timestamp_seconds: float,
    label: str | None = None,
) -> str:
    """Generate YouTube link with timestamp parameter.
    
    Args:
        video_url: Base YouTube video URL
        timestamp_seconds: Timestamp in seconds
        label: Optional display label (defaults to formatted timestamp)
        
    Returns:
        Markdown-formatted link with timestamp
    """
    # Convert seconds to YouTube timestamp format (integer seconds)
    timestamp_int = int(timestamp_seconds)
    
    # Add timestamp parameter to URL
    if '?' in video_url:
        timestamped_url = f"{video_url}&t={timestamp_int}"
    else:
        timestamped_url = f"{video_url}?t={timestamp_int}"
    
    # Format display label
    if label is None:
        minutes = timestamp_int // 60
        seconds = timestamp_int % 60
        label = f"{minutes}:{seconds:02d}"
    
    return f"[{label}]({timestamped_url})"


def format_sentiment_badge(sentiment_label: str | None) -> str:
    """Format sentiment as colored badge.
    
    Args:
        sentiment_label: "positive", "neutral", or "negative"
        
    Returns:
        Markdown badge with color
    """
    if sentiment_label == "positive":
        return "🟢 **Positive**"
    elif sentiment_label == "negative":
        return "🔴 **Negative**"
    else:
        return "⚫ **Neutral**"
