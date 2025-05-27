from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu
from PySide6.QtGui import QPainter, QColor, Qt
from collections import defaultdict, deque

from Neo4LDAP.gui.graph_generator.GG_node import GraphNode
from Neo4LDAP.gui.graph_generator.GG_edge import GraphEdge

class GraphView(QGraphicsView):
    COLUMN_WIDTH = 400
    NODE_VERTICAL_SPACING = 80

    def __init__(self):
        super().__init__()

        self._drag_active = False
        self._clicked_on_node = False
        self._last_mouse_pos = None
        self._ctrl_pressed = False

        self.nodes = {}
        self.edges = []

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.setStyleSheet("""
            QGraphicsView {
                border: none;
            }
            QScrollBar:vertical {
                background: #1b2831;
                width: 10px;
                margin: 2px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #4c566a;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                background: #1b2831;
                height: 10px;
                margin: 2px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #4c566a;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0;
            }
        """)

        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#3B4252"))
        self.scene.setBackgroundBrush(QColor("#3B4252"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def choose_node_color(self, node_type) -> str:
        color = ""
        if node_type == "User" :
            color = "#387478"
        elif node_type == "Group" :
            color = "#B8A349"
        elif node_type == "Computer" :
            color = "#9B4F4F"
        elif node_type == "OU" :
            color = "#A06A42"
        elif node_type == "GPO" :
            color = "#6F9EBF"
        elif node_type == "Domain" :
            color = "#50708A"
        elif node_type == "Container" :
            color = "#9D5C48"
        else:
            color = "#c21289"

        return color 

    # Node utilities
    def add_node(self, x, y, label, node_type, node_id, shadow_relationships) -> GraphNode:
        fill_color = self.choose_node_color(node_type)
        node = GraphNode(x, y, label, node_type, node_id, fill_color, shadow_relationships)
        self.scene.addItem(node)
        self.nodes[label] = node

        return node

    def get_node_parents(self, node) -> list:
        result = []
        for edge in node.edges:
            if edge.dst == node :
                result.append(edge.src)

        return result
    
    def get_node_childrens(self, node) -> list:
        result = []
        for edge in node.edges:
            if edge.src == node :
                result.append(edge.dst)

        return result
    
    # ---

    # Edge utilities
    def add_edge(self, src_label, dst_label, acl, offset=10, color=Qt.white) -> None:
        edge = GraphEdge(self.nodes[src_label], self.nodes[dst_label], offset, color, acl)
        self.scene.addItem(edge)
        self.scene.addItem(edge.arrow_head)
        self.edges.append(edge)

    def update_all_edges(self) -> None:
        for edge in self.edges:
            edge.update_edge_position()

    def update_edge_visibility(self) -> None:
        for edge in self.edges:
            show = edge.src.isVisible and edge.dst.isVisible() and not edge.src.subgraph_hidden
            
            edge.setVisible(show)
            edge.arrow_head.setVisible(show)
            edge.label.setVisible(show)

            if show :
                edge.update_edge_position()
    
    # ---
        
    # Visibility and layout utilities
    def collect_node_descendants(self, root_label) -> set:
        def dfs(node):
            if node not in reachable :
                reachable.add(node)
                for child_node in self.get_node_childrens(node):
                    dfs(child_node)

        reachable = set()

        root_node = self.nodes[root_label]
        dfs(root_node)

        return reachable

    def kahn_sort(self, edges, reachable_nodes=None) -> list:
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for edge in edges:
            source_node, target_node = edge.src, edge.dst
            if reachable_nodes and (source_node not in reachable_nodes or target_node not in reachable_nodes) :
                continue

            graph[source_node].append(target_node)
            in_degree[target_node] += 1
            if source_node not in in_degree :
                in_degree[source_node] = 0

        queue = deque()
        for node, degree in in_degree.items():
            if degree == 0 :
                queue.append(node)

        ordered = []

        while queue:
            node = queue.popleft()
            ordered.append(node)
            for child in graph[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0 :
                    queue.append(child)

        return ordered

    def toggle_subgraph(self, root_label, hide=True):
        root_node = self.nodes[root_label]
        root_node.subgraph_hidden = hide
        root_node.setVisible(True)
        root_node.update_visual_cue()

        reachable_nodes = self.collect_node_descendants(root_label)

        filtered_edges = []
        for edge in self.edges:
            if edge.src in reachable_nodes and edge.dst in reachable_nodes :
                filtered_edges.append(edge)
        
        ordered_nodes = self.kahn_sort(filtered_edges, reachable_nodes)
        
        # If any parent is visible, the node must be visible
        for node in ordered_nodes:
            if node == root_node :
                continue

            parents = self.get_node_parents(node)
            visible = False

            for parent in parents:
                if parent.isVisible() and not parent.subgraph_hidden :
                    visible = True
                    break

            node.setVisible(visible)
            node.subgraph_hidden = not visible
            node.update_visual_cue()

        self.update_edge_visibility()

    def calculate_dag_layout(self, root_label) -> None:
        visible_edges = []

        for edge in self.edges:
            if edge.src.isVisible() and edge.dst.isVisible() :
                visible_edges.append(edge)

        ordered_nodes = self.kahn_sort(visible_edges)

        # Layer assignation
        layer_map = defaultdict(int)
        layers = defaultdict(list)

        for node in ordered_nodes:
            if node.isVisible() :
                layer = layer_map[node]
                layers[layer].append(node)

                for child in self.get_node_childrens(node):
                    if child.isVisible() :
                        layer_map[child] = max(layer_map[child], layer + 1)

        # Layout nodes in each layer
        for depth in sorted(layers):
            layer_nodes = layers[depth]

            # Separate nodes with and without visible children
            with_children = []
            without_children = []

            for node in layer_nodes:
                has_child = False
                for child_node in self.get_node_childrens(node):
                    if child_node.isVisible() :
                        has_child = True
                        break

                if has_child :
                    with_children.append(node)
                else:
                    without_children.append(node)

            total_nodes = len(layer_nodes)
            center_start = (total_nodes - len(with_children)) // 2

            # The nodes with childrens must be as centered as possible
            top_without = without_children[:center_start]
            bottom_without = without_children[center_start:]
            all_ordered = top_without + with_children + bottom_without

            # Compute vertical position centered around y = 0
            total_height = total_nodes * self.NODE_VERTICAL_SPACING
            start_y = -total_height / 2

            for i, node in enumerate(all_ordered):
                node.setPos(depth * self.COLUMN_WIDTH, start_y + i * self.NODE_VERTICAL_SPACING)

        # If the root node is not processed, need to be setted
        root_node = self.nodes[root_label]
        if root_node not in layer_map :
            root_node.setPos(0, 0)

        self.update_all_edges()

    # ---

    # Input events
    def mouseMoveEvent(self, event):
        if self._drag_active and self._last_mouse_pos :
            current_pos = event.position().toPoint()
            delta = current_pos - self._last_mouse_pos
            self._last_mouse_pos = current_pos

            if not self._clicked_on_node :
                self.translate(delta.x(), delta.y())
        
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control :
            self._ctrl_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control :
            self._ctrl_pressed = False
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        item = self.scene.itemAt(scene_pos, self.transform())

        while item and not isinstance(item, GraphNode):
            item = item.parentItem()

        self._drag_active = False
        self._clicked_on_node = False
        self._last_mouse_pos = event.position().toPoint()

        if event.button() == Qt.LeftButton and self._ctrl_pressed :
            self.setDragMode(QGraphicsView.RubberBandDrag)
        elif event.button() == Qt.LeftButton :
            self.setDragMode(QGraphicsView.NoDrag)

            if isinstance(item, GraphNode) :
                self._clicked_on_node = True
            else:
                self._drag_active = True
                self.setCursor(Qt.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton :
            self._drag_active = False
            self._clicked_on_node = False
            self.setCursor(Qt.ArrowCursor)

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom = 0

        if event.angleDelta().y() > 0 :
            zoom = 1.25
        else:
            zoom =  1 / 1.25

        self.scale(zoom, zoom)

    # ---

    # View node to model
    def simple_topological_sort(self, node_labels):
        visited = set()
        sorted_nodes = []

        nodes = []
        for label in node_labels:
            nodes.append(self.nodes[label])

        def visit(node):
            if node not in visited :
                visited.add(node)

                for child in self.get_node_childrens(node):
                    visit(child)
                sorted_nodes.append(node)

        for node in nodes:
            visit(node)

        return reversed(sorted_nodes)

    def retrieve_selected_nodes(self) -> list:
        selected_nodes = []
        for node in self.scene.selectedItems():
            if isinstance(node, GraphNode):
                selected_nodes.append(node.label)

        return selected_nodes
    
    def show_context_menu(self, global_pos, selected_nodes) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2e3440;
                color: white;
                border: 1px solid #1b2831;
                padding: 5px;
            }
            QMenu::item:selected {
                background-color: #5b87a4;
            }
        """)
               
        hide_action = menu.addAction("Hide Nodes")
        show_action = menu.addAction("Show Nodes")
        menu.addSeparator()
        exclude_action = menu.addAction("Exclude Nodes")

        selected = menu.exec(global_pos)
        topological_selected_nodes = self.simple_topological_sort(selected_nodes)

        if selected == hide_action :
            for selected_node in topological_selected_nodes:
                for node in self.scene.selectedItems():
                    if node == selected_node :
                        node.toggle_action(hide=True)
            self.update_edge_visibility()
        elif selected == show_action :
            for selected_node in topological_selected_nodes:
                for node in self.scene.selectedItems():
                    if node == selected_node :
                        node.toggle_action(hide=False)
            self.update_edge_visibility()
        elif selected == exclude_action :
            excluded_nodes = []
            for selected_node in topological_selected_nodes:
                excluded_nodes.append(selected_node.label)

            from Neo4LDAP.controllers.N4L_Controller import N4LController

            controller = N4LController().get_instance()
            controller.repeat_request_with_exclusion(excluded_nodes)

    def contextMenuEvent(self, event) -> None:
        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, self.transform())

        if isinstance(item, GraphNode) :
            if not item.isSelected() :
                self.scene.clearSelection()
                item.setSelected(True)

        selected_nodes = self.retrieve_selected_nodes()

        if isinstance(item, GraphNode) and len(selected_nodes) == 1 :
            item.show_context_menu(event.globalPos())
        elif len(selected_nodes) > 1 :
            self.show_context_menu(event.globalPos(), selected_nodes)

    # ---

    def clear_graph(self) -> None:
        for edge in self.edges:
            if edge.scene() is self.scene:
                self.scene.removeItem(edge)
            if edge.arrow_head.scene() is self.scene:
                self.scene.removeItem(edge.arrow_head)
            if(edge.label.scene() is self.scene):
                self.scene.removeItem(edge.label)

        for node in self.nodes.values():
            if node.scene() is self.scene:
                self.scene.removeItem(node)
            if hasattr(node, "text") and node.text and node.text.scene() is self.scene:
                self.scene.removeItem(node.text)
            if hasattr(node, "count_text") and node.count_text and node.count_text.scene() is self.scene:
                self.scene.removeItem(node.count_text)

        self.nodes.clear()
        self.edges.clear() 

        self.scene.update() 

    def build_graph(self, graph, root_node, inbound_check) -> None:
        self.clear_graph()

        for node, data in graph.nodes(data=True):
            self.add_node(0, 0, node, data.get("node_type", ""), data.get("node_id", ""), data.get("shadow_relationships", 0))
        
        for source, target, data in graph.edges(data=True):
            self.add_edge(source, target, data.get("relationship", ""))

        if inbound_check :
            self.COLUMN_WIDTH = 700
        else:
            self.COLUMN_WIDTH = 400

        self.calculate_dag_layout(root_node) 