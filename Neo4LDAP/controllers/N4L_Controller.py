from PySide6.QtGui import QIcon, QFont, QPalette, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QThread, Signal, QEventLoop

from Neo4LDAP.model.N4L_Common import Neo4jConnector
from Neo4LDAP.gui.N4L_MainWindow import MainWindow

import sys
import os
import json

class ModelRequestWorker(QObject):
    task_started_signal = Signal()
    task_ended_signal = Signal()
    success_signal  = Signal(object)

    def __init__(self, thread, func, *args, **kwargs):
        super().__init__()
        self.thread = thread
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.task_started_signal.emit()
            result = self.func(*self.args, **self.kwargs)
            if(result != None and "traceback" in result.lower()):
                self.success_signal.emit(False)
            else:    
                self.success_signal.emit(True)
        except Exception:
            self.success_signal.emit(False)
        finally:
            self.task_ended_signal.emit()
            self.thread.quit()

class N4LController():
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None :
            cls._instance = super().__new__(cls)
        
        return cls._instance

    def __init__(self):
        if not self._initialized :
            self.app = QApplication(sys.argv)
            self.app.setFont(QFont("Segoe UI, Tahoma, Arial, sans-serif", 11))

            palette = QPalette()
            palette.setColor(QPalette.Highlight, QColor("#4c566a"))          
            palette.setColor(QPalette.HighlightedText, QColor("white"))

            self.app.setPalette(palette)

            icon_path = self.retrieve_resource_path("logo.png")
            self.app.setWindowIcon(QIcon(icon_path))

            self.custom_queries_list = []
            self.load_custom_queries()

            self.main_window = MainWindow(self.get_instance())
            self._initialized = True

    @classmethod
    def get_instance(cls) -> object:
        return cls._instance
    
    def run_in_new_thread(self, informational_popup, wait, task, *args, **kwargs) -> bool:
        return_value = None

        thread = QThread()
        worker = ModelRequestWorker(thread, task, *args, **kwargs)
        worker.moveToThread(thread)

        if informational_popup :
            from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
            popup = N4LMessageBox("Task in process", "This message will be closed once the task is completed, please be patient.", self.retrieve_main_window())

            worker.task_started_signal.connect(popup.show)
            worker.task_ended_signal.connect(popup.close)

        def cleanup() -> None:
            worker.deleteLater()
            thread.deleteLater()

        loop = QEventLoop()

        def store_return(value):
            nonlocal return_value
            return_value = value
            loop.quit()

        if(wait):
            worker.success_signal.connect(store_return)

        thread.finished.connect(cleanup)
        thread.started.connect(worker.run)
        thread.start()
        
        if(wait):
            loop.exec()

        return return_value
    
    # Login methods
    def login(self, username, password, bolt_uri) -> None:
        success = self.run_in_new_thread(True, True, Neo4jConnector.connect_to_neo4j, username, password, bolt_uri)
        if(success):
            self.main_window.init_gui_after_login()

    def init_gui(self) -> None:
        self.main_window.showMaximized()
        self.main_window.init_login(self.app)

    def init_gui_after_login(self) -> None:
        self.main_window.showMaximized()
        self.main_window.init_gui_after_login()

    # --- 

    # Path management and information
    def retrieve_neo4j_stats(self) -> list:
        return Neo4jConnector.retrieve_neo4j_stats()
    
    def retrieve_application_base_path(self) -> str:
        return os.path.dirname(os.path.abspath(__file__))
    
    def retrieve_resource_path(self, resource_name) -> str:
        return os.path.join(self.retrieve_application_base_path(), "..", "resources", resource_name)
    
    def retrieve_data_path(self, data_name) -> str:
        return os.path.join(self.retrieve_data_path_dir(), data_name)
    
    def retrieve_data_path_dir(self) -> str:
        return os.path.join(self.retrieve_application_base_path(), "..", "data")
    
    # ---
    
    # View switch
    def change_to_ACLView(self) -> None:
        self.main_window.change_to_ACLViewer_signal.emit()

    def change_to_LDAPView(self) -> None:
        self.main_window.change_to_LDAPViewer_signal.emit()

    # ---

    # Ingestor
    def ingest_data_to_neo4j(self, json_files, is_legacy) -> None:
        from Neo4LDAP.model.N4L_Parser import upload_data
        self.run_in_new_thread(False, False, upload_data, json_files, is_legacy)

    # LDAP View
    def request_LDAP_query(self, query_value, attribute_list, raw_query) -> None: 
        from Neo4LDAP.model.N4L_Cypher import perform_query
        self.run_in_new_thread(True, False, perform_query, query_value, attribute_list, raw_query)

    def redraw_LDAP_result_table(self, queryOutput) -> None:
        self.main_window.redraw_LDAP_result_table(queryOutput)

    # # Custom Queries
    def load_custom_queries(self) -> None:
        data_path = self.retrieve_data_path_dir()
        if os.path.exists(data_path) :
            custom_queries_json_path = self.retrieve_data_path("N4L_custom_queries.json")
            if os.path.exists(custom_queries_json_path) :
                with open(custom_queries_json_path, "r", encoding="utf-8") as custom_queries_file:
                    self.custom_queries_list = json.load(custom_queries_file)

    def save_custom_queries(self) -> None:
        data_path = self.retrieve_data_path_dir()
        if not os.path.exists(data_path) :
            os.mkdir(data_path)

        custom_queries_json_path = self.retrieve_data_path("N4L_custom_queries.json")
        with open(custom_queries_json_path, "w", encoding="utf-8") as custom_queries_file:
            json.dump(self.custom_queries_list, custom_queries_file, indent=4)

    def add_new_custom_query(self, index, name, description, query, attributes) -> None:
        if index == -1 :
            self.custom_queries_list.append({"name":name, "description":description, "query":query, "attributes":attributes})
        else:
            self.custom_queries_list[index] = {"name":name, "description":description, "query":query, "attributes":attributes}

        self.save_custom_queries()
        self.update_custom_queries_view()

    def update_custom_queries_view(self) -> None:
        self.main_window.update_custom_queries_view(self.custom_queries_list)

    def delete_custom_query(self, index) -> None:
        self.custom_queries_list.pop(index)
        self.save_custom_queries()
        self.update_custom_queries_view()

    # # --- 
    # ---

    # ACL View
    def request_ACL_query(self, name_value, acl_list, depth, source_value, target_value, exclusion_list, inbound_check) -> None:
        targeted_check = False
        if source_value != "" and target_value != "" :
            targeted_check = True
        
        from Neo4LDAP.model.N4L_ACLs import check_acls
        self.run_in_new_thread(True, False, check_acls, name_value, acl_list, depth, source_value, target_value, exclusion_list, inbound_check, targeted_check)

    def redraw_ACL_graph(self, graph, root_node, inbound_check) -> None:
        self.main_window.redraw_ACL_graph(graph, root_node, inbound_check)
    
    # ---

    # View node to model
    def request_LDAP_query_from_node(self, query_value, attribute_list, raw_query) -> None: 
        from Neo4LDAP.model.N4L_Cypher import perform_query
        self.change_to_LDAPView()
        self.main_window.add_query_to_panel(query_value)
        self.run_in_new_thread(True, False, perform_query, query_value, attribute_list, raw_query)

    def request_inbound_graph_from_node(self, root_node) -> None:
        from Neo4LDAP.model.N4L_ACLs import check_acls
        self.main_window.add_inbound_to_panel(root_node)
        self.run_in_new_thread(True, False, check_acls, root_node, ["all"], '', "", "", None, True)

    def request_outbound_graph_from_node(self, root_node) -> None:
        from Neo4LDAP.model.N4L_ACLs import check_acls
        self.main_window.add_outbound_to_panel(root_node)
        self.run_in_new_thread(True, False, check_acls, root_node, ["all"], '', "", "", None, False)

    def repeat_request_with_exclusion(self, excluded_node_list) -> None:
        from Neo4LDAP.model.N4L_ACLs import check_acls
        name_value, acl_list, depth_value, source_value, target_value, exclusion_list, inbound_check = self.main_window.repeat_request_with_exclusion(excluded_node_list)
        self.run_in_new_thread(True, False, check_acls, name_value, acl_list, depth_value, source_value, target_value, exclusion_list, inbound_check)
    
    def put_target(self, target) -> None:
        self.main_window.put_target(target)

    def put_source(self, source) -> None:
        self.main_window.put_source(source)

    # ---

    # Popups
    def retrieve_main_window(self) -> MainWindow:
        return self.main_window
    
    def notify_no_results(self, message) -> None:
        self.main_window.notify_no_results(message)

    def notify_error(self, message) -> None:
        self.main_window.notify_error(message)

    def push_debug_info(self, message) -> None:
        self.main_window.push_debug_info(message)

    def update_neo4j_db_stats(self) -> None:
        self.main_window.update_neo4j_db_stats(self.retrieve_neo4j_stats())

    def push_upload_debug_info(self, message) -> None:
        self.main_window.push_upload_debug_info(message)

    def clear_neo4j_db_data(self) -> None:
        Neo4jConnector.clear_neo4j_db_data()
        self.update_neo4j_db_stats()

    # ---