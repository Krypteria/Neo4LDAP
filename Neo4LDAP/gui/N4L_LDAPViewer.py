from PySide6.QtGui import QColor, QKeySequence, QShortcut, QFont
from PySide6.QtWidgets import QToolTip, QApplication, QHeaderView, QScrollArea, QTableWidget, QTableWidgetItem, QMenu
from PySide6.QtCore import QPoint

from Neo4LDAP.gui.N4L_CommonViewer import *

class LDAPViewerApp(ViewerApp):
    debug_signal = Signal(str)
    add_query_signal = Signal(str)
    update_custom_queries_signal = Signal(list)
    push_upload_debug_info_signal = Signal(str)
    update_neo4j_db_stats_signal = Signal(dict)

    def __init__(self, controller, neo4j_stats):
        super().__init__(controller)

        self.debug_signal.connect(self.push_debug)
        self.add_query_signal.connect(self.add_query_text)
        self.update_custom_queries_signal.connect(self.update_custom_queries)
        self.push_upload_debug_info_signal.connect(self.push_upload_debug_info)
        self.update_neo4j_db_stats_signal.connect(self.update_information_panel)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Panel
        self.left_panel = self.initialize_left_panel()

        # Middle Panel
        self.middle_panel = self.initialize_middle_panel()

        # Right Panel
        self.right_panel = self.initialize_right_panel(neo4j_stats)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.middle_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([400, 800, 400])
        splitter.setHandleWidth(0)

        main_layout.addWidget(splitter)
        self.init_shortcuts()

    def initialize_left_panel(self) -> QWidget:
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: {color}; border: none;".format(color = self.PANELS_BG))

        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: {color}; border: none;".format(color = self.PANELS_BG))

        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop)

        switch_buttons_layout = self.create_switch_buttons_layout()

        ldap_title = self.create_label("LDAP TO CIPHER", False, self.TITLE_STYLE)
        custom_query_title = self.create_label("CUSTOM QUERIES", False, self.TITLE_STYLE) 

        ldap_title.setAlignment(Qt.AlignCenter)
        custom_query_title.setAlignment(Qt.AlignCenter)

        ldap_frame = self.init_ldap_query_panel()
        custom_query_frame = self.init_custom_query_panel()

        # Footer
        footer_label = QLabel("@_kripteria")
        footer_label.setStyleSheet("color: {background}; font-weight: bold; font-size: 12px; margin-top: 10px;".format(background = self.BUTTON_HOVER))
        footer_label.setAlignment(Qt.AlignCenter)

        #Scrollable content
        scroll_layout.addWidget(ldap_title)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(ldap_frame)
        scroll_layout.addSpacing(10)
        scroll_layout.addWidget(custom_query_title)
        scroll_layout.addSpacing(5)
        scroll_layout.addWidget(custom_query_frame)
        scroll_layout.addSpacing(30)
        scroll_layout.addWidget(footer_label)
        scroll_layout.addSpacing(30)

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

    def initialize_middle_panel(self) -> QWidget:
        middle_panel = QWidget()
        middle_panel.setStyleSheet("background-color: {color}; border: none;".format(color = self.PANELS_BG))

        ldap_result_frame = self.init_ldap_result_panel()

        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.addWidget(ldap_result_frame)

        return middle_panel
    
    def initialize_right_panel(self, neo4j_stats) -> QWidget:
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: {color}".format(color = self.PANELS_BG))

        information_title = self.create_label("NEO4J INFORMATION", False, self.TITLE_STYLE)
        debug_title = self.create_label("DEBUG", False, self.TITLE_STYLE)

        information_title.setAlignment(Qt.AlignCenter)
        debug_title.setAlignment(Qt.AlignCenter)

        information_layout = QVBoxLayout(right_panel)
        information_frame = self.init_information_panel(neo4j_stats)
        debug_frame = self.init_debug_panel()
        
        information_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        debug_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        information_layout.addWidget(information_title)
        information_layout.addSpacing(5)
        information_layout.setAlignment(Qt.AlignTop)

        information_layout.addWidget(information_frame)
        information_layout.addSpacing(10)
        information_layout.addWidget(debug_title)
        information_layout.addSpacing(5)
        information_layout.addWidget(debug_frame)

        return right_panel

    def init_ldap_query_panel(self) -> QFrame:
        ldap_frame = QFrame()
        ldap_frame.setStyleSheet(self.QFRAME_STYLE)

        query_label = self.create_label("Query", True)
        attributes_label = self.create_label("Attributes", True)

        self.query_input = self.create_text_field()
        self.attributes_input = self.create_text_field()

        checkbox_container = self.create_checkbox_container("Raw output")
        query_button =  self.create_button("Query", self.on_query_button_clicked) 

        ldap_layout = QVBoxLayout(ldap_frame)
        ldap_layout.setContentsMargins(20, 20, 20, 20)
        ldap_layout.setSpacing(7)

        # First Row
        ldap_layout.addWidget(query_label)
        ldap_layout.addWidget(self.query_input)
        ldap_layout.addSpacing(10)
        
        # Second Row
        ldap_layout.addWidget(attributes_label)
        ldap_layout.addWidget(self.attributes_input)

        ldap_layout.addSpacing(10)

        # Third row
        ldap_layout.addWidget(checkbox_container)
        ldap_layout.addWidget(query_button)

        return ldap_frame

    # Custom queries
    def init_custom_query_panel(self) -> QFrame:
        main_frame = QFrame()
        main_frame.setStyleSheet("background-color: {background}; border: 1px solid {border}; border-radius: 10px;".format(background = self.SUBPANELS_BG, border = self.PANELS_BD))
        main_frame.setMinimumHeight(320) 

        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(20, 20, 20, 20)

        add_custom_query_button = self.create_button("Add custom query", self.add_custom_query_popup)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(self.QSCROLLBAR_STYLE)

        self.query_rows_container = QWidget()
        self.query_rows_container.setStyleSheet("background-color: {background}; border: none; border-radius: 10px;".format(background = self.PANELS_BG))

        self.query_rows_layout = QVBoxLayout(self.query_rows_container)
        self.query_rows_layout.setSpacing(12)
        self.query_rows_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.query_rows_container)
        
        # First Row
        main_layout.addWidget(add_custom_query_button, alignment=Qt.AlignTop)
        main_layout.addWidget(scroll_area)

        return main_frame
    
    def update_custom_queries(self, custom_queries_list) -> None:
        self.clear_custom_queries_from_view()
        for index, custom_query in enumerate(custom_queries_list):
            self.add_custom_query_row(custom_query, index)

    def clear_custom_queries_from_view(self) -> None:
        while self.query_rows_layout.count():
            item = self.query_rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None :
                widget.setParent(None)

    def add_custom_query_row(self, query_json, index) -> None:
        row_layout = QHBoxLayout()
        row_layout.setSpacing(15)

        label = self.create_label(query_json["name"])
        
        run_button = self.create_button("\u25B6", lambda: self.run_custom_query(query_json), self.SMALL_BUTTON_STYLE)
        edit_button = self.create_button("\u270E", lambda: self.edit_custom_query(query_json, index), self.SMALL_BUTTON_STYLE)
        delete_button = self.create_button("\u2715", lambda: self.delete_custom_query(index), self.SMALL_BUTTON_STYLE)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(run_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)

        button_container = QWidget()
        button_container.setLayout(button_layout)
        button_container.setStyleSheet("background: transparent; border: none;")

        row_layout.addWidget(label, stretch=1)
        row_layout.addWidget(button_container)

        container = QWidget()
        container.setStyleSheet(self.CUSTOM_QUERY_STYLE)
        container.setLayout(row_layout)

        self.query_rows_layout.addWidget(container)

    def edit_custom_query(self, query_json, index) -> None:
        from Neo4LDAP.gui.N4L_Popups import N4LQueryPopup
        
        attributes = ""
        if query_json["attributes"] != None:
            attributes = ",".join(query_json["attributes"])

        N4LQueryPopup(self.controller, self.controller.retrieve_main_window(), index, query_json["name"], query_json["description"], query_json["query"], attributes)

    def delete_custom_query(self, index) -> None:
        self.controller.delete_custom_query(index)

    def run_custom_query(self, query_json) -> None:
        self.query_input.setText(query_json["query"])

        attributes = ""
        if query_json["attributes"] != None:
            attributes = ",".join(query_json["attributes"])

        self.attributes_input.setText(attributes)
        self.on_query_button_clicked()

    # ---

    def create_ldap_table(self) -> QTableWidget:
        table  = QTableWidget(0, 2)
        table.setColumnWidth(0, 250)
        table.setColumnWidth(1, 525)
        
        table.horizontalHeader().setSectionsMovable(False)
        table.verticalHeader().setSectionsMovable(False)

        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(False)

        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.result_table_context_menu)
        table.setFocusPolicy(Qt.StrongFocus)

        table.setStyleSheet("""
            QTableWidget {{
                gridline-color: {background}; 
                background-color: {background}; 
                border: none;
            }}
            QTableWidget::item {{
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {selection};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {background};
                border: none;
            }}
            {scrollbar}
        """.format(background=self.LDAP_TABLE_BG, selection = self.SELECTION, scrollbar = self.QSCROLLBAR_STYLE))

        return table

    def init_ldap_result_panel(self) -> QFrame:
        # Main frame
        ldap_result_frame = QFrame()
        ldap_result_frame.setStyleSheet("background-color: {background}; border: 1px solid {border}; border-radius: 10px;".format(background = self.LDAP_TABLE_BG, border = self.PANELS_BD))

        # Result panel
        table_panel = QWidget()
        table_panel.setStyleSheet("background-color: {background}; border: none;".format(background = self.LDAP_TABLE_BG))

        self.table_layout = QVBoxLayout(table_panel)

        self.ldap_result_table = self.create_ldap_table()

        self.table_layout.addWidget(self.ldap_result_table)
        
        main_layout = QVBoxLayout(ldap_result_frame)
        main_layout.addWidget(table_panel)

        return ldap_result_frame
    
    def init_information_panel(self, neo4j_stats) -> QFrame:
        neo4j_statsTitle = ["User", "Group", "Computer", "OU", "GPO", "Domain", "", "Relationships", "ACLs"]

        table_panel = QWidget()
        table_panel.setStyleSheet("background-color: {background}; border: none; ".format(background = self.PANELS_BG))

        # PLACEHOLDER
        self.information_table = QTableWidget(len(neo4j_statsTitle), 2)
        self.information_table.setSelectionMode(QTableWidget.NoSelection)

        self.information_table.setColumnWidth(0, 250)

        self.information_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.information_table.horizontalHeader().setSectionsMovable(False)
        self.information_table.verticalHeader().setSectionsMovable(False)

        self.information_table.verticalHeader().setVisible(False)
        self.information_table.horizontalHeader().setVisible(False)

        self.information_table.setAlternatingRowColors(True)
        self.information_table.setStyleSheet("""
            QTableWidget {{
                gridline-color: {background}; 
                background-color: {background}; 
                alternate-background-color: {alternate_background};
                border: none;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
            }}
            QHeaderView::section {{
                background-color: {background};
                border: none;
            }}
            {scrollbar}
        """.format(background = self.LDAP_TABLE_BG, alternate_background = self.INPUT_BG, scrollbar = self.QSCROLLBAR_STYLE))

        self.update_information_panel(neo4j_stats)

        information_frame = QFrame()
        information_frame.setStyleSheet("background-color: {background}; border: none;".format(background = self.PANELS_BG))
        information_frame.setMaximumHeight(335)

        import_files_button = self.create_button("Upload", self.upload_files)
        refresh_button = self.create_button("Refresh", self.refresh_neo4j_db_data)
        clear_button = self.create_button("Clear DB", self.clear_neo4j_db_data)
        

        db_buttons_layout = QHBoxLayout()
        db_buttons_layout.addWidget(import_files_button)
        db_buttons_layout.addWidget(refresh_button)
        db_buttons_layout.addWidget(clear_button)

        information_layout = QVBoxLayout(information_frame)
        information_layout.setAlignment(Qt.AlignTop)
        information_layout.setContentsMargins(5,5,5,5)

        information_layout.addWidget(self.information_table, stretch=1)
        information_layout.addSpacing(10)
        information_layout.addLayout(db_buttons_layout)

        return information_frame
    
    def update_information_panel(self, neo4j_stats) -> None:
        neo4j_statsTitle = ["User", "Group", "Computer", "OU", "GPO", "Domain", "", "Relationships", "ACLs"]

        self.information_table.clearContents()

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)

        QToolTip.setFont(font)
        self.setStyleSheet("""
            QToolTip { 
                background-color: black; 
                color: white; 
                border: black solid 1px
            }
        """)

        for row, stat in enumerate(neo4j_statsTitle):
            stat_label, stat_item = "", ""
            if stat != "" :
                stat_label = QTableWidgetItem(stat)
                stat_label.setForeground(QColor("white"))

                stat_item = QTableWidgetItem(str(neo4j_stats[stat]))
                stat_item.setForeground(QColor("white"))
            else:
                stat_label = QTableWidgetItem("")
                stat_item = QTableWidgetItem("")

            stat_label.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            stat_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)

            stat_label.setFlags(stat_label.flags() & ~Qt.ItemIsEditable)
            stat_item.setFlags(stat_item.flags() & ~Qt.ItemIsEditable)

            stat_label.setFont(font)
            stat_item.setFont(font)

            stat_item.setToolTip(stat_item.text())
                       
            self.information_table.setItem(row, 0, stat_label)
            self.information_table.setItem(row, 1, stat_item)

    def init_debug_panel(self) -> QFrame:
        debug_frame = QFrame()
        debug_frame.setStyleSheet("background-color: {background}; border: none; border-radius: 10px;".format(background = self.LDAP_TABLE_BG))
        debug_frame.setMinimumHeight(150) 

        debug_layout = QVBoxLayout(debug_frame)

        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setStyleSheet("""
            QTextEdit {{
                background-color: {background};
                color: white;
                padding: 8px;
                border: none;
            }}
            {scrollbar}
        """.format(background = self.LDAP_TABLE_BG, scrollbar = self.QSCROLLBAR_STYLE))

        self.debug_text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.debug_text.customContextMenuRequested.connect(self.debug_context_menu)
        self.debug_text.setFocusPolicy(Qt.StrongFocus)

        debug_layout.addWidget(self.debug_text)

        return debug_frame
    
    # Context menus
    def result_table_context_menu(self, position: QPoint) -> None:
        index = self.ldap_result_table.indexAt(position)
        if not index.isValid() :
            return
    
        menu = QMenu(self)
        menu.setStyleSheet(self.QMENU_STYLE)
        
        copy_action = menu.addAction("Copy\tCtrl+C")
        select_all_action = menu.addAction("Select All\tCtrl+A")
        
        selected = menu.exec_(self.ldap_result_table.viewport().mapToGlobal(position))
        
        if selected == copy_action :
            self.copy_cells()
        elif selected == select_all_action :
            self.select_all_cells()

    def debug_context_menu(self, position) -> None:
        menu = QMenu(self)  
        menu.setStyleSheet(self.QMENU_STYLE)

        copy_action = menu.addAction("Copy\tCtrl+C")
        select_all_action = menu.addAction("Select All\tCtrl+A")
        clear_action = menu.addAction("Clear")

        action = menu.exec_(self.debug_text.mapToGlobal(position))
        cursor = self.debug_text.textCursor()

        if action == copy_action and cursor.hasSelection() :
            self.debug_copy_text()
        elif action == select_all_action :
            self.debug_select_all()
        elif action == clear_action :
            self.debug_clear()

    def debug_copy_text(self) -> None:
        cursor = self.debug_text.textCursor()
        if cursor.hasSelection() :
            self.debug_text.copy()

    def debug_select_all(self) -> None:
        self.debug_text.selectAll()

    def debug_clear(self) -> None:
        self.debug_text.clear()

    def init_shortcuts(self) -> None:
        self.table_copy_sc = QShortcut(QKeySequence("Ctrl+C"), self.ldap_result_table)
        self.table_select_all_sc = QShortcut(QKeySequence("Ctrl+A"), self.ldap_result_table)

        self.table_copy_sc.activated.connect(self.copy_cells)
        self.table_select_all_sc.activated.connect(self.select_all_cells)

        self.table_copy_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.table_select_all_sc.setContext(Qt.WidgetWithChildrenShortcut)

        self.debug_copy_sc = QShortcut(QKeySequence("Ctrl+C"), self.debug_text)
        self.debug_select_all_sc = QShortcut(QKeySequence("Ctrl+A"), self.debug_text)

        self.debug_copy_sc.activated.connect(self.debug_copy_text)
        self.debug_select_all_sc.activated.connect(self.debug_select_all)

        self.debug_copy_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.debug_select_all_sc.setContext(Qt.WidgetWithChildrenShortcut)

    def select_all_cells(self) -> None:
        self.ldap_result_table.selectAll()

    def copy_cells(self) -> None:
        selected_items = self.ldap_result_table.selectedItems()
        clipboard = QApplication.clipboard()
        
        if not selected_items :
            return 
        
        selected_columns = set()
        for item in selected_items:
            selected_columns.add(item.column())
            
        formatted_text = []

        if len(selected_columns) == 1 :
            for item in selected_items:
                formatted_text.append(item.text())
        else: 
            for i in range(0, len(selected_items), 2):
                column_0 = selected_items[i].text()
                column_1 = ""
                if i + 1 < len(selected_items) :
                    column_1 = selected_items[i + 1].text()

                if column_0 != "" :
                    formatted_text.append(f"{column_0}: {column_1}")
                else:
                    formatted_text.append(f"\t  {column_1}")

        text = "\n".join(formatted_text)
        clipboard.setText(text)

    # ---
    
    # Utility methods
    def redraw_gui(self, resultOutput) -> None:
        lines = resultOutput.split("\n")

        old_table = self.ldap_result_table
        self.ldap_result_table = self.create_ldap_table()
        
        self.ldap_result_table.setRowCount(len(lines))

        memberof_key = False
        member_key = False
        spn_key = False

        font = QFont()
        font.setPointSize(12)
        font.setBold(False)

        for row, line in enumerate(lines):
            split_data = line.split(":", 1)
            key = split_data[0].strip()
            value = ""

            if len(split_data) > 1 :
                value = split_data[1].strip() 

            if key == "" :
                memberof_key = False
                member_key = False
                spn_key = False

            if key == "memberOf" and not memberof_key :
                memberof_key = True
            elif key == "memberOf" and memberof_key :
                key = ""
            
            if key == "member" and not member_key :
                member_key = True
            elif key == "member" and member_key :
                key = ""

            if key == "serviceprincipalnames" and not spn_key :
                spn_key = True
            elif key == "serviceprincipalnames" and spn_key :
                key = ""

            value_item = QTableWidgetItem(value)
            value_item.setForeground(QColor("white"))
            value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            key_item = QTableWidgetItem(key)
            key_item.setForeground(QColor("white"))
            key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            key_item.setFont(font)
            value_item.setFont(font)

            self.ldap_result_table.setItem(row, 0, key_item)
            self.ldap_result_table.setItem(row, 1, value_item)

        self.table_layout.replaceWidget(old_table, self.ldap_result_table)
        old_table.deleteLater()

    def on_query_button_clicked(self) -> None: 
        query_value = self.query_input.text()
        attributes = self.attributes_input.text()
        raw_query = self.raw_query_check.isChecked()

        tokens = ["&", "|", "!"]
        valid_query = True

        if query_value == "" :
            valid_query = False
        else:
            if not re.search(r"(<=|>=|=|>|<)", query_value) :
                valid_query = False
            else:
                for token in tokens:
                    if token in query_value and "(" + token not in query_value :
                        valid_query = False
                        break
            
        if valid_query :
            attribute_list = None
            if attributes != "" :
                attribute_list = ["cn"]
                for attribute in attributes.split(","):
                    if attribute != "cn" and attribute != "name" :
                        attribute_list.append(attribute.strip())

            self.controller.request_LDAP_query(query_value.strip(), attribute_list, raw_query)
        else:
            self.controller.notify_no_results("The provided LDAP query is not a valid LDAP query.")

    # ---

    # Popups
    def push_debug(self, message) -> None:
        self.debug_text.append(message)

    def add_query_text(self, query) -> None:
        self.query_input.setText(query)

    def push_upload_debug_info(self, message) -> None:
        self.file_uploader.push_debug_info(message)

    def upload_files(self) -> None:
        from Neo4LDAP.gui.N4L_Popups import N4LFileExplorer
        self.file_uploader = N4LFileExplorer(self.controller.retrieve_main_window(), self.controller)
        self.file_uploader.show()

    def refresh_neo4j_db_data(self) -> None:
        self.controller.update_neo4j_db_stats()

    def clear_neo4j_db_data(self) -> None:
        from Neo4LDAP.gui.N4L_Popups import N4LQuestionBox
        question_box = N4LQuestionBox("Clear Neo4j DB", "You are about to delete all the nodes and relationships inside the current Neo4j database, are you sure?", self.controller.retrieve_main_window())
        question_box.decision_made.connect(self.clear_neo4j_db_data_decision)
    
    def clear_neo4j_db_data_decision(self, decision) -> None:
        if decision :
            self.controller.clear_neo4j_db_data()
            self.controller.update_neo4j_db_stats()

    def add_custom_query_popup(self) -> None:
        from Neo4LDAP.gui.N4L_Popups import N4LQueryPopup
        N4LQueryPopup(self.controller, self.controller.retrieve_main_window())
        