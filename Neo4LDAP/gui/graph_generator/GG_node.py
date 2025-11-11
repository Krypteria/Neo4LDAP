from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem, QMenu, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtCore import Qt

class GraphNode(QGraphicsEllipseItem):
    def __init__(self, x, y, label, node_type, node_id, color, shadow_relationships = 0, shadow_relationships_list = [], radius=20):
        super().__init__(-radius, -radius, radius * 2, radius * 2)

        self.radius = radius
        self.node_id = node_id
        self.label = label

        self.edges = []
        self.subgraph_hidden = False

        self.set_hidden_count(shadow_relationships)

        self.shadow_relationships_list = shadow_relationships_list
        self.availaible_shadow_relationships = False
        if(self.shadow_relationships_list != []):
            self.availaible_shadow_relationships = True

        self.default_color = QColor(color)
        self.collapsed_color = QColor("#6A5473")


        self.setBrush(QBrush(self.default_color))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)

        if node_type == "OU" :
            self.node_type = "OrganizationalUnit"
        elif node_type == "GPO" :
            self.node_type = "GroupPolicyContainer"
        else:
            self.node_type = node_type

        self.setPos(x, y)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.AllButtons)

        self.text = QGraphicsTextItem(label, self)
        self.text.setDefaultTextColor(Qt.white)
        self.text.setPos(-self.text.boundingRect().width() / 2, radius + 4)

        self.setZValue(2)
        self.text.setZValue(3)

    def set_hidden_count(self, count: int) -> None:
        if hasattr(self, 'count_text') and self.count_text :
            self.scene().removeItem(self.count_text)
            self.count_text = None

        if count <= 0 :
            return

        self.count_text = QGraphicsTextItem(str(count), self)
        self.count_text.setDefaultTextColor(Qt.white)
        self.count_text.setFont(QFont("Segoe UI, Tahoma, Arial, sans-serif", 8, QFont.Bold))

        offset_x = self.radius * 0.5
        offset_y = self.radius * 0.5

        self.count_text.setPos(offset_x, offset_y)
        self.count_text.setZValue(4)

    def add_edge(self, edge) -> None:
        self.edges.append(edge)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)

        scene = self.scene()
        if not scene:
            return
        
        selected_nodes = []
        for item in self.scene().selectedItems():
            if isinstance(item, GraphNode) and item.scene() is not None:
                selected_nodes.append(item)

        for node in selected_nodes:
            for edge in node.edges:
                edge.update_edge_position()

    def update_visual_cue(self) -> None:
        color = ""
        if self.subgraph_hidden :
            color = self.collapsed_color
        else:
            color = self.default_color
            
        self.setBrush(QBrush(color))

    def toggle_action(self, hide) -> None:
        self.update_visual_cue()
        self.scene().views()[0].toggle_subgraph(self.label, hide=hide)

    def show_context_menu(self, global_pos) -> None:
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
        
        details_action = menu.addAction("Show details")

        shadow_relationships_action = ""
        if(self.availaible_shadow_relationships):
            shadow_relationships_action = menu.addAction("Show shadow relationships")

        menu.addSeparator()

        toggle_action = ""
        if self.subgraph_hidden :
            toggle_action = menu.addAction("Show")
        else:
            toggle_action = menu.addAction("Hide")

        menu.addSeparator()
        inbound_action = menu.addAction("Inbound ACLs")
        outbound_action = menu.addAction("Outbound ACLs")
        menu.addSeparator()
        source_action = menu.addAction("Add as Source")
        target_action = menu.addAction("Add as Target")
        menu.addSeparator()
        exclusion_action = menu.addAction("Exclude")

        selected = menu.exec(global_pos)

        from Neo4LDAP.controllers.N4L_Controller import N4LController
        controller = N4LController().get_instance()
        
        if selected == toggle_action :
            self.toggle_action(not self.subgraph_hidden)
        elif selected == details_action :
            query = "(&(objectClass={node_type})(objectid={node_id}))".format(node_type = self.node_type, node_id = self.node_id)

            controller.request_LDAP_query_from_node(query, None, False)
        elif selected == shadow_relationships_action:
            controller.show_shadow_relationships(self.label, self.shadow_relationships_list)
        elif selected == inbound_action :
            controller.request_inbound_graph_from_node(self.label)
        elif selected == outbound_action :
            controller.request_outbound_graph_from_node(self.label)
        elif selected == exclusion_action :
            controller.repeat_request_with_exclusion([self.label])
        elif selected == target_action :
            controller.put_target(self.label)
        elif selected == source_action :
            controller.put_source(self.label)

        