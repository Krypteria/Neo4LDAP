from PySide6.QtGui import QPixmap

from Neo4LDAP.gui.N4L_CommonViewer import *

class LoginWindow(ViewerApp):
    def __init__(self, controller):
        super().__init__(controller)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # LEFT SPAN
        left_span = QWidget(self)
        left_span.setFixedWidth(650)
        left_span.setStyleSheet("background-color: {background};".format(background = self.PANELS_BG))

        # RIGHT SPAN
        right_span = QWidget(self)
        right_span.setFixedWidth(650)
        right_span.setStyleSheet("background-color: {background};".format(background = self.PANELS_BG))

        # CENTER SPAN
        center_span = QWidget(self)
        center_span.setStyleSheet("background-color: {background};".format(background = self.PANELS_BG))

        # LOGIN FORM
        login_frame = QFrame(self)
        login_frame.setStyleSheet(self.QFRAME_STYLE)
        login_frame.setFixedSize(350, 430)

        vertical_layout = QVBoxLayout(login_frame)
        vertical_layout.setContentsMargins(30, 30, 30, 30)
        vertical_layout.setSpacing(10)

        # IMAGE LABEL
        image_label = QLabel(self)
        image_label.setStyleSheet("background: white")
        icon_path = controller.retrieve_resource_path("brand.png") 
        
        pixmap = QPixmap(icon_path)
        scaled_pixmap = pixmap.scaled(250, 1000, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)

        self.username_input = self.create_text_field("Neo4j username")
        self.username_input.setText("neo4j")
        self.username_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        self.password_input = self.create_text_field("Neo4j password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText("neo4j")
        self.password_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        self.database_input = self.create_text_field("Neo4j database (default: neo4j)")
        self.database_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        self.bolt_uri_input = self.create_text_field("Neo4j Bolt port")
        self.bolt_uri_input.setText("bolt://localhost:7687")
        self.bolt_uri_input.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        login_button = self.create_button("Login", self.on_login_button_clicked)
        login_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        center_layout = QVBoxLayout(center_span)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(login_frame)

        vertical_layout.addWidget(image_label)
        vertical_layout.addSpacing(5)
        vertical_layout.addWidget(self.username_input)
        vertical_layout.addSpacing(5)
        vertical_layout.addWidget(self.password_input)
        vertical_layout.addSpacing(5)
        vertical_layout.addWidget(self.database_input)
        vertical_layout.addSpacing(5)
        vertical_layout.addWidget(self.bolt_uri_input)
        vertical_layout.addItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        vertical_layout.addWidget(login_button)

        main_layout.addWidget(left_span)
        main_layout.addWidget(center_span)
        main_layout.addWidget(right_span)

        self.setLayout(main_layout)

    def on_login_button_clicked(self) -> None: 
        self.controller.login(self.username_input.text(), self.password_input.text(), self.database_input.text(), self.bolt_uri_input.text())