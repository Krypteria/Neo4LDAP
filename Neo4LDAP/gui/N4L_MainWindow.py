from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from Neo4LDAP.gui.N4L_LDAPViewer import LDAPViewerApp
from Neo4LDAP.gui.N4L_ACLViewer import ACLViewerApp
from Neo4LDAP.gui.N4L_Login import LoginWindow

import sys

class MainWindow(QMainWindow):
    change_to_ACLViewer_signal = Signal()
    change_to_LDAPViewer_signal = Signal()

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.stacked_widgets = QStackedWidget(self)

        self.login_handler = LoginWindow(self.controller)
        self.stacked_widgets.addWidget(self.login_handler)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.stacked_widgets)

        main_widget = QWidget(self)
        main_widget.setLayout(layout)

        self.setCentralWidget(main_widget)
        self.setWindowTitle("Neo4LDAP")

        self.stacked_widgets.setCurrentWidget(self.login_handler)
    
    # Login methods
    def init_login(self, app) -> None:
        self.stacked_widgets.setCurrentWidget(self.login_handler)
        self.stacked_widgets.showMaximized()
        sys.exit(app.exec())
    
    def init_gui_after_login(self) -> None:
        self.change_to_ACLViewer_signal.connect(self.change_to_ACLView)
        self.change_to_LDAPViewer_signal.connect(self.change_to_LDAPView)

        neo4j_stats = self.controller.retrieve_neo4j_stats()
        self.LDAPViewer_handler = LDAPViewerApp(self.controller, neo4j_stats)
        self.ACLViewer_handler = ACLViewerApp(self.controller, neo4j_stats)

        self.stacked_widgets.addWidget(self.ACLViewer_handler)
        self.stacked_widgets.addWidget(self.LDAPViewer_handler)

        self.controller.update_custom_queries_view()

        self.stacked_widgets.setCurrentWidget(self.LDAPViewer_handler)
        self.stacked_widgets.showMaximized()

    # ---

    # View switch
    def change_to_ACLView(self) -> None:
        self.stacked_widgets.setCurrentWidget(self.ACLViewer_handler)

    def change_to_LDAPView(self) -> None:
        self.stacked_widgets.setCurrentWidget(self.LDAPViewer_handler)

    # ---

    def update_neo4j_db_stats(self, neo4j_stats) -> None:
        self.LDAPViewer_handler.update_neo4j_db_stats_signal.emit(neo4j_stats)

    # LDAP View
    def update_custom_queries_view(self, custom_queries_list) -> None:
        self.LDAPViewer_handler.update_custom_queries_signal.emit(custom_queries_list)

    def redraw_LDAP_result_table(self, queryOutput) -> None:
        self.LDAPViewer_handler.refresh_signal.emit(queryOutput)

    def add_query_to_panel(self, query) -> None:
        self.LDAPViewer_handler.add_query_signal.emit(query)

    # ---

    # ACL View
    def redraw_ACL_graph(self, graph, root_node, inbound_check) -> None:
        self.ACLViewer_handler.refresh_graph_signal.emit(graph, root_node, inbound_check)

    # --- 

    # View node to model
    def add_inbound_to_panel(self, root_node) -> None:
        self.ACLViewer_handler.add_inbound_signal.emit(root_node)

    def add_outbound_to_panel(self, root_node) -> None:
        self.ACLViewer_handler.add_outbound_signal.emit(root_node)

    def repeat_request_with_exclusion(self, excluded_node_list) -> list:
        return self.ACLViewer_handler.repeat_request_with_exclusion(excluded_node_list)
    
    def put_target(self, target) -> None:
        self.ACLViewer_handler.put_target_signal.emit(target)

    def put_source(self, source) -> None:
        self.ACLViewer_handler.put_source_signal.emit(source)
    
    # ---

    # Popups
    def notify_no_results(self, message) -> None:
        self.stacked_widgets.currentWidget().no_result_signal.emit(self, message)

    def notify_error(self, message) -> None:
        self.stacked_widgets.currentWidget().error_signal.emit(self, message)

    def push_upload_debug_info(self, message) -> None:
        self.LDAPViewer_handler.push_upload_debug_info_signal.emit(message)
        
    def push_debug_info(self, message) -> None:
        self.stacked_widgets.currentWidget().debug_signal.emit(message)
    # --- 
