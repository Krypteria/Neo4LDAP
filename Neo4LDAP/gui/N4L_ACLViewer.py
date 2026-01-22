from Neo4LDAP.gui.N4L_CommonViewer import *
from Neo4LDAP.gui.graph_generator.GG_view import GraphView

class ACLViewerApp(ViewerApp):
    add_inbound_signal = Signal(str)
    add_outbound_signal = Signal(str)
    put_target_signal = Signal(str)
    put_source_signal = Signal(str)

    def __init__(self, controller, neo4j_stats):
        super().__init__(controller)

        self.add_inbound_signal.connect(self.add_inbound_text)
        self.add_outbound_signal.connect(self.add_outbound_text)
        self.put_target_signal.connect(self.put_target)
        self.put_source_signal.connect(self.put_source)

        self.neo4j_stats = neo4j_stats

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Panel
        self.left_panel = self.initialize_left_panel()

        # Right Panel
        self.right_panel = self.initialize_right_panel()

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([400, 1200])
        splitter.setHandleWidth(0)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def initialize_left_panel(self) -> QWidget:
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: {color}".format(color = self.PANELS_BG))

        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: {color}; border: none;".format(color = self.PANELS_BG))

        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop)

        switch_buttons_layout = self.create_switch_buttons_layout()

        search_title = self.create_label("SEARCH", False, self.TITLE_STYLE)
        targeted_search_title = self.create_label("TARGETED SEARCH", False, self.TITLE_STYLE)
        exclusion_title = self.create_label("EXCLUSION LIST", False, self.TITLE_STYLE)

        search_title.setAlignment(Qt.AlignCenter)
        targeted_search_title.setAlignment(Qt.AlignCenter)
        exclusion_title.setAlignment(Qt.AlignCenter)

        search_frame = self.init_search_panel()
        targeted_search_frame = self.init_targeted_search_panel()
        exclusion_frame = self.init_exclusion_panel()

        search_button = self.create_button("Search", self.on_search_button_clicked)

        self.name_input.textChanged.connect(self.basic_search_changed)
        self.acl_input.textChanged.connect(self.basic_search_changed)
        self.depth_input.textChanged.connect(self.basic_search_changed)
        self.inbound_check.stateChanged.connect(self.basic_search_changed)

        self.source_input.textChanged.connect(self.targeted_search_changed)
        self.target_input.textChanged.connect(self.targeted_search_changed)

        #Scrollable content
        scroll_layout.addWidget(search_title)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(search_frame)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(targeted_search_title)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(targeted_search_frame)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(exclusion_title)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(exclusion_frame)
        scroll_layout.addSpacing(10)
        scroll_layout.addWidget(search_button)

        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(self.QSCROLLBAR_STYLE)
        scroll_area.setWidgetResizable(True)  
        scroll_area.setWidget(scroll_content)     
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        # Left Panel
        left_layout.addLayout(switch_buttons_layout)
        left_layout.addSpacing(10)
        left_layout.addWidget(scroll_area)

        return left_panel

    def initialize_right_panel(self) -> QWidget:
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: {color}".format(color = self.PANELS_BG))

        graph_layout = QVBoxLayout(right_panel)
        graph_layout.setContentsMargins(10, 10, 10, 10)

        self.graph_viewer = GraphView()

        graph_frame = QFrame()
        graph_frame.setStyleSheet("background-color: {background}; border: {border}".format(background = self.PANELS_BG, border = self.PANELS_BD))        

        graph_layout_aux = QVBoxLayout(graph_frame)
        graph_layout_aux.setContentsMargins(2, 2, 2, 2)
        graph_layout_aux.addWidget(self.graph_viewer)
       
        self.weight_modify_button_style = """
            QPushButton {{
                background-color: {background};
                padding: 8px;
                color: {text};
                border-radius: 6px;
                font-weight: bold;
                border: 1px solid {border};

            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {background};
            }}
        """.format(background=self.BUTTON_BG, hover=self.BUTTON_HOVER, text=self.TEXT_COLOR, border=self.PANELS_BD)
        

        self.weight_modify_button = self.create_button("Weights", self.show_weights_popup, self.weight_modify_button_style)
        self.weight_modify_button.setFixedSize(74, 40)

        self.weight_modify_button.setParent(graph_frame)
        self.weight_modify_button.raise_()
        self.weight_modify_button.move(graph_frame.width() - 94, 10)

        def weights_button_resize(event):
            self.weight_modify_button.move(graph_frame.width() - 94, 10)
            event.accept()
        
        graph_frame.resizeEvent = weights_button_resize
        graph_layout.addWidget(graph_frame)

        return right_panel


    def init_search_panel(self) -> QFrame:
        search_frame = QFrame()
        search_frame.setStyleSheet(self.QFRAME_STYLE)

        name_label = self.create_label("User Principal Name / DNS Name", True)
        acl_label = self.create_label("ACE Type", True)

        self.acl_input = self.create_text_field()
        self.name_input = self.create_text_field()

        acl_help_button = self.create_button("[?]", self.show_acl_help_popup, self.HELP_BUTTON_STYLE)

        acl_type_layout = QHBoxLayout()
        acl_type_layout.addWidget(acl_label)
        acl_type_layout.addWidget(acl_help_button)

        depth_label = self.create_label("Depth", True)
        self.depth_input = self.create_text_field()

        checkbox_container = QWidget()
        checkbox_container.setStyleSheet("border: none;")

        checkbox_layout = QHBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(0, 0, 0, 6)
        checkbox_layout.setSpacing(0)

        self.inbound_check = QCheckBox("Inbound")
        self.inbound_check.setStyleSheet(self.CHECKBOX_STYLE)

        checkbox_layout.addWidget(self.inbound_check)

        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(20, 20, 20, 20)
        search_layout.setSpacing(7)

        # First Row
        search_layout.addWidget(name_label)
        search_layout.addWidget(self.name_input)
        search_layout.addSpacing(7)
        
        # Second Row
        search_layout.addLayout(acl_type_layout)
        search_layout.addWidget(self.acl_input)
        search_layout.addSpacing(7)

        # Third Row
        search_layout.addWidget(depth_label)
        search_layout.addWidget(self.depth_input)

        search_layout.addSpacing(7)
        search_layout.addWidget(checkbox_container)

        return search_frame

    def init_targeted_search_panel(self) -> QFrame:
        targeted_search_frame = QFrame()
        targeted_search_frame.setStyleSheet(self.QFRAME_STYLE)
        
        source_label = self.create_label("Source User Principal Name / DNS Name", True)
        target_label = self.create_label("Target User Principal Name / DNS Name", True)
        
        self.source_input = self.create_text_field()
        self.target_input = self.create_text_field()
        
        targeted_search_layout = QVBoxLayout(targeted_search_frame)
        targeted_search_layout.setContentsMargins(20, 20, 20, 20)
        targeted_search_layout.setSpacing(7)

        targeted_search_layout.addWidget(source_label)
        targeted_search_layout.addWidget(self.source_input)
        targeted_search_layout.addSpacing(10)
        targeted_search_layout.addWidget(target_label)
        targeted_search_layout.addWidget(self.target_input)

        return targeted_search_frame

    def init_exclusion_panel(self) -> QFrame:
        exclusion_frame = QFrame()
        exclusion_frame.setStyleSheet(self.QFRAME_STYLE)

        nodes_label = self.create_label("Nodes", True)
        nodes_help_button = self.create_button("[?]", self.show_exclusion_help_popup, self.HELP_BUTTON_STYLE)
        self.nodes_input = self.create_text_field()
        
        nodes_help_layout = QHBoxLayout()
        nodes_help_layout.addWidget(nodes_label)
        nodes_help_layout.addWidget(nodes_help_button)

        exclusion_layout = QVBoxLayout(exclusion_frame)

        exclusion_layout.addLayout(nodes_help_layout)
        exclusion_layout.addWidget(self.nodes_input)
        exclusion_layout.setContentsMargins(20, 20, 20, 20)
        exclusion_layout.setSpacing(7)

        return exclusion_frame
    
    # Utility methods
    def redraw_gui(self, graph, root_node, inbound_check) -> None:
        self.graph_viewer.build_graph(graph, root_node, inbound_check)

    def basic_search_changed(self) -> None:
        has_text = bool(self.name_input.text().strip()) or bool(self.acl_input.text().strip()) or bool(self.depth_input.text().strip())
        
        if self.inbound_check.isChecked() :
            self.source_input.setReadOnly(True)
            self.target_input.setReadOnly(True)
            self.depth_input.setReadOnly(True)

            self.source_input.clear()
            self.target_input.clear()
            self.depth_input.clear()

            self.source_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
            self.target_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
            self.depth_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
        else:
            self.source_input.setReadOnly(False)
            self.target_input.setReadOnly(False)
            self.acl_input.setReadOnly(False)
            self.depth_input.setReadOnly(False)
            
            self.source_input.setStyleSheet(self.INPUT_STYLE)
            self.target_input.setStyleSheet(self.INPUT_STYLE)
            self.acl_input.setStyleSheet(self.INPUT_STYLE)
            self.depth_input.setStyleSheet(self.INPUT_STYLE)


        if has_text :
            self.source_input.setReadOnly(True)
            self.target_input.setReadOnly(True)

            self.source_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
            self.target_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
        elif not self.inbound_check.isChecked() :
            self.source_input.setReadOnly(False)
            self.target_input.setReadOnly(False)

            self.source_input.setStyleSheet(self.INPUT_STYLE)
            self.target_input.setStyleSheet(self.INPUT_STYLE)

    def targeted_search_changed(self) -> None:
        has_text = bool(self.source_input.text().strip()) or bool(self.target_input.text().strip())

        if has_text :
            self.name_input.setReadOnly(True)
            self.acl_input.setReadOnly(True)
            self.depth_input.setReadOnly(True)

            self.name_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
            self.acl_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
            self.depth_input.setStyleSheet(self.DISABLED_INPUT_STYLE)
        else:
            self.name_input.setReadOnly(False)
            self.acl_input.setReadOnly(False)
            self.depth_input.setReadOnly(False)

            self.name_input.setStyleSheet(self.INPUT_STYLE)
            self.acl_input.setStyleSheet(self.INPUT_STYLE)
            self.depth_input.setStyleSheet(self.INPUT_STYLE)

    def process_inputs(self) -> list:
        name_value = self.name_input.text()
        acl_value = self.acl_input.text()
        nodes_value = self.nodes_input.text()
        depth_value = self.depth_input.text()

        inbound_check = self.inbound_check.isChecked()

        source_value = self.source_input.text()
        target_value = self.target_input.text()

        if depth_value != "" and not depth_value.isdigit() :
            from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
            N4LMessageBox("Information", "Depth must be an integer", self.controller.retrieve_main_window())
        else:
            acl_list = []

            valid_parameters = True
            if not self.name_input.isReadOnly() : #Basic search
                if acl_value == "" or name_value == "" :
                    valid_parameters = False
            elif not self.source_input.isReadOnly() : #Targeted search
                if source_value == "" or target_value == "" :
                    valid_parameters = False

            if valid_parameters :
                for acl in acl_value.split(","):
                    if acl != "" :
                        acl_list.append(acl.strip())

                if source_value != "" and target_value != "" :
                    acl_list.append("all")

                exclusion_list = []
                for node in nodes_value.split(","):
                    exclusion_list.append(node.strip())

                return True, name_value.strip().upper(), acl_list, depth_value.strip(), source_value.strip().upper(), target_value.strip().upper(), exclusion_list, inbound_check
            else:
                self.controller.notify_no_results("Invalid parameters")
                return False, "", "", "", "", "", "", ""

    def on_search_button_clicked(self) -> None: 
        valid_parameters, name_value, acl_list, depth_value, source_value, target_value, exclusion_list, inbound_check =  self.process_inputs()
        if valid_parameters :
            self.controller.request_ACL_query(name_value, acl_list, depth_value, source_value, target_value, exclusion_list, inbound_check)
            
    # ---

    # View node to acl view
    def add_inbound_text(self, root_node) -> None:
        self.name_input.setText(root_node)
        self.acl_input.setText("all")
        self.inbound_check.setChecked(True)

        self.source_input.clear()
        self.target_input.clear()
        self.nodes_input.clear()

    def add_outbound_text(self, root_node) -> None:
        self.name_input.setText(root_node)
        self.acl_input.setText("all")
        self.inbound_check.setChecked(False)

        self.source_input.clear()
        self.target_input.clear()
        self.nodes_input.clear()

    def put_target(self, target) -> None:
        self.name_input.clear()
        self.acl_input.clear()
        self.depth_input.clear()
        self.nodes_input.clear()
        self.inbound_check.setChecked(False)

        self.target_input.setText(target)
    
    def put_source(self, source) -> None:
        self.name_input.clear()
        self.acl_input.clear()
        self.depth_input.clear()
        self.nodes_input.clear()
        self.inbound_check.setChecked(False)

        self.source_input.setText(source)

    def repeat_request_with_exclusion(self, excluded_node_list) -> list:
        excluded_nodes = ""
        for exclusion in excluded_node_list:
            excluded_nodes += exclusion + ","

        excluded_nodes = excluded_nodes[:-1]

        if self.nodes_input.text() :
            self.nodes_input.setText(self.nodes_input.text() + "," + excluded_nodes)
        else:
            self.nodes_input.setText(excluded_nodes)

        valid_parameters, name_value, acl_list, depth_value, source_value, target_value, exclusion_list, inbound_check =  self.process_inputs()

        if valid_parameters :
            return name_value, acl_list, depth_value, source_value, target_value, exclusion_list, inbound_check

    # ---

    # Popups
    def show_weights_popup(self) -> None: 
        from Neo4LDAP.gui.N4L_Popups import N4LWeights
        N4LWeights(self.controller.retrieve_main_window(), self.controller, self.controller.retrieve_actual_acl_weights())

    def show_acl_help_popup(self) -> None: 
        from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
        text = "The following ACEs are supported in Neo4LDAP:\n\n• All\n• FirstDegree\n\nExtended ACEs:\n\n"
        
        self.neo4j_stats = self.controller.retrieve_neo4j_stats()
        for acl in self.neo4j_stats["ACL_Types"]:
            text += "• {acl}\n".format(acl = acl)

        N4LMessageBox("Information", text, self.controller.retrieve_main_window())
    
    def show_exclusion_help_popup(self) -> None: 
        from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
        text = "This feature allows you to manually exclude nodes by User Principal Name or DNS name from the graph.\n\n(e.g., dummy.user@corp.com, DC01.corp.com).\n\nThis is useful when:\n• Certain nodes are irrelevant to your current analysis\n• You want to reduce visual clutter in large graphs"
        
        N4LMessageBox("Information", text, self.controller.retrieve_main_window(), 300, 460)
