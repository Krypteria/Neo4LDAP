from PySide6.QtWidgets import QTreeView, QFileSystemModel, QAbstractItemView, QButtonGroup, QGridLayout
from PySide6.QtCore import QDir
from PySide6.QtGui import QIntValidator

from Neo4LDAP.gui.N4L_CommonViewer import *

import os

class N4LFileExplorer(Popups):
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        self.controller = controller
        self.first_time = True
        self.selected_files = []

        self.setMinimumSize(700, 800)

        title_label = self.create_label("Ingest JSON into Neo4j", True, self.MESSAGE_TITLE_STYLE_2, 40)
        title_label.setAlignment(Qt.AlignCenter)

        explorer_frame = QFrame()
        explorer_frame.setStyleSheet("""
            QFrame {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """.format(background = self.POPUP_BG, border = self.PANELS_BD))

        explorer_layout = QVBoxLayout(explorer_frame)

        # Path bar
        path_bar_layout = QHBoxLayout()
        self.path_input = self.create_text_field(QDir.homePath())
        self.go_button = self.create_button("Go", self.navigate_to_path, self.SMALL_BUTTON_STYLE)

        path_bar_layout.addWidget(self.path_input)
        path_bar_layout.addWidget(self.go_button)

        # File system view
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.homePath())
        self.model.setNameFilters(["*.json"])
        self.model.setNameFilterDisables(False)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setRootIndex(self.model.index(QDir.homePath()))
        self.view.setColumnWidth(0, 350)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setStyleSheet("""
            QTreeView {{
                background-color: {background};
                color: white;
                padding: 8px;
                border: 1px solid {border};
            }}
            QHeaderView::section {{
                background-color: #3B4252;
                color: white;
                padding: 4px;
                text-align: center;
                font-weight: bold;
                border: none;
                border-right: 1px solid {border};
            }}
            {scrollbar}
        """.format(background = self.SUBPANELS_BG, scrollbar = self.QSCROLLBAR_STYLE, border = self.TEXT_PANEL_BD))

        # Inputs
        checkbox_container = QWidget()
        checkbox_container.setStyleSheet("border: none;")

        checkbox_layout = QHBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(0, 0, 0, 6)
        checkbox_layout.setSpacing(0)

        self.legacy_check = QCheckBox("Legacy")
        self.legacy_check.setStyleSheet(self.CHECKBOX_STYLE)
        self.legacy_check.setChecked(True)

        self.ce_check = QCheckBox("CE")
        self.ce_check.setStyleSheet(self.CHECKBOX_STYLE)

        button_group = QButtonGroup(checkbox_container)
        button_group.setExclusive(True)
        button_group.addButton(self.legacy_check)
        button_group.addButton(self.ce_check)

        checkbox_layout.addStretch()
        checkbox_layout.addWidget(self.legacy_check)
        checkbox_layout.addSpacing(11)
        checkbox_layout.addWidget(self.ce_check)
        checkbox_layout.addStretch()

        self.debug_panel = self.create_popup_text_field(None, "Selected JSON files and debug information will appear here...")

        self.select_files_button = self.create_button("Add JSON files", self.add_selected_files)        
        self.confirm_button = self.create_button("Upload", self.confirm_selection)
        self.close_button = self.create_button("Close", self.close)

        self.workers_label = self.create_label("Workers", True)
        self.retries_label = self.create_label("Retries", True)

        self.workers_input = self.create_text_field(None, "10")
        self.workers_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        self.retries_input = self.create_text_field(None, "15")
        self.retries_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        upload_options_buttons_layout = QHBoxLayout()
        upload_options_buttons_layout.addWidget(checkbox_container)
        upload_options_buttons_layout.addWidget(self.workers_label)
        upload_options_buttons_layout.addWidget(self.workers_input)
        upload_options_buttons_layout.addWidget(self.retries_label)
        upload_options_buttons_layout.addWidget(self.retries_input)

        options_buttons_layout = QHBoxLayout()
        options_buttons_layout.addWidget(self.confirm_button)
        options_buttons_layout.addWidget(self.close_button)

        explorer_layout.addWidget(title_label)
        explorer_layout.addLayout(path_bar_layout)
        explorer_layout.addWidget(self.view)
        explorer_layout.addWidget(self.select_files_button)
        explorer_layout.addWidget(self.debug_panel)
        explorer_layout.addSpacing(10)
        explorer_layout.addLayout(upload_options_buttons_layout)
        explorer_layout.addSpacing(10)
        explorer_layout.addLayout(options_buttons_layout)

        self.view.setMinimumHeight(300)
        self.debug_panel.setMinimumHeight(250)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(explorer_frame)

        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2

        self.move(x, y)

    def navigate_to_path(self) -> None:
        path = self.path_input.text()
        if os.path.isdir(path) :
            self.view.setRootIndex(self.model.index(path))
        else:
            N4LMessageBox("Error", "The specified path is not valid")

    def add_selected_files(self) -> None:
        if len(self.selected_files) == 0:
            self.debug_panel.append("=== SELECTED FILES ===\n")
            self.first_time = False

        indexes = self.view.selectionModel().selectedIndexes()

        for index in indexes:
            if index.column() != 0 :
                continue

            path = self.model.filePath(index)
            if os.path.isfile(path) and path.endswith(".json") :
                if path not in self.selected_files :
                    self.debug_panel.append(path)
                    self.selected_files.append(path)

    def confirm_selection(self) -> None:
        self.debug_panel.append("\n=== UPLOADING FILES TO NEO4J ===\n")
        self.controller.ingest_data_to_neo4j(list(self.selected_files), int(self.workers_input.text()), int(self.retries_input.text()), self.legacy_check.isChecked())
        self.selected_files.clear()

    def push_debug_info(self, message) -> None:
        self.debug_panel.append(message)

class N4LWeights(Popups):
    def __init__(self, parent, controller, acl_value):
        super().__init__(parent)

        self.controller = controller

        # Sort alphabetically
        sorted_items = sorted(acl_value.items(), key=lambda x: x[0])

        message_frame = QFrame()
        message_frame.setStyleSheet("""
            QFrame {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """.format(background=self.POPUP_BG, border=self.PANELS_BD))

        title_label = self.create_label("ACE Weight Editor", True, self.MESSAGE_TITLE_STYLE, 40)
        title_label.setAlignment(Qt.AlignCenter)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(self.QSCROLLBAR_STYLE)
        scroll_area.setFixedHeight(340)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("""
            QWidget {{
                background-color: {background};
                border: none;
                color: white;
                font-weight: normal;
            }}
        """.format(background=self.POPUP_BG, border=self.PANELS_BD))
        
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 5, 0, 5)
        grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.text_fields = {}
        columns = 3
        for index, (acl_name, value) in enumerate(sorted_items):
            col = index % columns
            row = index // columns

            label = QLineEdit(acl_name)
            label.setFixedWidth(220)
            label.setFixedHeight(30)
            label.setReadOnly(True)
            label.setContextMenuPolicy(Qt.NoContextMenu)

            label.setStyleSheet("color: white; font-weight: bold;")
            label.setStyleSheet("""
                QLineEdit {{
                    background-color: {background};
                    border: 1px solid {border};
                    border-radius: 4px;
                    color: white;
                    font-weight: normal;
                }}
            """.format(background=self.SUBPANELS_BG, border=self.PANELS_BD))
            label.setContentsMargins(5, 0, 0, 0)

            field = QLineEdit(str(value))
            field.setStyleSheet(self.INPUT_STYLE)
            field.setContextMenuPolicy(Qt.NoContextMenu)
            field.setFixedWidth(50)
            field.setFixedHeight(30)
            field.setAlignment(Qt.AlignCenter)
            field.setValidator(QIntValidator(1, 9))
            self.text_fields[acl_name] = field

            grid_layout.addWidget(label, row, col * 2)
            grid_layout.addWidget(field, row, col * 2 + 1)


        scroll_area.setWidget(grid_widget)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(15)
        button_layout.setAlignment(Qt.AlignCenter)

        save_button = self.create_button("Save", self.save)
        cancel_button = self.create_button("Cancel", self.cancel)
        reset_button = self.create_button("Default", self.default)

        save_button.setFixedSize(150, 35)
        cancel_button.setFixedSize(150, 35)
        reset_button.setFixedSize(150, 35)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(reset_button)

        frame_layout = QVBoxLayout(message_frame)
        frame_layout.setContentsMargins(15, 15, 15, 15)
        frame_layout.addWidget(title_label)
        frame_layout.addWidget(scroll_area)
        frame_layout.addStretch()
        frame_layout.addLayout(button_layout)

        self.setFixedSize(890, 470)
        self.setAttribute(Qt.WA_DeleteOnClose)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(message_frame)

        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2

        self.move(x, y)
        self.show()

    def save(self):
        acl_weight_values = {}
        valid_weights = True

        for key, field in self.text_fields.items():
            try:
                if(field.text() == ""):
                    from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
                    N4LMessageBox("Invalid weight", "The weights associated with ACE's cannot be empty values.", self.controller.retrieve_main_window())
                    valid_weights = False
                    break
                else:
                    acl_weight_values[key] = int(field.text())
            except ValueError:
                pass

        if(valid_weights):
            self.controller.update_actual_acl_weights(acl_weight_values)
            self.close()

    def default(self):
        self.controller.reset_actual_acl_weights()
        self.close()

    def cancel(self) -> bool:
        self.close()

class N4LShadowRelationshiphs(Popups):
    def __init__(self, parent, controller, node, shadow_relationships):
        super().__init__(parent)

        self.controller = controller

        title_label = self.create_label("Shadow Relationships", True, self.MESSAGE_TITLE_STYLE, 40)
        title_label.setAlignment(Qt.AlignCenter)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search identity or ACE")
        self.search_field.setStyleSheet(self.INPUT_STYLE)
        self.search_field.setContextMenuPolicy(Qt.NoContextMenu)
        self.search_field.textChanged.connect(self.filter_relationships)

        message_frame = QFrame()
        message_frame.setStyleSheet("""
            QFrame {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """.format(background=self.POPUP_BG, border=self.PANELS_BD))

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(self.QSCROLLBAR_STYLE)
        scroll_area.setFixedHeight(330)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("""
            QWidget {{
                background-color: {background};
                border: none;
                color: white;
                font-weight: normal;
            }}
        """.format(background=self.POPUP_BG, border=self.PANELS_BD))
        
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(10)
        grid_layout.setContentsMargins(0, 10, 0, 10)
        grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        identity_style = """
            QLineEdit {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 4px;
                color: white;
                font-weight: normal;
            }}
        """.format(background=self.SUBPANELS_BG, border=self.PANELS_BD)

        acl_style = """
            QLineEdit {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 4px;
                color: white;
                font-weight: normal;
            }}
        """.format(background=self.INPUT_BG, border=self.PANELS_BD)
        
        self.shadow_relationships_rows = []
        for row, (target, acls) in enumerate(shadow_relationships):
            node_label = self.create_identity_label(node.split("@")[0], identity_style)
            acl_label = self.create_identity_label(acls, acl_style)
            target_label = self.create_identity_label(target.split("@")[0], identity_style)


            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0) 

            row.addWidget(node_label)
            row.addWidget(acl_label)
            row.addWidget(target_label)

            frame = QFrame()
            frame.setLayout(row)
            self.shadow_relationships_rows.append((frame, node.split("@")[0], acls, target.split("@")[0]))
            grid_layout.addWidget(frame)


        scroll_area.setWidget(grid_widget)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(15)
        button_layout.setAlignment(Qt.AlignCenter)

        close_button = self.create_button("Ok", self.ok)
        close_button.setFixedSize(150, 35)

        button_layout.addWidget(close_button)

        # Frame layout
        frame_layout = QVBoxLayout(message_frame)
        frame_layout.setContentsMargins(15, 15, 15, 15)
        frame_layout.addWidget(title_label)
        frame_layout.addSpacing(10)
        frame_layout.addWidget(self.search_field)
        frame_layout.addWidget(scroll_area)
        frame_layout.addSpacing(5)
        frame_layout.addLayout(button_layout)

        # Main popup layout
        self.setFixedSize(860, 510)
        self.setAttribute(Qt.WA_DeleteOnClose)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(message_frame)

        # Center on parent
        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2
        self.move(x, y)

        self.show()

    def create_identity_label(self, text, style) -> QLabel:
        label = QLineEdit(text)
        label.setFixedWidth(250)
        label.setFixedHeight(30)
        label.setReadOnly(True)
        label.setCursorPosition(0)
        label.setContextMenuPolicy(Qt.NoContextMenu)
        label.setStyleSheet("color: white; font-weight: bold;")
        label.setStyleSheet(style)
        label.setContentsMargins(0, 0, 0, 0)
        label.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        return label
    
    def filter_relationships(self, text):
        text = text.lower()
        for frame, node, acls, target in self.shadow_relationships_rows:
            if text in (node.lower() or "") or text in (acls.lower() or "") or text in (target.lower() or ""):
                frame.show()
            else:
                frame.hide()

    def ok(self) -> bool:
        self.close()

class N4LMessageBox(Popups):
    def __init__(self, title, message, parent, height = 300, width = 400):
        super().__init__(parent)

        message_frame = QFrame()
        message_frame.setStyleSheet("""
            QFrame {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """.format(background = self.POPUP_BG, border = self.PANELS_BD))

        title_label = self.create_label(title, True, self.MESSAGE_TITLE_STYLE, 40)
        title_label.setAlignment(Qt.AlignCenter)

        self.message_text = self.create_popup_text_field(message)        
        close_button = self.create_button("OK", self.close)
        close_button.setFixedSize(150, 35)

        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(10, 10, 10, 10)
        message_layout.setSpacing(7)
        
        message_layout.addWidget(title_label)
        message_layout.addWidget(self.message_text)
        message_layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setFixedSize(width,height)
        self.setAttribute(Qt.WA_DeleteOnClose)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(message_frame)

        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2

        self.move(x, y)
        self.show()

class N4LQuestionBox(Popups):
    
    decision_made = Signal(bool)

    def __init__(self, title, message, parent, height = 300, width = 400):
        super().__init__(parent)

        message_frame = QFrame()
        message_frame.setStyleSheet("""
            QFrame {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """.format(background = self.POPUP_BG, border = self.PANELS_BD))

        title_label = self.create_label(title, True, self.MESSAGE_TITLE_STYLE, 40)
        title_label.setAlignment(Qt.AlignCenter)

        self.message_text = self.create_popup_text_field(message) 

        self.confirmation_button = self.create_button("Yes", self.afirmation)
        self.negation_button = self.create_button("No", self.negation)

        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(10, 10, 10, 10)
        message_layout.setSpacing(7)

        options_buttons_layout = QHBoxLayout()
        options_buttons_layout.addWidget(self.confirmation_button)
        options_buttons_layout.addWidget(self.negation_button)

        message_layout.addWidget(title_label)
        message_layout.addWidget(self.message_text)
        message_layout.addLayout(options_buttons_layout)
        message_layout.setAlignment(Qt.AlignCenter)

        self.setFixedSize(width,height)
        self.setAttribute(Qt.WA_DeleteOnClose)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(message_frame)

        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2

        self.move(x, y)
        self.show()
    
    def afirmation(self) -> bool:
        self.decision_made.emit(True)
        self.close()
    
    def negation(self) -> bool:
        self.decision_made.emit(False)
        self.close()

class N4LQueryPopup(Popups):
    def __init__(self, controller, parent, index = -1, name = "", description = "", query = "", attributes = "", height = 300, width = 400):
        super().__init__(parent)

        self.controller = controller

        message_frame = QFrame()
        message_frame.setStyleSheet("background-color: {background}; border: 1px solid {border}; border-radius: 10px; ".format(background = self.POPUP_BG, border = self.PANELS_BD))

        title_label = self.create_label("Custom Query", True, self.MESSAGE_TITLE_STYLE, 40)
        title_label.setAlignment(Qt.AlignCenter)

        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: {background}; border: 1px solid {border}; border-radius: 10px; ".format(background = self.SUBPANELS_BG, border = self.PANELS_BD))

        self.name_input = self.create_text_field("Custom query name")
        self.description_input = self.create_text_field("Description")
        self.query_input = self.create_text_field("LDAP query")
        self.attributes_input = self.create_text_field("Attributes")

        self.name_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.description_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.query_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.attributes_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        if name != "" :
            self.name_input.setText(name)

        if description != "" :
            self.description_input.setText(description)

        if query != "" :
            self.query_input.setText(query)

        if attributes != "" :
            self.attributes_input.setText(attributes)

        self.index = index

        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(5)
        
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.description_input)
        input_layout.addWidget(self.query_input)
        input_layout.addWidget(self.attributes_input)

        buttoms_layout = QHBoxLayout()

        self.submit_button = self.create_button("Submit", self.submit)
        self.close_button = self.create_button("Close", self.close)

        buttoms_layout.addWidget(self.submit_button)
        buttoms_layout.addWidget(self.close_button)        

        message_layout = QVBoxLayout(message_frame)
        message_layout.setSpacing(7)

        message_layout.addWidget(title_label)
        message_layout.addWidget(input_frame)
        message_layout.addLayout(buttoms_layout)

        self.setFixedSize(width,height)
        self.setAttribute(Qt.WA_DeleteOnClose)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(message_frame)

        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2

        self.move(x, y)
        self.show()

    def submit(self) -> None:
        name = self.name_input.text()
        description = self.description_input.text()
        query = self.query_input.text()
        attributes = self.attributes_input.text()
        
        tokens = ["&", "|", "!"]
        valid_query = True

        if query == "" or name == "" :
            valid_query = False
        else:
            if not re.search(r"(<=|>=|=|>|<)", query) :
                valid_query = False
            else:
                for token in tokens:
                    if token in query and "(" + token not in query :
                        valid_query = False
                        break
            
        if valid_query :
            attribute_list = None
            if attributes != "" :
                attribute_list = ["cn"]
                for attribute in attributes.split(","):
                    if attribute != "cn" and attribute != "name" :
                        attribute_list.append(attribute.strip())

            self.controller.add_new_custom_query(self.index, name, description, query, attribute_list)
            self.close()
        else:
            text = ""
            if name == "" :
                text = "Name can't be empty"
            elif query == "" :
                text = "LDAP query can't be empty"
            else:
                text = "The provided LDAP query is not a valid LDAP query"
            N4LMessageBox("Error", text, self, 300, 350)