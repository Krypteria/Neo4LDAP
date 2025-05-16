from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton, QLineEdit, QLabel, QSplitter, QSizePolicy, QFrame, QMessageBox, QSpacerItem, QCheckBox
from PySide6.QtCore import Qt, Signal, QObject, QThread

import re 

class Styles(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        # Base background
        self.PANELS_BG     = "#181A1F" 
        self.PANELS_BD     = "#2e3440" 

        # Sub panels
        self.SUBPANELS_BG  = "#23252E" 

        # Text inputs
        self.INPUT_BG      = "#2E3440"
        self.INPUT_BD      = "#4C566A"

        self.MENU_BG       = "#2e3440" 

        # Popups
        self.POPUP_BG      = "#181A1F"
        self.TEXT_PANEL_BG = "#3B4252"
        self.TEXT_PANEL_BD = "#3F3F3F"

        # Text and selection
        self.TEXT_COLOR    = "white"
        self.SELECTION     = "#4c566a"

        # Buttons
        self.BUTTON_BG     = "#5d7f99"
        self.BUTTON_HOVER  = "#516b80"

        # Ldap table and debug
        self.LDAP_TABLE_BG = "#3B4252"

        self.QFRAME_STYLE = """
            background-color: {background}; 
            border: 1px solid {border}; 
            border-radius: 10px;
        """.format(background = self.SUBPANELS_BG, border = self.PANELS_BD)
        
        self.TITLE_STYLE = """
            font-weight: bold; 
            font-size: 16px; 
            margin-top: 6px; 
            margin-bottom: 4px; 
            letter-spacing: 0.5px; 
            color: white; 
            padding-bottom: 5px; 
            border-bottom: 2px solid white;
        """

        self.DISABLED_INPUT_STYLE = """
            background-color: #3a3a3a; 
            padding: 5px; 
            color: black;
            border-radius: 5px; 
            padding: 5px;
        """

        self.LABEL_STYLE = """
            font-size: 14px; 
            font-weight: bold; 
            color: white; 
            border: none; 
            margin-bottom: 2px;
        """

        self.CUSTOM_QUERY_STYLE = """
            background-color: {background}; 
            border: 1px solid {border}; 
            border-radius: 10px;
        """.format(background = self.LDAP_TABLE_BG, border = self.PANELS_BD)
        
        self.MESSAGE_TITLE_STYLE = """
            background-color: {background};
            font-weight: bold;
            color: white;
            font-size: 16px;
            padding: 10px;
            border: 1px solid {border};
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        """.format(background = self.TEXT_PANEL_BG, border = self.TEXT_PANEL_BD)

        self.MESSAGE_TITLE_STYLE_2 = """
            background-color: {background};
            font-weight: bold;
            color: white;
            font-size: 16px;
            padding: 10px;
            border: none;
        """.format(background = self.PANELS_BG)

        self.QSCROLLBAR_STYLE = """
            QScrollBar {{
                background: transparent; 
                border: none;
            }}
            QScrollBar:vertical {{
                background: {background};
                width: 10px;
                margin: 2px;
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {handle};
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {background};
                height: 10px;
                margin: 2px;
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle};
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0;
                border: none;
            }}
        """.format(background=self.PANELS_BG, handle=self.SELECTION)

        self.MESSAGE_TEXT_STYLE = """
            QTextEdit {{
                background-color: {background};
                color: white;
                padding: 8px;
                border: 1px solid {border};
            }}
            {scrollbar}
        """.format(background = self.TEXT_PANEL_BG, scrollbar = self.QSCROLLBAR_STYLE, border = self.TEXT_PANEL_BD)

        self.QMENU_STYLE = """
            QMenu {{
                background-color: {background};
                color: {text};
                border: 1px solid {border};
            }}
            QMenu::item {{
                padding: 6px 20px;
                min-width: 200px;
            }}
            QMenu::item:selected {{
                background-color: {selection};
            }}
            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 4px 10px;
            }}
        """.format(background=self.MENU_BG, border=self.PANELS_BD, selection=self.SELECTION, text=self.TEXT_COLOR)

        self.INPUT_STYLE = """
            QLineEdit, QComboBox, QTextEdit {{
                background-color: {background};
                color: {text};
                border: 1px solid {border};
                border-radius: 5px;
                padding: 5px;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid {focus};
            }}
        """.format(background=self.INPUT_BG, text=self.TEXT_COLOR, border=self.INPUT_BD, focus=self.BUTTON_HOVER)

        self.BUTTON_STYLE = """
            QPushButton {{
                background-color: {background};
                border-radius: 6px;
                padding: 8px;
                color: {text};
                font-weight: bold;
                border: 1px solid {border};
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {background};
            }}
        """.format(background=self.BUTTON_BG, hover=self.BUTTON_HOVER, text=self.TEXT_COLOR, border=self.PANELS_BD)

        self.SMALL_BUTTON_STYLE = """
            QPushButton {{
                background-color: {background};
                border-radius: 5px;
                padding: 8px;
                color: {text};
                font-weight: bold;
                outline: none;
                font-size: 12px;
                min-width: 15px;
                min-height: 15px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {background};
            }}
        """.format(background=self.BUTTON_BG, hover=self.BUTTON_HOVER, text=self.TEXT_COLOR)

        self.HELP_BUTTON_STYLE = """
            QPushButton {{
                background-color: transparent;
                color: {text};
                font-weight: bold;
                font-size: 14px;
                padding: 2px;
                border: none;
                outline: none;
                text-align: right;
            }}
            QPushButton:hover {{
                color: {hover};
            }}
        """.format(text=self.TEXT_COLOR, hover=self.SELECTION)

        self.CHECKBOX_STYLE = """
            QCheckBox {{
                color: {text};
                spacing: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 1px solid {border};
                background-color: {background};
            }}
            QCheckBox::indicator:checked {{
                background-color: {fill};
            }}
            QCheckBox::indicator:hover {{
                border-color: {hover};
            }}
        """.format(text=self.TEXT_COLOR, border=self.SELECTION, background="white", fill=self.BUTTON_BG, hover=self.BUTTON_HOVER)


class QWidgetFactory(Styles):
    def create_text_field(self, text = None) -> QLineEdit:
        input_field = QLineEdit()
        input_field.setStyleSheet(self.INPUT_STYLE)
        input_field.setContextMenuPolicy(Qt.NoContextMenu)
        if text != None :
            input_field.setPlaceholderText(text)

        return input_field
    
    def create_popup_text_field(self, text, placeholder_text = None) -> QTextEdit:
        message_text = QTextEdit()
        if text != None :
            message_text.setText(text)
        
        if placeholder_text != None :
            message_text.setPlaceholderText(placeholder_text)

        message_text.setReadOnly(True)
        message_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        message_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        message_text.setContextMenuPolicy(Qt.NoContextMenu)
        message_text.setStyleSheet(self.MESSAGE_TEXT_STYLE)

        return message_text

    def create_label(self, title, fixed_size = False, style = None, size = 20) -> QLabel:
        label = QLabel(title)
        
        if style == None :
            label.setStyleSheet(self.LABEL_STYLE)
        else:
            label.setStyleSheet(style)

        if fixed_size :
            label.setFixedHeight(size)

        return label
    
    def create_button(self, title, on_click_trigger, style = None) -> QPushButton:
        button = QPushButton(title)
        
        if style == None :
            button.setStyleSheet(self.BUTTON_STYLE)
        else:
            button.setStyleSheet(style)

        button.clicked.connect(on_click_trigger)

        return button
    
    def create_checkbox_container(self, title) -> QWidget:
        checkbox_container = QWidget()
        checkbox_container.setStyleSheet("border: none;")
        checkbox_layout = QHBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(0, 0, 0, 6)
        checkbox_layout.setSpacing(0)

        self.raw_query_check = QCheckBox(title)
        self.raw_query_check.setStyleSheet(self.CHECKBOX_STYLE)

        checkbox_layout.addWidget(self.raw_query_check)

        return checkbox_container

class Popups(QWidgetFactory):
    def __init__(self, parent):
        super().__init__(parent)

class ViewerApp(QWidgetFactory):
    refresh_signal = Signal(str)
    refresh_graph_signal = Signal(object, str, bool)
    no_result_signal = Signal(QObject, str)
    error_signal = Signal(QObject, str)

    def __init__(self, controller):
        super().__init__()

        self.controller = controller
        
        self.refresh_signal.connect(self.redraw_gui)
        self.refresh_graph_signal.connect(self.redraw_gui)
        self.no_result_signal.connect(self.notify_no_results)
        self.error_signal.connect(self.notify_error)

        self.resize(1600, 900)

    def create_switch_buttons_layout(self) -> QHBoxLayout:
        switch_buttons_layout = QHBoxLayout()
        LDAPViewer_button = self.create_button("LDAP Viewer", self.change_to_LDAPView)
        ACLViewer_button = self.create_button("ACLs Viewer", self.change_to_ACLView) 

        switch_buttons_layout.addWidget(LDAPViewer_button)
        switch_buttons_layout.addWidget(ACLViewer_button)

        return switch_buttons_layout

    def notify_no_results(self, parent, message) -> None:
        from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
        N4LMessageBox("Information", message, parent)

    def notify_error(self, parent, message) -> None:
        from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
        N4LMessageBox("Error", message, parent, 600, 500)

    def change_to_ACLView(self) -> None:
        self.controller.change_to_ACLView()

    def change_to_LDAPView(self) -> None:
        self.controller.change_to_LDAPView()

    def redraw_gui() -> None:
        pass